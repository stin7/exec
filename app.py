from datetime import datetime
from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from config import config

app = Flask(__name__)
app.config.from_object(config["development"])
app.debug = True

# Initialize the database
db = SQLAlchemy(app)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    is_open = db.Column(db.Boolean, nullable=False, default=True)
    is_complete = db.Column(db.Boolean, nullable=False, default=False)
    client_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    discussion = db.relationship("TaskDiscussion", backref="task", lazy=True)
    parent_task_id = db.Column(db.Integer, db.ForeignKey("task.id"))
    subtasks = db.relationship(
        "Task", backref=db.backref("parent_task", remote_side=[id]), lazy=True
    )

    def __repr__(self):
        return f"<Task {self.title}>"


class TaskDiscussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

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


# Create the tables if they don't exist
with app.app_context():
    db.create_all()


# Routes
@app.route("/")
def home():
    tasks = Task.query.all()
    return render_template("home.html", tasks=tasks)


@app.route("/tasks/create", methods=["GET", "POST"])
def create_task():
    if request.method == "POST":
        # Logic to handle form submission and create the task
        title = request.form["title"]
        client = request.form["client"]
        worker = request.form["worker"]
        task = Task(title=title, client=client, worker=worker)
        # Save the task to the database
        db.session.add(task)
        db.session.commit()

        return redirect(url_for("home"))

    # Render the task creation form
    return render_template("create_task.html")


@app.route("/users/create", methods=["GET", "POST"])
def create_user():
    if request.method == "POST":
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
