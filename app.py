"""
BilimChallenge Websayt Backend API
====================================
Bu server saytdagi barcha so'rovlarni qabul qiladi:
- Telegram Login tekshiruvi
- Kategoriyalar, savol oqimi (bot bilan bir xil mantiq)
- Foydalanuvchi profili, reyting, qidiruv
- Coin bilan magazin
- Mini o'yinlar uchun coin berish
- IELTS AI tahlil (Gemini)

Bot bilan BIR XIL PostgreSQL bazasini ishlatadi (database.py orqali),
shuning uchun saytda ko'rilgan coinlar/profil bot bilan bir xil bo'ladi.

O'rnatish: pip install -r requirements.txt
Ishga tushirish: python app.py  (yoki Alwaysdata WSGI orqali wsgi.py)
"""

import os
import hmac
import hashlib
import time
import random
import logging
import asyncio
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import aiohttp

from database import db
from config import (
    BOT_TOKEN, ADMIN_IDS, GEMINI_API_KEY, GEMINI_MODELS, SHOP_ITEMS,
    PENALTY_PERCENT, TIMEOUT_PENALTY, STREAK_BONUSES, FRONTEND_ORIGIN,
)

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": FRONTEND_ORIGIN}})

SESSION_TTL_SECONDS = 30 * 24 * 3600  # 30 kun

DIFF_TIME = {"oson": 30, "orta": 60, "qiyin": 90}


# ─────────────────────────────────────────────────────────────────────────────
# YORDAMCHI: asyncio funksiyani Flask (sinxron) ichida ishga tushirish
# ─────────────────────────────────────────────────────────────────────────────
def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ─────────────────────────────────────────────────────────────────────────────
# TELEGRAM LOGIN TEKSHIRUVI
# ─────────────────────────────────────────────────────────────────────────────
def verify_telegram_auth(data: dict) -> bool:
    """https://core.telegram.org/widgets/login#checking-authorization"""
    if "hash" not in data:
        return False
    check_hash = data["hash"]
    auth_data = {k: v for k, v in data.items() if k != "hash"}

    try:
        auth_date = int(auth_data.get("auth_date", 0))
        if time.time() - auth_date > 86400:
            return False
    except (ValueError, TypeError):
        return False

    data_check_string = "\n".join(f"{k}={auth_data[k]}" for k in sorted(auth_data.keys()))
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed_hash, check_hash)


def create_session_token(user_id: int) -> str:
    expiry = int(time.time()) + SESSION_TTL_SECONDS
    payload = f"{user_id}:{expiry}"
    sig = hmac.new(BOT_TOKEN.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def verify_session_token(token: str):
    try:
        user_id_s, expiry_s, sig = token.split(":")
        payload = f"{user_id_s}:{expiry_s}"
        expected_sig = hmac.new(BOT_TOKEN.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, sig):
            return None
        if int(expiry_s) < time.time():
            return None
        return int(user_id_s)
    except Exception:
        return None


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()
        user_id = verify_session_token(token)
        if not user_id:
            return jsonify({"error": "Avtorizatsiyadan o'tmagansiz"}), 401
        g.user_id = user_id
        return f(*args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# AUTH ENDPOINTLARI
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/auth/telegram", methods=["POST"])
def auth_telegram():
    data = request.get_json(force=True, silent=True) or {}
    if not verify_telegram_auth(data):
        return jsonify({"error": "Telegram tasdiqlash muvaffaqiyatsiz"}), 401

    tg_id = int(data["id"])
    username = data.get("username", "") or ""
    first_name = data.get("first_name", "") or ""
    photo_url = data.get("photo_url", "") or ""

    user = db.get_user(tg_id)
    if not user:
        db.add_user(tg_id, username, first_name, None)

    db.set_web_profile_photo(tg_id, photo_url)

    token = create_session_token(tg_id)
    return jsonify({"token": token, "user_id": tg_id})


@app.route("/api/auth/me", methods=["GET"])
@require_auth
def auth_me():
    profile = db.get_full_profile(g.user_id)
    if not profile:
        return jsonify({"error": "Foydalanuvchi topilmadi"}), 404
    return jsonify(profile)


# ─────────────────────────────────────────────────────────────────────────────
# KATEGORIYALAR VA SAVOL OQIMI (bot bilan bir xil mantiq, bir xil baza)
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/categories", methods=["GET"])
def get_categories():
    cats = db.get_categories_with_counts_for_web()
    return jsonify(cats)


def _shuffle_options(opts_str, correct_letter):
    opts = opts_str.split("|")
    ci = ord(correct_letter.upper()) - 65
    if ci >= len(opts):
        return opts, correct_letter
    correct_text = opts[ci]
    shuffled = opts[:]
    random.shuffle(shuffled)
    new_ci = shuffled.index(correct_text)
    return shuffled, chr(65 + new_ci)


# Har bir foydalanuvchi uchun "hozir ko'rsatilayotgan savol" holatini
# xotirada saqlaymiz (aralashtirilgan variantlar va to'g'ri harf shu yerda,
# chunki bazada asl tartib saqlanadi, aralashtirish faqat ko'rsatishda bo'ladi).
_active_web_questions = {}  # user_id -> {question_id, correct_letter/correct_text, coins, q_type, started_at, difficulty}


@app.route("/api/question/next", methods=["GET"])
@require_auth
def question_next():
    category = request.args.get("category")
    mode = request.args.get("mode", "all")
    q_type = None
    if mode == "test":
        q_type = "test"
    elif mode == "open":
        q_type = "open"

    q = db.get_web_random_question(g.user_id, category if category and category != "Barchasi" else None, q_type)
    if not q:
        return jsonify({"finished": True})

    q_id, q_text, q_t, options, correct, coins, cat, difficulty, explanation, image_id, time_limit = q

    payload = {
        "question_id": q_id,
        "text": q_text,
        "q_type": q_t,
        "category": cat,
        "difficulty": difficulty,
        "coins": coins,
        "time_limit": DIFF_TIME.get(difficulty, 30),
    }

    if q_t == "test":
        shuffled_opts, new_correct_letter = _shuffle_options(options, correct)
        payload["options"] = shuffled_opts
        _active_web_questions[g.user_id] = {
            "question_id": q_id, "q_type": "test",
            "correct": new_correct_letter, "coins": coins,
            "explanation": explanation, "started_at": time.time(),
        }
    else:
        _active_web_questions[g.user_id] = {
            "question_id": q_id, "q_type": "open",
            "correct": correct, "coins": coins,
            "explanation": explanation, "started_at": time.time(),
        }

    return jsonify(payload)


def _check_open_answer(user_ans, correct_ans):
    ua = (user_ans or "").strip().lower()
    return ua in [a.strip().lower() for a in correct_ans.split("\n") if a.strip()]


def _streak_bonus(streak):
    b = 1.0
    for t in sorted(STREAK_BONUSES.keys()):
        if streak >= t:
            b = STREAK_BONUSES[t]
    return b


@app.route("/api/question/answer", methods=["POST"])
@require_auth
def question_answer():
    data = request.get_json(force=True, silent=True) or {}
    question_id = data.get("question_id")
    answer = data.get("answer")
    timed_out = bool(data.get("timed_out"))

    active = _active_web_questions.get(g.user_id)
    if not active or active["question_id"] != question_id:
        return jsonify({"error": "Bu savol sizning aktiv savolingiz emas yoki muddati o'tgan"}), 400

    if db.already_answered(g.user_id, question_id):
        return jsonify({"error": "Bu savolga allaqachon javob berilgan"}), 400

    coins = active["coins"]
    q_type = active["q_type"]
    explanation = active.get("explanation", "")

    result = {"explanation": explanation}

    if timed_out:
        db.save_web_answer(g.user_id, question_id, False)
        db.update_streak(g.user_id, False)
        penalty = round(coins * TIMEOUT_PENALTY, 1)
        db.add_coins(g.user_id, -penalty)
        result.update({"is_correct": False, "penalty": penalty})
        if q_type == "test":
            result["correct_letter"] = active["correct"]
        else:
            result["correct_answer"] = active["correct"].split("\n")[0].strip()

    else:
        if q_type == "test":
            is_correct = str(answer).upper() == active["correct"].upper()
        else:
            is_correct = _check_open_answer(answer, active["correct"])

        db.save_web_answer(g.user_id, question_id, is_correct)

        if is_correct:
            new_streak = db.update_streak(g.user_id, True)
            bonus = _streak_bonus(new_streak)
            earned = round(coins * bonus, 1)
            db.add_coins(g.user_id, earned)
            db.add_league_points(g.user_id, 2)
            result.update({"is_correct": True, "earned": earned, "bonus_multiplier": bonus, "new_streak": new_streak})
        else:
            db.update_streak(g.user_id, False)
            penalty = round(coins * PENALTY_PERCENT, 1)
            db.add_coins(g.user_id, -penalty)
            result.update({"is_correct": False, "penalty": penalty})
            if q_type == "test":
                result["correct_letter"] = active["correct"]
            else:
                result["correct_answer"] = active["correct"].split("\n")[0].strip()

    user = db.get_user(g.user_id)
    result["total_coins"] = round(user[3], 1) if user else None

    _active_web_questions.pop(g.user_id, None)
    return jsonify(result)


# ─────────────────────────────────────────────────────────────────────────────
# PROFIL / REYTING / QIDIRUV
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/profile/<int:user_id>", methods=["GET"])
def get_profile(user_id):
    profile = db.get_full_profile(user_id)
    if not profile:
        return jsonify({"error": "Foydalanuvchi topilmadi"}), 404
    return jsonify(profile)


@app.route("/api/leaderboard", methods=["GET"])
def leaderboard():
    limit = min(int(request.args.get("limit", 50)), 100)
    top = db.get_leaderboard(limit)
    result = []
    for uid, fname, uname, coins in top:
        result.append({
            "user_id": uid, "first_name": fname, "username": uname,
            "coins": round(coins, 1),
            "frame": db.get_equipped_frame(uid),
            "badge": db.get_equipped_badge(uid),
        })
    return jsonify(result)


@app.route("/api/search", methods=["GET"])
def search_users():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    results = db.search_users(q, limit=20)
    return jsonify([
        {"user_id": r[0], "first_name": r[1], "username": r[2], "coins": round(r[3], 1)}
        for r in results
    ])


# ─────────────────────────────────────────────────────────────────────────────
# MAGAZIN
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/shop/items", methods=["GET"])
def shop_items():
    return jsonify(SHOP_ITEMS)


@app.route("/api/shop/inventory", methods=["GET"])
@require_auth
def shop_inventory():
    owned = db.get_owned_items(g.user_id)
    equipped = {
        "avatar": db.get_equipped_avatar(g.user_id),
        "frame": db.get_equipped_frame(g.user_id),
        "badge": db.get_equipped_badge(g.user_id),
    }
    return jsonify({"owned": owned, "equipped": equipped})


@app.route("/api/shop/buy", methods=["POST"])
@require_auth
def shop_buy():
    data = request.get_json(force=True, silent=True) or {}
    item_id = data.get("item_id")
    item = next((i for i in SHOP_ITEMS if i["id"] == item_id), None)
    if not item:
        return jsonify({"error": "Mahsulot topilmadi"}), 404

    if db.owns_item(g.user_id, item_id):
        return jsonify({"error": "Bu mahsulot allaqachon sizda bor"}), 400

    user = db.get_user(g.user_id)
    if not user or user[3] < item["price"]:
        return jsonify({"error": "Coin yetarli emas"}), 400

    db.add_coins(g.user_id, -item["price"])
    db.add_owned_item(g.user_id, item_id, item["type"])
    return jsonify({"success": True, "remaining_coins": round(user[3] - item["price"], 1)})


@app.route("/api/shop/equip", methods=["POST"])
@require_auth
def shop_equip():
    data = request.get_json(force=True, silent=True) or {}
    item_id = data.get("item_id")
    item = next((i for i in SHOP_ITEMS if i["id"] == item_id), None)
    if not item:
        return jsonify({"error": "Mahsulot topilmadi"}), 404
    if not db.owns_item(g.user_id, item_id) and item["price"] > 0:
        return jsonify({"error": "Bu mahsulot sizda yo'q"}), 403
    db.equip_item(g.user_id, item_id, item["type"])
    return jsonify({"success": True})


# ─────────────────────────────────────────────────────────────────────────────
# MINI O'YINLAR - COIN BERISH
# ─────────────────────────────────────────────────────────────────────────────
GAME_REWARDS = {
    "memory":    {"base": 3, "max_bonus": 5},
    "reflex":    {"base": 2, "max_bonus": 4},
    "logic":     {"base": 4, "max_bonus": 6},
    "wordchain": {"base": 3, "max_bonus": 5},
}
DAILY_GAME_COIN_CAP = 40


def _game_signature(game_id: str, user_id: int, started_at: int) -> str:
    payload = f"{game_id}:{user_id}:{started_at}"
    return hmac.new(BOT_TOKEN.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]


@app.route("/api/games/start", methods=["POST"])
@require_auth
def games_start():
    data = request.get_json(force=True, silent=True) or {}
    game_id = data.get("game")
    if game_id not in GAME_REWARDS:
        return jsonify({"error": "Noma'lum o'yin"}), 400
    started_at = int(time.time())
    sig = _game_signature(game_id, g.user_id, started_at)
    return jsonify({"started_at": started_at, "signature": sig})


@app.route("/api/games/finish", methods=["POST"])
@require_auth
def games_finish():
    data = request.get_json(force=True, silent=True) or {}
    game_id = data.get("game")
    started_at = data.get("started_at")
    signature = data.get("signature")
    score_ratio = float(data.get("score_ratio", 0))

    if game_id not in GAME_REWARDS or started_at is None or not signature:
        return jsonify({"error": "Noto'g'ri so'rov"}), 400

    expected_sig = _game_signature(game_id, g.user_id, started_at)
    if not hmac.compare_digest(expected_sig, signature):
        return jsonify({"error": "Sessiya tasdiqlanmadi"}), 403

    elapsed = time.time() - started_at
    if elapsed < 3:
        return jsonify({"error": "O'yin juda tez tugadi"}), 400

    score_ratio = max(0.0, min(1.0, score_ratio))
    reward_cfg = GAME_REWARDS[game_id]
    earned = round(reward_cfg["base"] + reward_cfg["max_bonus"] * score_ratio, 1)

    today_total = db.get_today_game_coins(g.user_id)
    if today_total >= DAILY_GAME_COIN_CAP:
        return jsonify({"earned": 0, "message": "Kunlik mini o'yin coin limiti tugadi", "daily_cap": DAILY_GAME_COIN_CAP})

    if today_total + earned > DAILY_GAME_COIN_CAP:
        earned = round(DAILY_GAME_COIN_CAP - today_total, 1)

    db.add_coins(g.user_id, earned)
    db.log_game_coins(g.user_id, game_id, earned)
    user = db.get_user(g.user_id)
    return jsonify({
        "earned": earned,
        "total_coins": round(user[3], 1) if user else None,
        "daily_remaining": round(DAILY_GAME_COIN_CAP - today_total - earned, 1),
    })


# ─────────────────────────────────────────────────────────────────────────────
# IELTS AI TAHLIL (Gemini)
# ─────────────────────────────────────────────────────────────────────────────
async def _gemini_call(prompt: str, max_tokens: int = 700):
    for model in GEMINI_MODELS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.6},
            }
            async with aiohttp.ClientSession() as s:
                async with s.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as r:
                    if r.status != 200:
                        continue
                    d = await r.json()
                    candidates = d.get("candidates", [])
                    if candidates:
                        return candidates[0]["content"]["parts"][0]["text"]
        except Exception as e:
            logging.warning(f"Gemini {model}: {e}")
    return None


@app.route("/api/ielts/weakness-check", methods=["POST"])
@require_auth
def ielts_weakness_check():
    data = request.get_json(force=True, silent=True) or {}
    section = data.get("section", "writing")
    user_answer = data.get("answer", "")
    band_score = data.get("band_score")

    if not user_answer or len(user_answer.strip()) < 15:
        return jsonify({"tip": None})

    prompt = (
        f"Siz IELTS {section} bo'yicha shaxsiy murabbiysiz. "
        f"Foydalanuvchi quyidagi javobni yozdi (band score: {band_score}):\n\n"
        f"\"{user_answer[:800]}\"\n\n"
        f"O'ZBEK TILIDA, 2-3 gapda, ENG KATTA bitta xatoni ko'rsating va "
        f"aniq qanday tuzatish kerakligini ayting. Umumiy gap yozmang — "
        f"aynan shu javobdagi muammoni toping. Format:\n"
        f"XATO: [nima xato]\nTUZATISH: [qanday qilish kerak edi]"
    )
    analysis = run_async(_gemini_call(prompt, max_tokens=300))
    if analysis and band_score is not None:
        db.log_ielts_weakness(g.user_id, section, float(band_score), analysis.strip())
    if not analysis:
        return jsonify({"tip": None})
    return jsonify({"tip": analysis.strip()})


@app.route("/api/ielts/weekly-pattern", methods=["GET"])
@require_auth
def ielts_weekly_pattern():
    recent = db.get_recent_ielts_weaknesses(g.user_id, limit=10)
    if len(recent) < 3:
        return jsonify({"pattern": None, "message": "Naqsh aniqlash uchun kamida 3 ta javob kerak"})

    summary_lines = "\n".join(f"- {r['section']}: band {r['band']} — {r['tip'][:150]}" for r in recent)
    prompt = (
        f"Quyidagi foydalanuvchining oxirgi IELTS javoblari tahlili:\n\n{summary_lines}\n\n"
        f"O'ZBEK TILIDA, 3-4 gapda: bu odam DOIMIY ravishda qaysi ko'nikmada qiynalayotganini "
        f"aniqlang (masalan grammatika, so'z boyligi, tuzilma) va nima ustida ishlashi kerakligini ayting."
    )
    pattern = run_async(_gemini_call(prompt, max_tokens=350))
    return jsonify({"pattern": pattern.strip() if pattern else None})


# ─────────────────────────────────────────────────────────────────────────────
# SOG'LOM TEKSHIRUV
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    try:
        db.get_conn().cursor().execute("SELECT 1")
        return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
