from flask import Blueprint, render_template, request, redirect, url_for

# Create a blueprint for the routes
bp = Blueprint("routes", __name__)


# Define the routes
@bp.route("/")
def home():
    return "Welcome to Exec!"


@bp.route("/tasks/create", methods=["GET", "POST"])
def create_task():
    if request.method == "POST":
        # Logic to handle form submission and create the task
        # ...
        return redirect(url_for("routes.home"))

    # Render the task creation form
    return render_template("create_task.html")


# Register the blueprint
from app import app

app.register_blueprint(bp)
