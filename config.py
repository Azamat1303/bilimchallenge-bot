import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

ADMIN_IDS = [6060306988]

QUESTION_TIME = 30

PENALTY_PERCENT = 0.3

TIMEOUT_PENALTY = 0.45

STREAK_BONUSES = {
    3:  1.5,
    5:  2.0,
    10: 3.0,
}

GROQ_API_KEY = "curl AQ.Ab8RN6LZScKDk8xS6t1LUkPA_IPRN9Cegt_CJBC5MrvwLTdUug"
GROQ_MODEL = "llama-3.3-70b-versatile"
