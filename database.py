import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.conn.autocommit = True
        self.create_tables()

    def get_conn(self):
        try:
            self.conn.cursor().execute("SELECT 1")
        except:
            self.conn = psycopg2.connect(DATABASE_URL)
            self.conn.autocommit = True
        return self.conn

    def create_tables(self):
        cur = self.get_conn().cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     BIGINT PRIMARY KEY,
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
                id   SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id          SERIAL PRIMARY KEY,
                text        TEXT NOT NULL,
                q_type      TEXT NOT NULL,
                options     TEXT DEFAULT '',
                correct     TEXT NOT NULL DEFAULT '',
                coins       REAL DEFAULT 5,
                category    TEXT DEFAULT 'Umumiy',
                difficulty  TEXT DEFAULT 'orta',
                explanation TEXT DEFAULT '',
                image_id    TEXT DEFAULT '',
                time_limit  TEXT DEFAULT '',
                is_active   INTEGER DEFAULT 1
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS answers (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT,
                question_id INTEGER,
                is_correct  INTEGER,
                answered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, question_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id         SERIAL PRIMARY KEY,
                user_id    BIGINT,
                first_name TEXT DEFAULT '',
                username   TEXT DEFAULT '',
                text       TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_read    INTEGER DEFAULT 0
            )
        """)
        # Migrate: add time_limit column if not exists
        try:
            cur.execute("ALTER TABLE questions ADD COLUMN time_limit TEXT DEFAULT ''")
        except:
            pass

    # ── USERS ─────────────────────────────────────────────────────────────────
    def add_user(self, user_id, username, first_name):
        cur = self.get_conn().cursor()
        cur.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (%s, %s, %s) ON CONFLICT (user_id) DO NOTHING
        """, (user_id, username, first_name))

    def get_user(self, user_id):
        cur = self.get_conn().cursor()
        cur.execute(
            "SELECT user_id, username, first_name, coins, total_ans, correct_ans, streak, max_streak, join_date FROM users WHERE user_id=%s",
            (user_id,)
        )
        return cur.fetchone()

    def add_coins(self, user_id, amount):
        cur = self.get_conn().cursor()
        # Minus bo'lishiga ruxsat beramiz
        cur.execute("UPDATE users SET coins = coins + %s WHERE user_id = %s", (amount, user_id))

    def update_streak(self, user_id, is_correct):
        user = self.get_user(user_id)
        if not user: return 0
        cur = self.get_conn().cursor()
        if is_correct:
            new_streak = user[6] + 1
            max_streak = max(user[7], new_streak)
            cur.execute("UPDATE users SET streak=%s, max_streak=%s WHERE user_id=%s", (new_streak, max_streak, user_id))
            return new_streak
        else:
            cur.execute("UPDATE users SET streak=0 WHERE user_id=%s", (user_id,))
            return 0

    def get_leaderboard(self, limit=10):
        cur = self.get_conn().cursor()
        cur.execute("SELECT user_id, first_name, username, coins FROM users ORDER BY coins DESC LIMIT %s", (limit,))
        return cur.fetchall()

    def get_user_rank(self, user_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT COUNT(*)+1 FROM users WHERE coins > (SELECT COALESCE((SELECT coins FROM users WHERE user_id=%s),0))", (user_id,))
        row = cur.fetchone()
        return row[0] if row else 0

    def get_total_users(self): 
        cur = self.get_conn().cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        return cur.fetchone()[0]

    def get_active_users(self):
        cur = self.get_conn().cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE total_ans > 0")
        return cur.fetchone()[0]

    def get_all_user_ids(self):
        cur = self.get_conn().cursor()
        cur.execute("SELECT user_id FROM users")
        return [r[0] for r in cur.fetchall()]

    # ── CATEGORIES ────────────────────────────────────────────────────────────
    def get_categories(self):
        cur = self.get_conn().cursor()
        cur.execute("SELECT name FROM categories ORDER BY name")
        db_cats = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT category FROM questions WHERE is_active=1 AND q_type NOT IN ('writing','essay','reading','speaking')")
        q_cats = [r[0] for r in cur.fetchall()]
        return list(dict.fromkeys(db_cats + q_cats))

    def get_categories_with_count(self):
        cats = self.get_categories()
        result = []
        cur = self.get_conn().cursor()
        for cat in cats:
            cur.execute("SELECT COUNT(*) FROM questions WHERE is_active=1 AND category=%s", (cat,))
            count = cur.fetchone()[0]
            result.append((cat, count))
        return result

    def add_category(self, name):
        cur = self.get_conn().cursor()
        try:
            cur.execute("INSERT INTO categories (name) VALUES (%s) ON CONFLICT DO NOTHING", (name,))
        except: pass

    def delete_category(self, name):
        cur = self.get_conn().cursor()
        cur.execute("DELETE FROM categories WHERE name=%s", (name,))

    # ── QUESTIONS ─────────────────────────────────────────────────────────────
    def add_question(self, text, q_type, options, correct, coins, category, difficulty, explanation, image_id="", time_limit=""):
        cur = self.get_conn().cursor()
        cur.execute("""
            INSERT INTO questions (text, q_type, options, correct, coins, category, difficulty, explanation, image_id, time_limit)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (text, q_type, options, correct, coins, category, difficulty, explanation, image_id, time_limit))
        if q_type not in ('writing', 'essay', 'reading', 'speaking'):
            self.add_category(category)

    def get_random_question(self, user_id, category=None, q_type=None):
        cur = self.get_conn().cursor()
        cur.execute("SELECT question_id FROM answers WHERE user_id=%s", (user_id,))
        answered_ids = [r[0] for r in cur.fetchall()]
        conditions = ["is_active=1"]
        params = []
        if category and category != "Barchasi":
            conditions.append("category=%s")
            params.append(category)
        if q_type:
            if isinstance(q_type, list):
                conditions.append("q_type = ANY(%s)")
                params.append(q_type)
            else:
                conditions.append("q_type=%s")
                params.append(q_type)
        else:
            # Oddiy savollar uchun faqat IELTS turlarini chiqarmaymiz (premium qoladi)
            conditions.append("q_type NOT IN ('writing','essay','reading','speaking','listening')")
        if answered_ids:
            conditions.append("id != ALL(%s)")
            params.append(answered_ids)
        where = " AND ".join(conditions)
        cur.execute(f"SELECT id, text, q_type, options, correct, coins, category, difficulty, explanation, image_id, time_limit FROM questions WHERE {where} ORDER BY RANDOM() LIMIT 1", params)
        return cur.fetchone()

    def get_any_question_by_type(self, q_type):
        """Answered bo'lsa ham qaytaradi — IELTS uchun"""
        cur = self.get_conn().cursor()
        cur.execute(
            "SELECT id, text, q_type, options, correct, coins, category, difficulty, explanation, image_id, time_limit FROM questions WHERE is_active=1 AND q_type=%s ORDER BY RANDOM() LIMIT 1",
            (q_type,)
        )
        return cur.fetchone()

    def get_question_by_id(self, q_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT id, text, q_type, options, correct, coins, category, difficulty, explanation, image_id, time_limit FROM questions WHERE id=%s", (q_id,))
        return cur.fetchone()

    def update_question_field(self, q_id, field, value):
        allowed = ["text", "options", "correct", "coins", "category", "difficulty", "explanation", "image_id", "time_limit"]
        if field not in allowed: return
        cur = self.get_conn().cursor()
        cur.execute(f"UPDATE questions SET {field}=%s WHERE id=%s", (value, q_id))

    def get_all_questions(self):
        cur = self.get_conn().cursor()
        cur.execute("SELECT id, text, q_type, options, correct, coins, category, difficulty FROM questions WHERE is_active=1 ORDER BY id DESC")
        return cur.fetchall()

    def delete_question(self, q_id):
        cur = self.get_conn().cursor()
        cur.execute("UPDATE questions SET is_active=0 WHERE id=%s", (q_id,))

    # ── ANSWERS ───────────────────────────────────────────────────────────────
    def save_answer(self, user_id, question_id, is_correct):
        cur = self.get_conn().cursor()
        try:
            cur.execute("INSERT INTO answers (user_id, question_id, is_correct) VALUES (%s, %s, %s) ON CONFLICT (user_id, question_id) DO NOTHING", (user_id, question_id, int(is_correct)))
            cur.execute("UPDATE users SET total_ans=total_ans+1, correct_ans=correct_ans+%s WHERE user_id=%s", (int(is_correct), user_id))
        except: pass

    def already_answered(self, user_id, question_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT 1 FROM answers WHERE user_id=%s AND question_id=%s", (user_id, question_id))
        return cur.fetchone() is not None

    # ── FEEDBACKS ─────────────────────────────────────────────────────────────
    def save_feedback(self, user_id, first_name, username, text):
        cur = self.get_conn().cursor()
        cur.execute("INSERT INTO feedbacks (user_id, first_name, username, text) VALUES (%s, %s, %s, %s)", (user_id, first_name, username, text))

    def get_feedbacks(self, limit=50):
        cur = self.get_conn().cursor()
        cur.execute("SELECT id, user_id, first_name, username, text, created_at, is_read FROM feedbacks ORDER BY created_at DESC LIMIT %s", (limit,))
        return cur.fetchall()

    def delete_feedback(self, fb_id):
        cur = self.get_conn().cursor()
        cur.execute("DELETE FROM feedbacks WHERE id=%s", (fb_id,))

    def mark_feedbacks_read(self):
        cur = self.get_conn().cursor()
        cur.execute("DELETE FROM feedbacks WHERE is_read=1")
        cur.execute("UPDATE feedbacks SET is_read=1")

    # ── STATS ─────────────────────────────────────────────────────────────────
    def get_stats(self):
        cur = self.get_conn().cursor()
        cur.execute("SELECT COUNT(*) FROM users"); users = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM questions WHERE is_active=1"); questions = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM answers"); answers = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM answers WHERE is_correct=1"); correct = cur.fetchone()[0]
        accuracy = round((correct / answers * 100), 1) if answers > 0 else 0
        return {"users": users, "questions": questions, "answers": answers, "correct": correct, "accuracy": accuracy}

db = Database()
