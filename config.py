import os
 
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_TOKEN = "8930806821:AAGQTTeZow7y1bX_FfLhrRPj89XwcT8gDFM"
ADMIN_IDS = [6060306988]

QUESTION_TIME = 30
PENALTY_PERCENT = 0.3
TIMEOUT_PENALTY = 0.45

STREAK_BONUSES = {
    3:  1.5,
    5:  2.0,
    10: 3.0,
}

GROQ_API_KEY = "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"
GROQ_MODEL = "llama3-70b-8192"
GEMINI_API_KEY = "AQ.Ab8RN6LZScKDk8xS6t1LUkPA_IPRN9Cegt_CJBC5MrvwLTdUug"
DATABASE_URL = "postgresql://neondb_owner:npg_ISTdnGO5YpE3@ep-crimson-scene-aqmmilfp-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
