# ═══════════════════════════════════════════════════
#         BilimChallenge Bot — Konfiguratsiya
# ═══════════════════════════════════════════════════

# 1. @BotFather dan olgan tokeningiz
BOT_TOKEN = "8930806821:AAGQTTeZow7y1bX_FfLhrRPj89XwcT8gDFM"

# 2. Admin Telegram ID raqami
ADMIN_IDS = [6060306988]

# 3. Savol vaqti (soniyalarda)
#    Masalan: 30 = 30 soniya, 60 = 1 daqiqa
QUESTION_TIME = 30

# 4. Jarima foizi (noto'g'ri javob yoki vaqt tugaganda)
#    0.3 = 30%, 0.5 = 50%, 0.1 = 10%
PENALTY_PERCENT = 0.3

# 5. Streak bonuslari
#    Format: {ketma-ket_son: bonus_koeffitsient}
STREAK_BONUSES = {
    3:  1.5,   # 3 ta ketma-ket = x1.5
    5:  2.0,   # 5 ta ketma-ket = x2.0
    10: 3.0,   # 10 ta ketma-ket = x3.0
}
