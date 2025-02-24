from app import app, db, User, Exam, Question, ExamResult, create_sample_data
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def init_db():
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Create sample data only if we're in development
        if os.environ.get('FLASK_ENV') == 'development':
            create_sample_data()
            print("Sample data created for development environment!")
        else:
            # Create admin user for production
            admin = User.query.filter_by(email='admin@example.com').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    role='admin'
                )
                admin.set_password('admin123')  # Change this password in production!
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully!")

if __name__ == '__main__':
    init_db()
