from datetime import datetime
from functools import wraps

from flask import Flask, abort, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

from config import config

app = Flask(__name__)
app.config.from_object(config["development"])
app.debug = True

# Initialize the database
db = SQLAlchemy(app)

# Initialize the login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = (
    "login"  # specify what view to go to when a login is required
)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    is_open = db.Column(db.Boolean, nullable=False, default=True)
    is_complete = db.Column(db.Boolean, nullable=False, default=False)
    client_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    discussion = db.relationship("TaskDiscussion", backref="task", lazy=True)
    parent_task_id = db.Column(db.Integer, db.ForeignKey("task.id"))
    subtasks = db.relationship(
        "Task", backref=db.backref("parent_task", remote_side=[id]), lazy=True
    )

    def __repr__(self):
        return f"<Task {self.title}>"

    def add_message(self, user_id, message_text):
        message = TaskDiscussion(task_id=self.id, user_id=user_id, message=message_text)
        db.session.add(message)
        db.session.commit()


class TaskDiscussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

    @property
    def password(self):
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)  # HTTP "Forbidden" error
        return f(*args, **kwargs)

    return decorated_function


# Routes
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/tasks")
@login_required
def tasks():
    tasks = Task.query.filter(
        (Task.client_id == current_user.id) | (Task.worker_id == current_user.id)
    ).all()
    return render_template("tasks.html", tasks=tasks)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user is not None and user.verify_password(password):
            login_user(user)
            return redirect(url_for("home"))
        else:
            # If the user doesn't exist or password is wrong, reload the page
            return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/tasks/create", methods=["GET", "POST"])
@login_required
def create_task():
    if request.method == "POST":
        title = request.form["title"]
        ai = User.query.filter_by(username="ai").first()
        task = Task(title=title, client_id=current_user.id, worker_id=ai.id)
        db.session.add(task)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("create_task.html")


@app.route("/tasks/<int:task_id>/create_subtask", methods=["POST"])
@login_required
def create_subtask(task_id):
    parent_task = Task.query.get_or_404(task_id)

    title = request.form.get("title")
    if not title:
        abort(400, description="No title provided")

    subtask = Task(
        title=title, client_id=current_user.id, parent_task_id=parent_task.id
    )

    db.session.add(subtask)
    db.session.commit()

    return redirect(url_for("task_detail", task_id=task_id))


@app.route("/tasks/<int:task_id>")
@login_required
def task_detail(task_id):
    task = Task.query.get_or_404(task_id)
    if task.client_id != current_user.id and task.worker_id != current_user.id:
        return redirect(
            url_for("home")
        )  # Redirect to homepage if user isn't client or worker
    return render_template("task_detail.html", task=task)


@app.route("/tasks/<int:task_id>/add_message", methods=["POST"])
@login_required
def add_message(task_id):
    task = Task.query.get_or_404(task_id)

    message_text = request.form.get("message")
    if not message_text:
        abort(400, description="No message provided")

    task.add_message(current_user.id, message_text)

    return redirect(url_for("task_detail", task_id=task.id))


@app.route("/users", methods=["GET"])
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template("users.html", users=users)


@app.route("/users/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_user():
    if request.method == "POST":
        # TODO: Add a check for existing user before creating,
        # or otherwise enforce unique usernames and emails

        # Logic to handle form submission and create the user
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        user = User(username=username, email=email)
        user.password = password
        # Save the user to the database
        db.session.add(user)
        db.session.commit()

        return redirect(url_for("home"))

    # Render the user creation form
    return render_template("create_user.html")


if __name__ == "__main__":
    app.run(port=8007)
