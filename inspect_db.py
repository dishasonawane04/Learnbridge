import sqlite3

try:
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='ai_tutor_chat'")
    result = cursor.fetchone()
    if result:
        print("Schema for ai_tutor_chat:")
        print(result[0])
    else:
        print("Table ai_tutor_chat not found.")
    conn.close()
except Exception as e:
    print(e)
