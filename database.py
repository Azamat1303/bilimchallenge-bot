import sqlite3

DB_NAME = "bilimchallenge.db"

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.create_tables()
        

    def create_tables(self):
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT DEFAULT '',
                first_name  TEXT DEFAULT '',
                coins       REAL DEFAULT 0,
                total_ans   INTEGER DEFAULT 0,
                correct_ans INTEGER DEFAULT 0,
                streak      INTEGER DEFAULT 0,
                max_streak  INTEGER DEFAULT 0,
                join_date   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT UNIQUE NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                text        TEXT NOT NULL,
                q_type      TEXT NOT NULL,
                options     TEXT DEFAULT '',
                correct     TEXT NOT NULL,
                coins       REAL DEFAULT 5,
                category    TEXT DEFAULT 'Umumiy',
                difficulty  TEXT DEFAULT 'orta',
                explanation TEXT DEFAULT '',
                image_id    TEXT DEFAULT '',
                is_active   INTEGER DEFAULT 1
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS answers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                question_id INTEGER,
                is_correct  INTEGER,
                answered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, question_id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER,
                first_name TEXT DEFAULT '',
                username   TEXT DEFAULT '',
                text       TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_read    INTEGER DEFAULT 0
            )
        """)

        self.conn.commit()
        """Eski bazaga yangi ustunlar qo'shish"""
        cur = self.conn.cursor()
        try:
            cur.execute("ALTER TABLE questions ADD COLUMN image_id TEXT DEFAULT ''")
            self.conn.commit()
        except:
            pass
        try:
            cur.execute("ALTER TABLE questions ADD COLUMN difficulty TEXT DEFAULT 'orta'")
            self.conn.commit()
        except:
            pass
        try:
            cur.execute("ALTER TABLE questions ADD COLUMN explanation TEXT DEFAULT ''")
            self.conn.commit()
        except:
            pass
        try:
            cur.execute("ALTER TABLE users ADD COLUMN streak INTEGER DEFAULT 0")
            cur.execute("ALTER TABLE users ADD COLUMN max_streak INTEGER DEFAULT 0")
            self.conn.commit()
        except:
            pass

    # ── CATEGORIES ────────────────────────────────────────────────────────────
    def get_categories(self):
        cur = self.conn.execute("SELECT name FROM categories ORDER BY name")
        db_cats = [r[0] for r in cur.fetchall()]
        # Savollardagi kategoriyalarni ham qo'shish
        cur2 = self.conn.execute("SELECT DISTINCT category FROM questions WHERE is_active=1")
        q_cats = [r[0] for r in cur2.fetchall()]
        all_cats = list(dict.fromkeys(db_cats + q_cats))
        return all_cats

    def get_categories_with_count(self):
        cats = self.get_categories()
        result = []
        for cat in cats:
            cur = self.conn.execute(
                "SELECT COUNT(*) FROM questions WHERE is_active=1 AND category=?", (cat,)
            )
            count = cur.fetchone()[0]
            result.append((cat, count))
        return result

    def add_category(self, name):
        try:
            self.conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
            self.conn.commit()
        except:
            pass

    def delete_category(self, name):
        self.conn.execute("DELETE FROM categories WHERE name=?", (name,))
        self.conn.commit()

    # ── USERS ─────────────────────────────────────────────────────────────────
    def add_user(self, user_id, username, first_name):
        self.conn.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
        """, (user_id, username, first_name))
        self.conn.commit()

    def get_user(self, user_id):
        cur = self.conn.execute(
            "SELECT user_id, username, first_name, coins, total_ans, correct_ans, streak, max_streak, join_date FROM users WHERE user_id=?",
            (user_id,)
        )
        return cur.fetchone()

    def add_coins(self, user_id, amount):
        self.conn.execute(
            "UPDATE users SET coins = MAX(0, coins + ?) WHERE user_id = ?",
            (amount, user_id)
        )
        self.conn.commit()

    def update_streak(self, user_id, is_correct):
        user = self.get_user(user_id)
        if not user:
            return 0
        current_streak = user[6]
        if is_correct:
            new_streak = current_streak + 1
            max_streak = max(user[7], new_streak)
            self.conn.execute(
                "UPDATE users SET streak=?, max_streak=? WHERE user_id=?",
                (new_streak, max_streak, user_id)
            )
            self.conn.commit()
            return new_streak
        else:
            self.conn.execute("UPDATE users SET streak=0 WHERE user_id=?", (user_id,))
            self.conn.commit()
            return 0

    def get_leaderboard(self, limit=10):
        cur = self.conn.execute(
            "SELECT user_id, first_name, username, coins FROM users ORDER BY coins DESC LIMIT ?",
            (limit,)
        )
        return cur.fetchall()

    def get_user_rank(self, user_id):
        cur = self.conn.execute(
            "SELECT COUNT(*)+1 FROM users WHERE coins > (SELECT COALESCE((SELECT coins FROM users WHERE user_id=?),0))",
            (user_id,)
        )
        row = cur.fetchone()
        return row[0] if row else 0

    def get_total_users(self):
        return self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def get_active_users(self):
        return self.conn.execute("SELECT COUNT(*) FROM users WHERE total_ans > 0").fetchone()[0]

    # ── QUESTIONS ─────────────────────────────────────────────────────────────
    def add_question(self, text, q_type, options, correct, coins, category, difficulty, explanation, image_id=""):
        self.conn.execute("""
            INSERT INTO questions (text, q_type, options, correct, coins, category, difficulty, explanation, image_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (text, q_type, options, correct, coins, category, difficulty, explanation, image_id))
        self.conn.commit()
        self.add_category(category)

    def get_random_question(self, user_id, category=None):
        answered = self.conn.execute(
            "SELECT question_id FROM answers WHERE user_id=?", (user_id,)
        ).fetchall()
        answered_ids = [r[0] for r in answered]

        base = "SELECT id, text, q_type, options, correct, coins, category, difficulty, explanation, image_id FROM questions WHERE is_active=1"

        if category and category != "Barchasi":
            base += " AND category=?"
            params = [category]
        else:
            params = []

        if answered_ids:
            placeholders = ",".join("?" * len(answered_ids))
            base += f" AND id NOT IN ({placeholders})"
            params += answered_ids

        base += " ORDER BY RANDOM() LIMIT 1"
        cur = self.conn.execute(base, params)
        return cur.fetchone()

    def get_question_by_id(self, q_id):
        cur = self.conn.execute(
            "SELECT id, text, q_type, options, correct, coins, category, difficulty, explanation, image_id FROM questions WHERE id=?",
            (q_id,)
        )
        return cur.fetchone()

    def update_question_field(self, q_id, field, value):
        allowed = ["text", "options", "correct", "coins", "category", "difficulty", "explanation", "image_id"]
        if field not in allowed:
            return
        self.conn.execute(f"UPDATE questions SET {field}=? WHERE id=?", (value, q_id))
        self.conn.commit()

    def get_all_questions(self):
        cur = self.conn.execute(
            "SELECT id, text, q_type, options, correct, coins, category, difficulty FROM questions WHERE is_active=1 ORDER BY id DESC"
        )
        return cur.fetchall()

    def delete_question(self, q_id):
        self.conn.execute("UPDATE questions SET is_active=0 WHERE id=?", (q_id,))
        self.conn.commit()

    # ── ANSWERS ───────────────────────────────────────────────────────────────
    def save_answer(self, user_id, question_id, is_correct):
        try:
            self.conn.execute("""
                INSERT INTO answers (user_id, question_id, is_correct)
                VALUES (?, ?, ?)
            """, (user_id, question_id, int(is_correct)))
            self.conn.execute("""
                UPDATE users SET total_ans=total_ans+1, correct_ans=correct_ans+?
                WHERE user_id=?
            """, (int(is_correct), user_id))
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass

    def already_answered(self, user_id, question_id):
        cur = self.conn.execute(
            "SELECT 1 FROM answers WHERE user_id=? AND question_id=?",
            (user_id, question_id)
        )
        return cur.fetchone() is not None

    # ── STATS ─────────────────────────────────────────────────────────────────
    def get_stats(self):
        users = self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        questions = self.conn.execute("SELECT COUNT(*) FROM questions WHERE is_active=1").fetchone()[0]
        answers = self.conn.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
        correct = self.conn.execute("SELECT COUNT(*) FROM answers WHERE is_correct=1").fetchone()[0]
        accuracy = round((correct / answers * 100), 1) if answers > 0 else 0
        return {"users": users, "questions": questions, "answers": answers, "correct": correct, "accuracy": accuracy}

    # ── FEEDBACKS ─────────────────────────────────────────────────────────────
    def save_feedback(self, user_id, first_name, username, text):
        self.conn.execute(
            "INSERT INTO feedbacks (user_id, first_name, username, text) VALUES (?, ?, ?, ?)",
            (user_id, first_name, username, text)
        )
        self.conn.commit()

    def get_feedbacks(self, limit=50):
        cur = self.conn.execute(
            "SELECT id, user_id, first_name, username, text, created_at, is_read FROM feedbacks ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return cur.fetchall()

    def mark_feedbacks_read(self):
        self.conn.execute("UPDATE feedbacks SET is_read=1")
        self.conn.commit()

db = Database()
