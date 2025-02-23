from app import app, create_sample_data

with app.app_context():
    create_sample_data()
