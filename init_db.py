from app import app, db, User, Exam, Question, ExamResult, create_sample_data
import os

def init_db():
    # Make sure we're in the right directory
    if not os.path.exists('instance'):
        os.makedirs('instance')
    
    # Remove the existing database
    if os.path.exists('instance/exam.db'):
        os.remove('instance/exam.db')
    
    # Create all tables and sample data
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")
        create_sample_data()

if __name__ == '__main__':
    init_db()
