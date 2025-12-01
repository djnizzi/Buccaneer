import sqlite3
import os

PATHS = [
    r'C:\Users\djniz\AppData\Roaming\MediaMonkey5\MM.DB',
    r'C:\Users\djniz\AppData\Roaming\MediaMonkey5\MM5.DB',
    r'C:\Users\djniz\AppData\Roaming\MediaMonkey 5\MM.DB',
    r'C:\Users\djniz\AppData\Roaming\MediaMonkey 5\MM5.DB'
]

def inspect_schema():
    db_path = None
    for path in PATHS:
        if os.path.exists(path):
            db_path = path
            print(f"Found DB at: {db_path}")
            break
    
    if not db_path:
        print("DB not found in common locations.")
        return

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("\n--- Columns in Songs Table ---")
        cursor.execute("PRAGMA table_info(Songs)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"{col['cid']}: {col['name']} ({col['type']})")
        print("-" * 40)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    inspect_schema()
