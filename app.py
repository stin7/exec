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
from pubsub import pub

from config import config
from prompts.prompts import AgentOODA, ManagerOODA, ClientOODA
import tools

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


# create and register a pubsub listener
def task_listener(task_id, user_ids):
    print("Function listener1 received:")
    print(f"task_id: {task_id}")
    # Get the task from the database
    task = Task.query.get(task_id)

    # Get the users from the database
    users = User.query.filter(User.id.in_(user_ids)).all()
    print(f"users: {users}")
    for user in users:
        if user.username == "managerai":
            ai = ManagerAI()
            ai.handle_task(task=task, as_user=user)


pub.subscribe(task_listener, "tasks")


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
        result = f"Task title:{self.title}\n"

        for discussion in self.discussion:
            result += str(discussion)
        return result

    def add_message(self, user_id, message_text):
        message = TaskDiscussion(task_id=self.id, user_id=user_id, message=message_text)
        db.session.add(message)
        db.session.commit()
        # Publish a message to the task's pubsub topic
        user_ids_to_notify = [self.client_id, self.worker_id]
        # remove user that sent the message
        user_ids_to_notify.remove(user_id)
        pub.sendMessage("tasks", task_id=self.id, user_ids=user_ids_to_notify)

    def add_subtask(self, title, client_id, worker_id=None):
        if worker_id is not None:
            subtask = Task(
                title=title,
                client_id=client_id,
                worker_id=worker_id,
                parent_task_id=self.id,
            )
        else:
            subtask = Task(title=title, client_id=client_id, parent_task_id=self.id)
        db.session.add(subtask)
        db.session.commit()
        return subtask


class TaskDiscussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        username = User.query.get(self.user_id).username
        # determine Role, can be client, worker, or other
        if self.user_id == Task.query.get(self.task_id).client_id:
            role = "Client"
        elif self.user_id == Task.query.get(self.task_id).worker_id:
            role = "Worker"
        else:
            role = None
        return f"{self.timestamp} : {username} ({role}) : {self.message}\n"


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


class AgentAI(object):
    """An AI that takes on small tasks"""

    def handle_task(self, task, as_user):
        """Given a task, complete an OODA loop on the task"""
        ooda = AgentOODA(str(task))
        print(f"OODA: {ooda}")
        # Parse the action, separating out ACTION_NAME and ARGUMENT
        action_name = ooda.action.split("(")[0]
        print(f"action_name: {action_name}")
        argument = ooda.action.split("(")[1].split(")")[0]
        print(f"argument: {argument}")
        if action_name == "MESSAGE_CLIENT":
            task.add_message(user_id=as_user.id, message_text=argument)
        elif action_name == "SEARCH_WEB":
            result = tools.get_organic_search_results(argument)
            task.add_message(user_id=as_user.id, message_text=str(result))
        elif action_name == "ACCESS_URL":
            markdown = tools.get_markdown_from_url(argument)
            task.add_message(user_id=as_user.id, message_text=markdown)
        else:
            raise NotImplementedError(f"Action {action_name} is not implemented for AI")


class ManagerAI(object):
    """An AI that manages Agent AIs to complete a Client task"""

    def handle_task_as_worker(self, task, as_user):
        """Given a task, complete an OODA loop on the task"""
        ooda = ManagerOODA(str(task))
        print(f"OODA: {ooda}")
        # Parse the action, separating out ACTION_NAME and ARGUMENT
        action_name = ooda.action.split("(")[0]
        print(f"action_name: {action_name}")
        argument = ooda.action.split("(")[1].split(")")[0]
        print(f"argument: {argument}")
        if action_name == "MESSAGE_CLIENT":
            task.add_message(user_id=as_user.id, message_text=argument)
        elif action_name == "CREATE_PLAN":
            task.add_message(user_id=as_user.id, message_text=argument)
        elif action_name == "CREATE_SUBTASK":
            # Get the agent AI
            agent_ai = User.query.filter_by(username="agentai").first()
            task.add_subtask(
                title=argument, client_id=as_user.id, worker_id=agent_ai.id
            )
        else:
            raise NotImplementedError(f"Action {action_name} is not implemented for AI")

    def handle_task_as_client(self, task, as_user):
        """Given a task, complete an OODA loop on the task"""
        ooda = ClientOODA(str(task))
        print(f"OODA: {ooda}")
        # Parse the action, separating out ACTION_NAME and ARGUMENT
        action_name = ooda.action.split("(")[0]
        print(f"action_name: {action_name}")
        argument = ooda.action.split("(")[1].split(")")[0]
        print(f"argument: {argument}")
        if action_name == "MESSAGE_WORKER":
            task.add_message(user_id=as_user.id, message_text=argument)
        else:
            raise NotImplementedError(f"Action {action_name} is not implemented for AI")

    def handle_task(self, task, as_user):
        # determine if the user is the client or worker
        if as_user.id == task.client_id:
            self.handle_task_as_client(task=task, as_user=as_user)
        elif as_user.id == task.worker_id:
            self.handle_task_as_worker(task=task, as_user=as_user)


# TODO: Create TaskAgents that act directly on behalf of the client (calendar, email, etc.) Basically anthying that requires authorization or a PUT request that will change state.


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
        # get the manager AI
        mngr_ai = User.query.filter_by(username="managerai").first()
        task = Task(title=title, client_id=current_user.id, worker_id=mngr_ai.id)
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

    parent_task.add_subtask(title=title, client_id=current_user.id)

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
