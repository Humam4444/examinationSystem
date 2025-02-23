import sqlite3
from datetime import datetime

def migrate_database():
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()

    # Backup existing questions
    cursor.execute("SELECT * FROM question")
    existing_questions = cursor.fetchall()

    # Get column names
    cursor.execute("PRAGMA table_info(question)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]

    # Create temporary table with new schema
    cursor.execute("""
    CREATE TABLE question_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL,
        question_text VARCHAR(500) NOT NULL,
        question_type VARCHAR(20) NOT NULL,
        correct_answer VARCHAR(500) NOT NULL,
        points INTEGER NOT NULL,
        options BLOB,
        difficulty_level VARCHAR(20) NOT NULL DEFAULT 'medium',
        subject_tags VARCHAR(200),
        created_by INTEGER NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (exam_id) REFERENCES exam(id),
        FOREIGN KEY (created_by) REFERENCES user(id)
    )
    """)

    # Transfer existing data
    for question in existing_questions:
        # Create a dict of existing data
        question_data = dict(zip(column_names, question))
        
        # Insert into new table with default values for new columns
        cursor.execute("""
        INSERT INTO question_new (
            id, exam_id, question_text, question_type, correct_answer, 
            points, options, difficulty_level, subject_tags, created_by, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            question_data['id'],
            question_data['exam_id'],
            question_data['question_text'],
            question_data['question_type'],
            question_data.get('correct_answer', ''),  # Default empty string if not exists
            question_data['points'],
            question_data.get('options', None),  # Default None if not exists
            'medium',  # Default difficulty level
            '',  # Default empty subject tags
            question_data.get('exam_id', 1),  # Using exam creator as default created_by
            datetime.utcnow().isoformat()  # Current timestamp for created_at
        ))

    # Drop old table and rename new table
    cursor.execute("DROP TABLE question")
    cursor.execute("ALTER TABLE question_new RENAME TO question")

    # Commit changes and close connection
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("Starting database migration...")
    migrate_database()
    print("Database migration completed successfully!")
