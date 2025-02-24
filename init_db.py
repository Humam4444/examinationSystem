from app import app, db, User, Exam, Question, ExamResult, create_sample_data
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def init_db():
    try:
        with app.app_context():
            # Drop all tables first to ensure clean state
            db.drop_all()
            print("Dropped all existing tables.")
            
            # Create all tables
            db.create_all()
            print("Database tables created successfully!")
            
            # Create sample data only if we're in development
            if os.environ.get('FLASK_ENV') == 'development':
                try:
                    create_sample_data()
                    print("Sample data created for development environment!")
                except Exception as e:
                    print(f"Error creating sample data: {str(e)}")
            else:
                # Create admin user for production
                try:
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
                    else:
                        print("Admin user already exists.")
                except Exception as e:
                    print(f"Error creating admin user: {str(e)}")
                    db.session.rollback()
    except Exception as e:
        print(f"Database initialization error: {str(e)}")
        raise

if __name__ == '__main__':
    init_db()
