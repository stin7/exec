from flask import Flask

# Initialize the Flask application
app = Flask(__name__)

# Import the routes module after initializing the Flask app
from app import routes

# Add any other necessary configurations
# ...
