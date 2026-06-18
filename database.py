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
                join_date   TEXT DEFAULT CURRENT_TIMESTAMP,
                referrer_id BIGINT DEFAULT NULL,
                ref_count   INTEGER DEFAULT 0
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
                is_active   INTEGER DEFAULT 1,
                added_by    BIGINT DEFAULT NULL,
                is_approved INTEGER DEFAULT 1
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
                is_read    INTEGER DEFAULT 0,
                reply      TEXT DEFAULT ''
            )
        """)
        # Yordamchi adminlar jadvali
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sub_admins (
                user_id     BIGINT PRIMARY KEY,
                username    TEXT DEFAULT '',
                first_name  TEXT DEFAULT '',
                elected_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                term_end    TEXT DEFAULT '',
                salary      REAL DEFAULT 0,
                last_report TEXT DEFAULT '',
                report_count INTEGER DEFAULT 0,
                warnings    INTEGER DEFAULT 0,
                is_active   INTEGER DEFAULT 1
            )
        """)
        # Saylov jadvali
        cur.execute("""
            CREATE TABLE IF NOT EXISTS elections (
                id          SERIAL PRIMARY KEY,
                status      TEXT DEFAULT 'inactive',
                started_at  TEXT DEFAULT '',
                ends_at     TEXT DEFAULT '',
                winner_id   BIGINT DEFAULT NULL,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Ovoz berish
        cur.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id          SERIAL PRIMARY KEY,
                election_id INTEGER,
                voter_id    BIGINT,
                candidate_id BIGINT,
                voted_at    TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(election_id, voter_id)
            )
        """)
        # Nomzodlar
        cur.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id          SERIAL PRIMARY KEY,
                election_id INTEGER,
                user_id     BIGINT,
                username    TEXT DEFAULT '',
                first_name  TEXT DEFAULT '',
                confirmed   INTEGER DEFAULT 0,
                UNIQUE(election_id, user_id)
            )
        """)
        # Hisobotlar
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id          SERIAL PRIMARY KEY,
                sub_admin_id BIGINT,
                text        TEXT NOT NULL,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Moash va jarimalar
        cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id          SERIAL PRIMARY KEY,
                admin_id    BIGINT,
                target_id   BIGINT,
                amount      REAL,
                pay_type    TEXT DEFAULT 'salary',
                note        TEXT DEFAULT '',
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Kutayotgan savollar (yordamchi admin tomonidan)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pending_questions (
                id          SERIAL PRIMARY KEY,
                sub_admin_id BIGINT,
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
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                status      TEXT DEFAULT 'pending'
            )
        """)

        # Migrate: ustunlar qo'shish
        for col, typedef in [
            ("referrer_id", "BIGINT DEFAULT NULL"),
            ("ref_count", "INTEGER DEFAULT 0"),
            ("added_by", "BIGINT DEFAULT NULL"),
            ("is_approved", "INTEGER DEFAULT 1"),
            ("reply", "TEXT DEFAULT ''"),
        ]:
            try:
                if col in ["referrer_id", "ref_count"]:
                    cur.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")
                elif col in ["added_by", "is_approved"]:
                    cur.execute(f"ALTER TABLE questions ADD COLUMN {col} {typedef}")
                elif col == "reply":
                    cur.execute(f"ALTER TABLE feedbacks ADD COLUMN {col} {typedef}")
            except: pass

        try:
            cur.execute("ALTER TABLE questions ADD COLUMN time_limit TEXT DEFAULT ''")
        except: pass
        self.create_group_tables()
        self.create_duel_tables()

    # ── USERS ─────────────────────────────────────────────────────────────────
    def add_user(self, user_id, username, first_name, referrer_id=None):
        cur = self.get_conn().cursor()
        cur.execute("""
            INSERT INTO users (user_id, username, first_name, referrer_id)
            VALUES (%s, %s, %s, %s) ON CONFLICT (user_id) DO NOTHING
        """, (user_id, username, first_name, referrer_id))
        # Referal bonus
        if referrer_id:
            cur.execute("SELECT user_id FROM users WHERE user_id=%s", (user_id,))
            # Faqat yangi foydalanuvchi bo'lsa bonus berish
            cur.execute("UPDATE users SET coins=coins+30, ref_count=ref_count+1 WHERE user_id=%s", (referrer_id,))

    def get_user(self, user_id):
        cur = self.get_conn().cursor()
        cur.execute(
            "SELECT user_id, username, first_name, coins, total_ans, correct_ans, streak, max_streak, join_date FROM users WHERE user_id=%s",
            (user_id,)
        )
        return cur.fetchone()

    def get_user_full(self, user_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
        return cur.fetchone()

    def add_coins(self, user_id, amount):
        cur = self.get_conn().cursor()
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

    def get_top10_users(self):
        cur = self.get_conn().cursor()
        cur.execute("SELECT user_id, first_name, username, coins FROM users ORDER BY coins DESC LIMIT 10")
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

    def get_ref_count(self, user_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT ref_count FROM users WHERE user_id=%s", (user_id,))
        row = cur.fetchone()
        return row[0] if row else 0

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
    def add_question(self, text, q_type, options, correct, coins, category, difficulty, explanation, image_id="", time_limit="", added_by=None, is_approved=1):
        cur = self.get_conn().cursor()
        cur.execute("""
            INSERT INTO questions (text, q_type, options, correct, coins, category, difficulty, explanation, image_id, time_limit, added_by, is_approved)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (text, q_type, options, correct, coins, category, difficulty, explanation, image_id, time_limit, added_by, is_approved))
        if is_approved and q_type not in ('writing', 'essay', 'reading', 'speaking'):
            self.add_category(category)

    def get_random_question(self, user_id, category=None, q_type=None):
        cur = self.get_conn().cursor()
        cur.execute("SELECT question_id FROM answers WHERE user_id=%s", (user_id,))
        answered_ids = [r[0] for r in cur.fetchall()]
        conditions = ["is_active=1", "is_approved=1"]
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
            conditions.append("q_type NOT IN ('writing','essay','reading','speaking','listening')")
        if answered_ids:
            conditions.append("id != ALL(%s)")
            params.append(answered_ids)
        where = " AND ".join(conditions)
        cur.execute(f"SELECT id, text, q_type, options, correct, coins, category, difficulty, explanation, image_id, time_limit FROM questions WHERE {where} ORDER BY RANDOM() LIMIT 1", params)
        return cur.fetchone()

    def get_any_question_by_type(self, q_type):
        cur = self.get_conn().cursor()
        cur.execute(
            "SELECT id, text, q_type, options, correct, coins, category, difficulty, explanation, image_id, time_limit FROM questions WHERE is_active=1 AND is_approved=1 AND q_type=%s ORDER BY RANDOM() LIMIT 1",
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
        cur.execute("SELECT id, text, q_type, options, correct, coins, category, difficulty FROM questions WHERE is_active=1 AND is_approved=1 ORDER BY id DESC")
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

    def save_feedback_reply(self, fb_id, reply):
        cur = self.get_conn().cursor()
        cur.execute("UPDATE feedbacks SET reply=%s, is_read=1 WHERE id=%s", (reply, fb_id))

    def get_feedback_by_id(self, fb_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT id, user_id, first_name, username, text, created_at, is_read, reply FROM feedbacks WHERE id=%s", (fb_id,))
        return cur.fetchone()

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
        cur.execute("SELECT COUNT(*) FROM questions WHERE is_active=1 AND is_approved=1"); questions = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM answers"); answers = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM answers WHERE is_correct=1"); correct = cur.fetchone()[0]
        accuracy = round((correct / answers * 100), 1) if answers > 0 else 0
        return {"users": users, "questions": questions, "answers": answers, "correct": correct, "accuracy": accuracy}

    # ── SUB ADMINS ────────────────────────────────────────────────────────────
    def add_sub_admin(self, user_id, username, first_name, term_days=21):
        from datetime import datetime, timedelta
        term_end = (datetime.now() + timedelta(days=term_days)).strftime("%Y-%m-%d %H:%M:%S")
        cur = self.get_conn().cursor()
        cur.execute("""
            INSERT INTO sub_admins (user_id, username, first_name, term_end, is_active)
            VALUES (%s, %s, %s, %s, 1)
            ON CONFLICT (user_id) DO UPDATE SET is_active=1, term_end=%s, first_name=%s, username=%s
        """, (user_id, username, first_name, term_end, term_end, first_name, username))

    def remove_sub_admin(self, user_id):
        cur = self.get_conn().cursor()
        cur.execute("UPDATE sub_admins SET is_active=0 WHERE user_id=%s", (user_id,))

    def is_sub_admin(self, user_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT 1 FROM sub_admins WHERE user_id=%s AND is_active=1", (user_id,))
        return cur.fetchone() is not None

    def get_sub_admin(self, user_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT * FROM sub_admins WHERE user_id=%s", (user_id,))
        return cur.fetchone()

    def get_all_sub_admins(self):
        cur = self.get_conn().cursor()
        cur.execute("SELECT * FROM sub_admins WHERE is_active=1")
        return cur.fetchall()

    def set_sub_admin_salary(self, user_id, salary):
        cur = self.get_conn().cursor()
        cur.execute("UPDATE sub_admins SET salary=%s WHERE user_id=%s", (salary, user_id))

    def add_sub_admin_warning(self, user_id):
        cur = self.get_conn().cursor()
        cur.execute("UPDATE sub_admins SET warnings=warnings+1 WHERE user_id=%s", (user_id,))
        cur.execute("SELECT warnings FROM sub_admins WHERE user_id=%s", (user_id,))
        row = cur.fetchone()
        return row[0] if row else 0

    def update_last_report(self, user_id):
        from datetime import datetime
        cur = self.get_conn().cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("UPDATE sub_admins SET last_report=%s, report_count=report_count+1 WHERE user_id=%s", (now, user_id))

    # ── ELECTIONS ────────────────────────────────────────────────────────────
    def create_election(self):
        from datetime import datetime, timedelta
        cur = self.get_conn().cursor()
        # Avvalgi faol saylovni tugatamiz
        cur.execute("UPDATE elections SET status='finished' WHERE status IN ('active','nomination')")
        started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ends = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("INSERT INTO elections (status, started_at, ends_at) VALUES ('nomination', %s, %s) RETURNING id", (started, ends))
        return cur.fetchone()[0]

    def get_active_election(self):
        cur = self.get_conn().cursor()
        cur.execute("SELECT * FROM elections WHERE status IN ('active','nomination') ORDER BY id DESC LIMIT 1")
        return cur.fetchone()

    def start_voting(self, election_id):
        cur = self.get_conn().cursor()
        cur.execute("UPDATE elections SET status='active' WHERE id=%s", (election_id,))

    def finish_election(self, election_id):
        cur = self.get_conn().cursor()
        # G'olibni topish
        cur.execute("""
            SELECT candidate_id, COUNT(*) as vote_count FROM votes WHERE election_id=%s
            GROUP BY candidate_id ORDER BY vote_count DESC LIMIT 1
        """, (election_id,))
        row = cur.fetchone()
        winner_id = row[0] if row else None
        cur.execute("UPDATE elections SET status='finished', winner_id=%s WHERE id=%s", (winner_id, election_id))
        return winner_id

    def get_election_results(self, election_id):
        cur = self.get_conn().cursor()
        cur.execute("""
            SELECT c.user_id, c.first_name, c.username, COUNT(v.id) as votes
            FROM candidates c LEFT JOIN votes v ON v.candidate_id=c.user_id AND v.election_id=%s
            WHERE c.election_id=%s AND c.confirmed=1
            GROUP BY c.user_id, c.first_name, c.username ORDER BY votes DESC
        """, (election_id, election_id))
        return cur.fetchall()

    # ── CANDIDATES ────────────────────────────────────────────────────────────
    def add_candidate(self, election_id, user_id, username, first_name):
        cur = self.get_conn().cursor()
        try:
            cur.execute("INSERT INTO candidates (election_id, user_id, username, first_name, confirmed) VALUES (%s, %s, %s, %s, 0)", (election_id, user_id, username, first_name))
        except: pass

    def confirm_candidate(self, election_id, user_id):
        cur = self.get_conn().cursor()
        cur.execute("UPDATE candidates SET confirmed=1 WHERE election_id=%s AND user_id=%s", (election_id, user_id))

    def get_candidates(self, election_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT user_id, first_name, username, confirmed FROM candidates WHERE election_id=%s", (election_id,))
        return cur.fetchall()

    def get_confirmed_candidates(self, election_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT user_id, first_name, username FROM candidates WHERE election_id=%s AND confirmed=1", (election_id,))
        return cur.fetchall()

    # ── VOTES ────────────────────────────────────────────────────────────────
    def cast_vote(self, election_id, voter_id, candidate_id):
        cur = self.get_conn().cursor()
        try:
            cur.execute("INSERT INTO votes (election_id, voter_id, candidate_id) VALUES (%s, %s, %s)", (election_id, voter_id, candidate_id))
            return True
        except: return False

    def has_voted(self, election_id, voter_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT 1 FROM votes WHERE election_id=%s AND voter_id=%s", (election_id, voter_id))
        return cur.fetchone() is not None

    # ── REPORTS ──────────────────────────────────────────────────────────────
    def save_report(self, sub_admin_id, text):
        cur = self.get_conn().cursor()
        cur.execute("INSERT INTO reports (sub_admin_id, text) VALUES (%s, %s)", (sub_admin_id, text))
        self.update_last_report(sub_admin_id)

    def get_reports(self, limit=20):
        cur = self.get_conn().cursor()
        cur.execute("SELECT r.id, r.sub_admin_id, s.first_name, r.text, r.created_at FROM reports r LEFT JOIN sub_admins s ON s.user_id=r.sub_admin_id ORDER BY r.created_at DESC LIMIT %s", (limit,))
        return cur.fetchall()

    # ── PAYMENTS ─────────────────────────────────────────────────────────────
    def add_payment(self, admin_id, target_id, amount, pay_type, note=""):
        cur = self.get_conn().cursor()
        cur.execute("INSERT INTO payments (admin_id, target_id, amount, pay_type, note) VALUES (%s, %s, %s, %s, %s)", (admin_id, target_id, amount, pay_type, note))
        if pay_type == "fine":
            self.add_coins(target_id, -amount)
        else:
            self.add_coins(target_id, amount)

    def get_payments(self, target_id=None, limit=20):
        cur = self.get_conn().cursor()
        if target_id:
            cur.execute("SELECT * FROM payments WHERE target_id=%s ORDER BY created_at DESC LIMIT %s", (target_id, limit))
        else:
            cur.execute("SELECT * FROM payments ORDER BY created_at DESC LIMIT %s", (limit,))
        return cur.fetchall()

    # ── PENDING QUESTIONS ────────────────────────────────────────────────────
    def add_pending_question(self, sub_admin_id, text, q_type, options, correct, coins, category, difficulty, explanation, image_id="", time_limit=""):
        cur = self.get_conn().cursor()
        cur.execute("""
            INSERT INTO pending_questions (sub_admin_id, text, q_type, options, correct, coins, category, difficulty, explanation, image_id, time_limit)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (sub_admin_id, text, q_type, options, correct, coins, category, difficulty, explanation, image_id, time_limit))
        return cur.fetchone()[0]

    def get_pending_questions(self):
        cur = self.get_conn().cursor()
        cur.execute("SELECT * FROM pending_questions WHERE status='pending' ORDER BY created_at DESC")
        return cur.fetchall()

    def get_pending_question_by_id(self, pq_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT * FROM pending_questions WHERE id=%s", (pq_id,))
        return cur.fetchone()

    def approve_pending_question(self, pq_id):
        cur = self.get_conn().cursor()
        pq = self.get_pending_question_by_id(pq_id)
        if not pq: return False
        # pending_questions: id, sub_admin_id, text, q_type, options, correct, coins, category, difficulty, explanation, image_id, time_limit, created_at, status
        _, sub_id, text, q_type, options, correct, coins, category, difficulty, explanation, image_id, time_limit, _, _ = pq
        self.add_question(text, q_type, options, correct, coins, category, difficulty, explanation, image_id, time_limit, added_by=sub_id, is_approved=1)
        cur.execute("UPDATE pending_questions SET status='approved' WHERE id=%s", (pq_id,))
        return True

    def reject_pending_question(self, pq_id):
        cur = self.get_conn().cursor()
        cur.execute("UPDATE pending_questions SET status='rejected' WHERE id=%s", (pq_id,))



    # ── GROUPS ───────────────────────────────────────────────────────────────
    def create_group_tables(self):
        cur = self.get_conn().cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                chat_id     BIGINT PRIMARY KEY,
                title       TEXT DEFAULT '',
                is_main     INTEGER DEFAULT 0,
                is_active   INTEGER DEFAULT 1,
                added_at    TEXT DEFAULT CURRENT_TIMESTAMP,
                category    TEXT DEFAULT 'Barchasi'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_answers (
                id          SERIAL PRIMARY KEY,
                chat_id     BIGINT,
                user_id     BIGINT,
                question_id INTEGER,
                is_correct  INTEGER DEFAULT 0,
                answered_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_active_questions (
                chat_id     BIGINT PRIMARY KEY,
                question_id INTEGER,
                correct     TEXT,
                coins       REAL DEFAULT 5,
                asked_at    TEXT DEFAULT CURRENT_TIMESTAMP,
                is_open     INTEGER DEFAULT 1
            )
        """)

    def add_group(self, chat_id, title):
        cur = self.get_conn().cursor()
        cur.execute("""
            INSERT INTO groups (chat_id, title) VALUES (%s, %s)
            ON CONFLICT (chat_id) DO UPDATE SET title=%s, is_active=1
        """, (chat_id, title, title))

    def remove_group(self, chat_id):
        cur = self.get_conn().cursor()
        cur.execute("UPDATE groups SET is_active=0 WHERE chat_id=%s", (chat_id,))

    def get_group(self, chat_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT * FROM groups WHERE chat_id=%s", (chat_id,))
        return cur.fetchone()

    def get_all_groups(self):
        cur = self.get_conn().cursor()
        cur.execute("SELECT * FROM groups WHERE is_active=1")
        return cur.fetchall()

    def set_main_group(self, chat_id):
        cur = self.get_conn().cursor()
        cur.execute("UPDATE groups SET is_main=0")
        cur.execute("UPDATE groups SET is_main=1 WHERE chat_id=%s", (chat_id,))

    def get_main_group(self):
        cur = self.get_conn().cursor()
        cur.execute("SELECT chat_id FROM groups WHERE is_main=1 LIMIT 1")
        row = cur.fetchone()
        return row[0] if row else None

    def set_group_category(self, chat_id, category):
        cur = self.get_conn().cursor()
        cur.execute("UPDATE groups SET category=%s WHERE chat_id=%s", (category, chat_id))

    def get_group_category(self, chat_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT category FROM groups WHERE chat_id=%s", (chat_id,))
        row = cur.fetchone()
        return row[0] if row else "Barchasi"

    # Guruh aktiv savoli
    def set_group_question(self, chat_id, question_id, correct, coins):
        cur = self.get_conn().cursor()
        cur.execute("""
            INSERT INTO group_active_questions (chat_id, question_id, correct, coins, is_open)
            VALUES (%s, %s, %s, %s, 1)
            ON CONFLICT (chat_id) DO UPDATE SET question_id=%s, correct=%s, coins=%s, is_open=1, asked_at=CURRENT_TIMESTAMP
        """, (chat_id, question_id, correct, coins, question_id, correct, coins))

    def get_group_question(self, chat_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT * FROM group_active_questions WHERE chat_id=%s AND is_open=1", (chat_id,))
        return cur.fetchone()

    def close_group_question(self, chat_id):
        cur = self.get_conn().cursor()
        cur.execute("UPDATE group_active_questions SET is_open=0 WHERE chat_id=%s", (chat_id,))

    # Guruh javoblari
    def save_group_answer(self, chat_id, user_id, question_id, is_correct):
        cur = self.get_conn().cursor()
        # Bir savolga bir marta javob
        cur.execute("SELECT 1 FROM group_answers WHERE chat_id=%s AND user_id=%s AND question_id=%s",
                    (chat_id, user_id, question_id))
        if cur.fetchone(): return False
        cur.execute("INSERT INTO group_answers (chat_id, user_id, question_id, is_correct) VALUES (%s,%s,%s,%s)",
                    (chat_id, user_id, question_id, int(is_correct)))
        return True

    def already_answered_group(self, chat_id, user_id, question_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT 1 FROM group_answers WHERE chat_id=%s AND user_id=%s AND question_id=%s",
                    (chat_id, user_id, question_id))
        return cur.fetchone() is not None

    def get_group_leaderboard(self, chat_id, limit=10):
        cur = self.get_conn().cursor()
        cur.execute("""
            SELECT ga.user_id, u.first_name, u.username, COUNT(*) as correct_count
            FROM group_answers ga
            LEFT JOIN users u ON u.user_id = ga.user_id
            WHERE ga.chat_id=%s AND ga.is_correct=1
            GROUP BY ga.user_id, u.first_name, u.username
            ORDER BY correct_count DESC LIMIT %s
        """, (chat_id, limit))
        return cur.fetchall()

    def get_group_stats(self, chat_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT COUNT(DISTINCT user_id) FROM group_answers WHERE chat_id=%s", (chat_id,))
        players = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM group_answers WHERE chat_id=%s AND is_correct=1", (chat_id,))
        correct = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM group_answers WHERE chat_id=%s", (chat_id,))
        total = cur.fetchone()[0]
        return {"players": players, "correct": correct, "total": total}

    # ── DUEL TIZIMI ──────────────────────────────────────────────────────────
    def create_duel_tables(self):
        cur = self.get_conn().cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS duels (
                id          SERIAL PRIMARY KEY,
                challenger_id BIGINT,
                opponent_id   BIGINT,
                bet           REAL DEFAULT 10,
                status        TEXT DEFAULT 'pending',
                winner_id     BIGINT DEFAULT NULL,
                challenger_score INTEGER DEFAULT 0,
                opponent_score   INTEGER DEFAULT 0,
                current_question INTEGER DEFAULT 0,
                total_questions  INTEGER DEFAULT 5,
                created_at    TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS duel_questions (
                id          SERIAL PRIMARY KEY,
                duel_id     INTEGER,
                question_id INTEGER,
                order_num   INTEGER
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS duel_answers (
                id          SERIAL PRIMARY KEY,
                duel_id     INTEGER,
                user_id     BIGINT,
                question_id INTEGER,
                is_correct  INTEGER DEFAULT 0,
                answered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(duel_id, user_id, question_id)
            )
        """)
        # ── LIGA TIZIMI ──
        cur.execute("""
            CREATE TABLE IF NOT EXISTS leagues (
                user_id     BIGINT PRIMARY KEY,
                league      TEXT DEFAULT 'bronza',
                points      INTEGER DEFAULT 0,
                week_points INTEGER DEFAULT 0,
                season      INTEGER DEFAULT 1,
                updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def get_or_create_league(self, user_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT * FROM leagues WHERE user_id=%s", (user_id,))
        row = cur.fetchone()
        if not row:
            cur.execute("INSERT INTO leagues (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))
            cur.execute("SELECT * FROM leagues WHERE user_id=%s", (user_id,))
            row = cur.fetchone()
        return row

    def add_league_points(self, user_id, points):
        cur = self.get_conn().cursor()
        self.get_or_create_league(user_id)
        cur.execute("""
            UPDATE leagues SET points=points+%s, week_points=week_points+%s, updated_at=CURRENT_TIMESTAMP
            WHERE user_id=%s
        """, (points, points, user_id))
        self._update_league_rank(user_id)

    def _update_league_rank(self, user_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT points FROM leagues WHERE user_id=%s", (user_id,))
        row = cur.fetchone()
        if not row: return
        pts = row[0]
        if pts >= 1000: league = "olmos"
        elif pts >= 500: league = "platina"
        elif pts >= 200: league = "oltin"
        elif pts >= 80:  league = "kumush"
        else:            league = "bronza"
        cur.execute("UPDATE leagues SET league=%s WHERE user_id=%s", (league, user_id))

    def get_league_leaderboard(self, league=None, limit=10):
        cur = self.get_conn().cursor()
        if league:
            cur.execute("""
                SELECT l.user_id, u.first_name, u.username, l.points, l.league
                FROM leagues l LEFT JOIN users u ON u.user_id=l.user_id
                WHERE l.league=%s ORDER BY l.points DESC LIMIT %s
            """, (league, limit))
        else:
            cur.execute("""
                SELECT l.user_id, u.first_name, u.username, l.points, l.league
                FROM leagues l LEFT JOIN users u ON u.user_id=l.user_id
                ORDER BY l.points DESC LIMIT %s
            """, (limit,))
        return cur.fetchall()

    def get_weekly_leaderboard(self, limit=10):
        cur = self.get_conn().cursor()
        cur.execute("""
            SELECT l.user_id, u.first_name, u.username, l.week_points, l.league
            FROM leagues l LEFT JOIN users u ON u.user_id=l.user_id
            ORDER BY l.week_points DESC LIMIT %s
        """, (limit,))
        return cur.fetchall()

    def reset_weekly_points(self):
        cur = self.get_conn().cursor()
        cur.execute("UPDATE leagues SET week_points=0")

    # Duel metodlari
    def create_duel(self, challenger_id, opponent_id, bet=10):
        cur = self.get_conn().cursor()
        cur.execute("""
            INSERT INTO duels (challenger_id, opponent_id, bet, status)
            VALUES (%s, %s, %s, 'pending') RETURNING id
        """, (challenger_id, opponent_id, bet))
        return cur.fetchone()[0]

    def get_duel(self, duel_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT * FROM duels WHERE id=%s", (duel_id,))
        return cur.fetchone()

    def get_active_duel(self, user_id):
        cur = self.get_conn().cursor()
        cur.execute("""
            SELECT * FROM duels WHERE status='active'
            AND (challenger_id=%s OR opponent_id=%s)
            ORDER BY created_at DESC LIMIT 1
        """, (user_id, user_id))
        return cur.fetchone()

    def get_pending_duel(self, user_id):
        cur = self.get_conn().cursor()
        cur.execute("""
            SELECT * FROM duels WHERE status='pending' AND opponent_id=%s
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        return cur.fetchone()

    def accept_duel(self, duel_id):
        cur = self.get_conn().cursor()
        cur.execute("UPDATE duels SET status='active' WHERE id=%s", (duel_id,))

    def decline_duel(self, duel_id):
        cur = self.get_conn().cursor()
        cur.execute("UPDATE duels SET status='declined' WHERE id=%s", (duel_id,))

    def set_duel_questions(self, duel_id, question_ids):
        cur = self.get_conn().cursor()
        for i, qid in enumerate(question_ids):
            cur.execute("INSERT INTO duel_questions (duel_id, question_id, order_num) VALUES (%s,%s,%s)",
                        (duel_id, qid, i))

    def get_duel_questions(self, duel_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT question_id FROM duel_questions WHERE duel_id=%s ORDER BY order_num", (duel_id,))
        return [r[0] for r in cur.fetchall()]

    def save_duel_answer(self, duel_id, user_id, question_id, is_correct):
        cur = self.get_conn().cursor()
        try:
            cur.execute("""
                INSERT INTO duel_answers (duel_id, user_id, question_id, is_correct)
                VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING
            """, (duel_id, user_id, question_id, int(is_correct)))
            if is_correct:
                # Kim challenger kim opponent
                duel = self.get_duel(duel_id)
                if duel[1] == user_id:
                    cur.execute("UPDATE duels SET challenger_score=challenger_score+1 WHERE id=%s", (duel_id,))
                else:
                    cur.execute("UPDATE duels SET opponent_score=opponent_score+1 WHERE id=%s", (duel_id,))
        except: pass

    def get_duel_answer_count(self, duel_id, user_id):
        cur = self.get_conn().cursor()
        cur.execute("SELECT COUNT(*) FROM duel_answers WHERE duel_id=%s AND user_id=%s", (duel_id, user_id))
        return cur.fetchone()[0]

    def finish_duel(self, duel_id):
        cur = self.get_conn().cursor()
        duel = self.get_duel(duel_id)
        if not duel: return None
        _, ch_id, op_id, bet, status, winner, ch_score, op_score, cur_q, total_q, created = duel
        if ch_score > op_score: winner_id = ch_id
        elif op_score > ch_score: winner_id = op_id
        else: winner_id = None  # draw
        cur.execute("UPDATE duels SET status='finished', winner_id=%s WHERE id=%s", (winner_id, duel_id))
        return winner_id, ch_score, op_score

    def get_duel_stats(self, user_id):
        cur = self.get_conn().cursor()
        cur.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN winner_id=%s THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN winner_id IS NOT NULL AND winner_id!=%s THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN winner_id IS NULL AND status='finished' THEN 1 ELSE 0 END) as draws
            FROM duels WHERE status='finished' AND (challenger_id=%s OR opponent_id=%s)
        """, (user_id, user_id, user_id, user_id))
        return cur.fetchone()

    def get_random_test_questions(self, count=5):
        cur = self.get_conn().cursor()
        cur.execute("""
            SELECT id FROM questions WHERE is_active=1 AND is_approved=1 AND q_type='test'
            ORDER BY RANDOM() LIMIT %s
        """, (count,))
        return [r[0] for r in cur.fetchall()]

db = Database()
