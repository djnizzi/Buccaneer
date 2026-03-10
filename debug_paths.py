import sqlite3

DB_PATH = r'C:\Users\djniz\AppData\Roaming\MediaMonkey5\MM5.DB'

def check_paths():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- First 20 Paths in DB ---")
    cursor.execute("SELECT SongPath FROM Songs LIMIT 20")
    for row in cursor.fetchall():
        print(row['SongPath'])

    print("\n--- Checking for 'Y:' ---")
    cursor.execute("SELECT COUNT(*) FROM Songs WHERE SongPath LIKE '%Y:%'")
    print(f"Count with Y: {cursor.fetchone()[0]}")

    conn.close()

if __name__ == "__main__":
    check_paths()
