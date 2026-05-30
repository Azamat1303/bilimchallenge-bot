import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

ADMIN_IDS = [6060306988]

# Qiyinlik bo'yicha vaqt (soniyalarda)
QUESTION_TIME = {"oson": 30, "orta": 60, "qiyin": 90}

PENALTY_PERCENT = 0.3

TIMEOUT_PENALTY = 0.45

STREAK_BONUSES = {
    3:  1.5,
    5:  2.0,
    10: 3.0,
}

GROQ_API_KEY = "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"
GROQ_MODEL = "llama-3.3-70b-versatile"
