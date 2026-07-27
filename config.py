# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "8930806821:AAGMdNjL_P-7DPsjso7YwNymYMyD97E25zM")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")

# Admin IDs
ADMIN_IDS = [6060306988]  # O'zingizning Telegram ID ni kiriting

# AI Configuration (Universal Key - Emergent tomonidan)
EMERGENT_LLM_KEY = "sk-emergent-0219d98163196B0Fc1"

# Penalties and Bonuses
TIMEOUT_PENALTY = 5
WRONG_ANSWER_PENALTY = 2
CORRECT_ANSWER_BONUS = 5
STREAK_BONUS = 2
