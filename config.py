"""
Backend konfiguratsiyasi.
BOT_TOKEN bot.py dagi bilan BIR XIL bo'lishi shart —
Telegram Login Widget shu tokenga bog'liq imzoni tekshiradi.
"""

import os

# Bot bilan bir xil token va admin ro'yxati
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8930806821:AAGQTTeZow7y1bX_FfLhrRPj89XwcT8gDFM")
ADMIN_IDS = [6060306988]

PENALTY_PERCENT = 0.3
TIMEOUT_PENALTY = 0.45
STREAK_BONUSES = {3: 1.5, 5: 2.0, 10: 3.0}

# Gemini API (bot bilan bir xil kalit ishlatilishi mumkin)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyC-PUT-YOUR-GEMINI-KEY-HERE")
GEMINI_MODELS = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

# ─────────────────────────────────────────────────────────────────────────────
# MAGAZIN MAHSULOTLARI
# ─────────────────────────────────────────────────────────────────────────────
SHOP_ITEMS = [
    # ── Ramkalar (frame) ──
    {"id": "frame_bronze",   "type": "frame",  "name": "Bronza ramka",      "emoji": "🟤", "price": 0,   "css": "frame-bronze"},
    {"id": "frame_silver",   "type": "frame",  "name": "Kumush ramka",      "emoji": "⚪", "price": 150, "css": "frame-silver"},
    {"id": "frame_gold",     "type": "frame",  "name": "Oltin ramka",       "emoji": "🟡", "price": 400, "css": "frame-gold"},
    {"id": "frame_neon",     "type": "frame",  "name": "Neon ramka",        "emoji": "💠", "price": 800, "css": "frame-neon"},
    {"id": "frame_fire",     "type": "frame",  "name": "Olov ramka",        "emoji": "🔥", "price": 1200,"css": "frame-fire"},

    # ── Nishonlar (badge) ──
    {"id": "badge_brain",    "type": "badge",  "name": "Miya nishoni",      "emoji": "🧠", "price": 100, "css": "badge-brain"},
    {"id": "badge_rocket",   "type": "badge",  "name": "Raketa nishoni",    "emoji": "🚀", "price": 250, "css": "badge-rocket"},
    {"id": "badge_crown",    "type": "badge",  "name": "Toj nishoni",       "emoji": "👑", "price": 600, "css": "badge-crown"},
    {"id": "badge_diamond",  "type": "badge",  "name": "Olmos nishoni",     "emoji": "💎", "price": 1000,"css": "badge-diamond"},

    # ── Fon effektlari (avatar) ──
    {"id": "avatar_stars",   "type": "avatar", "name": "Yulduzli fon",      "emoji": "✨", "price": 200, "css": "avatar-stars"},
    {"id": "avatar_wave",    "type": "avatar", "name": "To'lqin fon",       "emoji": "🌊", "price": 350, "css": "avatar-wave"},
    {"id": "avatar_matrix",  "type": "avatar", "name": "Matritsa fon",      "emoji": "🟩", "price": 700, "css": "avatar-matrix"},
]

# Frontend CORS uchun aniq domen (ixtiyoriy, bo'sh qoldirsa "*" ishlatiladi)
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")
