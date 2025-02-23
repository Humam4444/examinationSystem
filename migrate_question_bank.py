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

    # Create question_folder table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS question_folder (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        parent_id INTEGER,
        created_by INTEGER NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES question_folder(id),
        FOREIGN KEY (created_by) REFERENCES user(id)
    )
    """)

    # Create temporary table with new schema
    cursor.execute("""
    CREATE TABLE question_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER,
        folder_id INTEGER,
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
        FOREIGN KEY (folder_id) REFERENCES question_folder(id),
        FOREIGN KEY (created_by) REFERENCES user(id)
    )
    """)

    # Transfer existing data
    for question in existing_questions:
        # Create a dict of existing data
        question_data = dict(zip(column_names, question))
        
        # Get the exam creator as the question creator
        if 'exam_id' in question_data:
            cursor.execute("SELECT creator_id FROM exam WHERE id = ?", (question_data['exam_id'],))
            creator = cursor.fetchone()
            created_by = creator[0] if creator else 1
        else:
            created_by = 1

        # Insert into new table with default values for new columns
        cursor.execute("""
        INSERT INTO question_new (
            id, exam_id, folder_id, question_text, question_type,
            correct_answer, points, options, difficulty_level,
            subject_tags, created_by, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            question_data['id'],
            question_data.get('exam_id'),
            None,  # folder_id is initially null
            question_data['question_text'],
            question_data['question_type'],
            question_data.get('correct_answer', ''),
            question_data['points'],
            question_data.get('options'),
            'medium',  # default difficulty level
            '',  # default empty subject tags
            created_by,
            datetime.utcnow().isoformat()
        ))

    # Drop old table and rename new table
    cursor.execute("DROP TABLE question")
    cursor.execute("ALTER TABLE question_new RENAME TO question")

    # Create indexes for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_question_folder_id ON question(folder_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_question_created_by ON question(created_by)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_question_type ON question(question_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_question_difficulty ON question(difficulty_level)")

    # Commit changes and close connection
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("Starting database migration...")
    migrate_database()
    print("Database migration completed successfully!")
