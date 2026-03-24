import sqlite3
import os

DB_PATH = "campus_tasks.db"

def init_sqlite_db():
    print(f"🗄️ SQLite 데이터베이스 초기화 중... ({DB_PATH})")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        course_name TEXT NOT NULL,
        description TEXT,
        due_date DATETIME NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)
    
    conn.commit()
    conn.close()
    print("✅ SQLite 세팅 완료")

if __name__ == "__main__":
    init_sqlite_db()
