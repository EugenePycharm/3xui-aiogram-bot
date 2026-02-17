import sqlite3
import os

db_path = 'db.sqlite3'

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN received_bonus BOOLEAN DEFAULT 0")
        conn.commit()
        print("Successfully added received_bonus column to users table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column received_bonus already exists.")
        else:
            print(f"Error: {e}")
    finally:
        conn.close()
else:
    print("Database file not found.")
