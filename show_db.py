import sqlite3
from pprint import pprint
import sys

# Set console to UTF-8 mode
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def show_database_contents():
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("\n=== Database Tables ===")
    for table in tables:
        table_name = table[0]
        print(f"\n[Table: {table_name}]")
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print("Columns:", [col[1] for col in columns])
        
        # Get all rows
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        print(f"Number of rows: {len(rows)}")
        print("\nData:")
        for row in rows:
            try:
                print(row)
            except UnicodeEncodeError:
                # Convert problematic items to strings explicitly
                formatted_row = []
                for item in row:
                    if isinstance(item, str):
                        formatted_row.append(item.encode('utf-8').decode('utf-8'))
                    else:
                        formatted_row.append(str(item))
                print(tuple(formatted_row))
        print("-" * 50)
    
    conn.close()

if __name__ == "__main__":
    show_database_contents()
