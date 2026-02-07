#!/usr/bin/env python
"""
Fix AI Tutor database schema by recreating tables
"""
import sqlite3
import os

db_path = 'db.sqlite3'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Drop existing tables if they exist
cursor.execute("DROP TABLE IF EXISTS ai_tutor_chatmessage")
cursor.execute("DROP TABLE IF EXISTS ai_tutor_chat")

# Create Chat table with correct schema
cursor.execute("""
CREATE TABLE ai_tutor_chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_key VARCHAR(40),
    title VARCHAR(255) NOT NULL DEFAULT 'New Chat',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    is_archived BOOLEAN NOT NULL DEFAULT 0,
    is_pinned BOOLEAN NOT NULL DEFAULT 0,
    share_token CHAR(32) NOT NULL UNIQUE,
    user_id INTEGER,
    unit_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE,
    FOREIGN KEY (unit_id) REFERENCES course_courseunit(id) ON DELETE SET NULL
)
""")

# Create ChatMessage table
cursor.execute("""
CREATE TABLE ai_tutor_chatmessage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender VARCHAR(10) NOT NULL,
    content TEXT,
    msg_type VARCHAR(10) NOT NULL DEFAULT 'text',
    attachment VARCHAR(100),
    created_at DATETIME NOT NULL,
    chat_id INTEGER NOT NULL,
    FOREIGN KEY (chat_id) REFERENCES ai_tutor_chat(id) ON DELETE CASCADE
)
""")

# Create indexes
cursor.execute("CREATE INDEX ai_tutor_chat_session_key_8827f32c ON ai_tutor_chat(session_key)")
cursor.execute("CREATE INDEX ai_tutor_chat_user_id_02388e18 ON ai_tutor_chat(user_id)")
cursor.execute("CREATE INDEX ai_tutor_chat_unit_id_6021adfa ON ai_tutor_chat(unit_id)")

conn.commit()
conn.close()

print("✅ AI Tutor tables created successfully!")
