import sqlite3

DB_NAME = "bilimchallenge.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Mavjud test savollari jadvali
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        options TEXT NOT NULL,
        correct TEXT NOT NULL
    )
    """)
    
    # YANGI: Listening savollari jadvali
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listening_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        audio_file_id TEXT NOT NULL,
        question_text TEXT,
        image_file_id TEXT,
        options TEXT NOT NULL,
        correct TEXT NOT NULL
    )
    """)
    
    # Foydalanuvchilar jadvali
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        score INTEGER DEFAULT 0,
        listening_score INTEGER DEFAULT 0
    )
    """)
    
    conn.commit()
    conn.close()

# ---- Eski Test funksiyalari (O'zgarishsiz qoldi) ----
def add_question(text, options, correct):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO questions (text, options, correct) VALUES (?, ?, ?)", (text, options, correct))
    conn.commit()
    conn.close()

def get_all_questions():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, text, options, correct FROM questions")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_question(q_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions WHERE id = ?", (q_id,))
    conn.commit()
    conn.close()

# ---- YANGI: Listening funksiyalari ----
def add_listening_question(audio_id, text, image_id, options, correct):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO listening_questions (audio_file_id, question_text, image_file_id, options, correct) 
        VALUES (?, ?, ?, ?, ?)
    """, (audio_id, text, image_id, options, correct))
    conn.commit()
    conn.close()

def get_all_listening_questions():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, audio_file_id, question_text, image_file_id, options, correct FROM listening_questions")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_listening_question(q_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM listening_questions WHERE id = ?", (q_id,))
    conn.commit()
    conn.close()

# ---- Foydalanuvchi ballari funksiyalari ----
def add_user(user_id, username, full_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)", (user_id, username, full_name))
    conn.commit()
    conn.close()

def update_score(user_id, points=1):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET score = score + ? WHERE user_id = ?", (points, user_id))
    conn.commit()
    conn.close()

def update_listening_score(user_id, points=1):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET listening_score = listening_score + ? WHERE user_id = ?", (points, user_id))
    conn.commit()
    conn.close()

def get_leaderboard():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Umumiy reyting (Oddiy test + Listening test ballari qo'shib hisoblanadi)
    cursor.execute("SELECT full_name, (score + listening_score) FROM users ORDER BY (score + listening_score) DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    return rows
