from app import db

def upgrade():
    # Add viewed column to exam_result table
    with db.engine.connect() as conn:
        conn.execute('ALTER TABLE exam_result ADD COLUMN viewed BOOLEAN DEFAULT FALSE')
