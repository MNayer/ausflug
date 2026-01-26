import sqlite3
import os

db_path = "app.db"

def upgrade():
    if not os.path.exists(db_path):
        print("Database not found.")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE trip ADD COLUMN multiday_data TEXT DEFAULT '[]'")
        print("Column multiday_data added.")
    except sqlite3.OperationalError as e:
        print(f"Error (maybe column exists): {e}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade()
