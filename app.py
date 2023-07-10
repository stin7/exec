from datetime import datetime
from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy

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
    result_file = db.Column(db.String(256))

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
    name = db.Column(db.String(128), nullable=False)
    # ... additional user fields and relationships


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
        task = Task(title=title)
        # Save the task to the database
        db.session.add(task)
        db.session.commit()

        return redirect(url_for("home"))

    # Render the task creation form
    return render_template("create_task.html")


if __name__ == "__main__":
    app.run(port=8007)
