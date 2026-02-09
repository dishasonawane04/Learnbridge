import sqlite3

try:
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    # Disable foreign keys to allow dropping tables out of order
    cursor.execute("PRAGMA foreign_keys = OFF;")
    
    print("Dropping ai_tutor_chatmessage...")
    cursor.execute("DROP TABLE IF EXISTS ai_tutor_chatmessage")
    
    print("Dropping ai_tutor_chat...")
    cursor.execute("DROP TABLE IF EXISTS ai_tutor_chat")
    
    conn.commit()
    print("Tables dropped successfully.")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
