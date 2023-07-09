import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "your-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    # Update the database URI for your PostgreSQL database
    SQLALCHEMY_DATABASE_URI = "postgresql://username:password@localhost/db_name"


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    # Add more configurations as needed
}
