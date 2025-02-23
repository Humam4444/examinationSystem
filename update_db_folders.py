from app import app, db, QuestionFolder
from flask_migrate import Migrate

migrate = Migrate(app, db)

def update_database():
    with app.app_context():
        # Create the question_folder table
        db.create_all()
        print("Database updated successfully!")

if __name__ == "__main__":
    update_database()
