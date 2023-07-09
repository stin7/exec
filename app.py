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
    description = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<Task {self.title}>"


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
        description = request.form["description"]
        task = Task(title=title, description=description)
        # Save the task to the database
        db.session.add(task)
        db.session.commit()

        return redirect(url_for("home"))

    # Render the task creation form
    return render_template("create_task.html")


if __name__ == "__main__":
    app.run(port=8007)
