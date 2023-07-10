from app import app, db, User


def create_user(username, email, password, is_admin=False):
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username, email=email, is_admin=is_admin)
        user.password = password
        db.session.add(user)
        db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        # Create the tables if they don't exist
        db.create_all()

        create_user("admin", "admin@example.com", "adminpassword", True)
        create_user("alice", "alice@example.com", "alicepassword")
        create_user("ai", "ai@example.com", "aipassword")
