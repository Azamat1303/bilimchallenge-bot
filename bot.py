import logging
import asyncio
import random
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from database import db
from config import BOT_TOKEN, ADMIN_IDS, QUESTION_TIME, PENALTY_PERCENT, TIMEOUT_PENALTY, STREAK_BONUSES, GROQ_API_KEY, GROQ_MODEL, GEMINI_API_KEY

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DIFFICULTY_ICONS = {"oson": "🟢", "orta": "🟡", "qiyin": "🔴"}
DIFFICULTY_NAMES = {"oson": "Oson", "orta": "O'rta", "qiyin": "Qiyin"}
IELTS_TYPES = ["writing", "essay", "reading", "speaking", "listening"]

# ── Stikerlar ─────────────────────────────────────────────────────────────────
STICKER_QUESTION = "CAACAgQAAxkBAAFK2GFqGBZkvOQYIqxuYRxOg8yZ_kGpCQACLhMAAqtUsFGayERH0PRbYTsE"
STICKER_CORRECT_LOW  = "CAACAgIAAxkBAAFK2HxqGBcuYTvi4L__VuLGnOmw_0h3MQACT6cAAiS3qEprLmY89x6ufjsE"
STICKER_CORRECT_MID  = "CAACAgQAAxkBAAFK2FxqGBZODMIw26R9HpabXj_GXXHY_QAC9wsAAsVA0FKiYzU0cZkIATsE"
STICKER_CORRECT_HIGH = "CAACAgIAAxkBAAFK2HFqGBa54WJlIjngkLvRxQyv_iejvAACUqEAAs2uqEoU5ts6XT2m-DsE"
STICKERS_CORRECT_RANDOM = [
    "CAACAgIAAxkBAAFK2BdqGBSDpT9UJGnf8A933SkujhR1ugAC7i4AAu2JwEjbRw5y8ATySTsE",
    "CAACAgIAAxkBAAFK2B1qGBSg7YLcDzG45IMbWD9yLQd2twACxCwAAmyCwUhW4u2V7FLn2jsE",
    "CAACAgIAAxkBAAFK2ChqGBT8ht7vPfWPVNZSJ99eSrO4aAACpy4AAlsmwUgiQZe-63v_8DsE",
]
STICKER_WRONG_LOW  = "CAACAgIAAxkBAAFK2I5qGBe3fhF_QafwvVtn9eZZJ2wyYgACwnEAAj3NaUpk2l3tCbDGJTsE"
STICKER_WRONG_MID  = "CAACAgIAAxkBAAFK2GZqGBaGcsKcNXFNKzEjnwAB_N6SLx4AAiZjAAIexglIbW6k0yQK8f47BA"
STICKER_WRONG_HIGH = "CAACAgIAAxkBAAFK2ABqGBdBbZ364p3pJn7rIUWgmYP_ZwACe5gAArNyiUj8ULr6FLOqsTsE"
STICKERS_WRONG_RANDOM = [
    "CAACAgIAAxkBAAFK2B9qGBSy53xM_fWFSR3_QB-b-96PzwACuUIAAkSZyEj30qYDy3h_-TsE",
    "CAACAgIAAxkBAAFK2CFqGBTQxCg8PTNAy8ELJPO1ekiKQAACcSkAAthiwUi7vlkGdgu7SjsE",
    "CAACAgIAAxkBAAFK2I5qGBe3fhF_QafwvVtn9eZZJ2wyYgACwnEAAj3NaUpk2l3tCbDGJTsE",
]
STICKERS_TIMEOUT = [
    "CAACAgIAAxkBAAFK2CpqGBT9Y8JM8DQ_k5oZ_koPS4fNlgACWiYAAlDgwEhOxSLS4ALrSDsE",
    "CAACAgIAAxkBAAFK2CVqGBTpcrLFTrOLIF6ZRjaUHU_NxwACei0AAhRdCUkIUGBOZbVgrjsE",
]
STICKER_LEADERBOARD = "CAACAgQAAxkBAAFK2F5qGBZib8V7GFYDhDMw8H10BaJIfgAChBYAAkfnsFEm5zMVxs4-nDsE"
STICKER_TOP1  = "CAACAgQAAxkBAAFK2pVqGC8QLY1z08fADOc-QGogLJWn2AACFxsAAvdb0FEvAAGtAAFifD0MOwQ"
STICKER_TOP2  = "CAACAgQAAxkBAAFK2E9qGBXpsYQFe_Q2qKm4WQcn5lZeRAACGhYAAkQp2VGaVMouneMzrjsE"
STICKER_TOP3  = "CAACAgQAAxkBAAFK2FJqGBXrg1BmRPSdqE663UwwKVFsWAACnxQAAk8s6FDKghp6_6nUJDsE"
STICKER_TOP5  = "CAACAgQAAxkBAAFK2FZqGBX4e7mmRfTgeyt3WLZCD4xSdQADFwACZFbRUYAvpAABVerDrjsE"
STICKER_TOP10 = "CAACAgQAAxkBAAFK2FhqGBYKX7aALmALEnidgp-wFO-3nQAC2RYAAj6CKVFONJy-EgNA5TsE"

def get_correct_sticker(coins):
    if coins <= 1: return STICKER_CORRECT_LOW
    elif coins <= 5: return random.choice(STICKERS_CORRECT_RANDOM)
    else: return STICKER_CORRECT_HIGH

def get_wrong_sticker(coins):
    if coins <= 1: return STICKER_WRONG_LOW
    elif coins <= 5: return STICKER_WRONG_MID
    else: return STICKER_WRONG_HIGH

def get_rank_sticker(rank):
    if rank == 1: return STICKER_TOP1
    elif rank == 2: return STICKER_TOP2
    elif rank == 3: return STICKER_TOP3
    elif rank <= 5: return STICKER_TOP5
    elif rank <= 10: return STICKER_TOP10
    return None

# ── STATES ────────────────────────────────────────────────────────────────────
class AdminStates(StatesGroup):
    waiting_question_type = State()
    waiting_question_text = State()
    waiting_options = State()
    waiting_correct_answer = State()
    waiting_coin_reward = State()
    waiting_difficulty = State()
    waiting_category = State()
    waiting_explanation = State()
    waiting_image = State()
    waiting_time_limit = State()
    waiting_new_category = State()
    editing_field = State()
    editing_value = State()
    broadcast_text = State()
    broadcast_image = State()

class UserStates(StatesGroup):
    answering_open = State()
    sending_feedback = State()
    answering_premium = State()
    answering_ielts = State()
    ai_chat = State()
    ai_chat_confirm_debt = State()

ILLEGAL_WORDS = ["bomb", "portlat", "o'ldur", "qotil", "terror", "drug", "narkotik", "hack", "взлом", "бомба"]
AI_COST_PER_15_CHARS = 1  # har 15 belgi uchun 1 coin

# ── HELPERS ───────────────────────────────────────────────────────────────────
def is_admin(uid): return uid in ADMIN_IDS

def main_menu(uid):
    buttons = [
        [KeyboardButton(text="🎯 Savol olish"), KeyboardButton(text="🏆 Reyting")],
        [KeyboardButton(text="👤 Profilim"), KeyboardButton(text="ℹ️ Yordam")],
        [KeyboardButton(text="📝 Taklif/Shikoyat"), KeyboardButton(text="🎓 IELTS")],
        [KeyboardButton(text="🤖 AI Chat")],
    ]
    if is_admin(uid): buttons.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def admin_menu():
    buttons = [
        [KeyboardButton(text="➕ Savol qo'shish"), KeyboardButton(text="📋 Savollar ro'yxati")],
        [KeyboardButton(text="✏️ Savol tahrirlash"), KeyboardButton(text="🗑 Savol o'chirish")],
        [KeyboardButton(text="📂 Kategoriyalar"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="👥 Foydalanuvchilar"), KeyboardButton(text="💬 Takliflar")],
        [KeyboardButton(text="📢 Xabar yuborish"), KeyboardButton(text="🔙 Asosiy menyu")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def streak_bonus(streak):
    bonus = 1.0
    for t in sorted(STREAK_BONUSES.keys()):
        if streak >= t: bonus = STREAK_BONUSES[t]
    return bonus

def streak_message(streak):
    if streak >= 10: return f"🔥🔥🔥 SUPER STREAK x{streak}!"
    if streak >= 5: return f"🔥🔥 STREAK x{streak}!"
    if streak >= 3: return f"🔥 STREAK x{streak}!"
    return ""

def shuffle_options(options_str, correct_letter):
    opts = options_str.split("|")
    correct_idx = ord(correct_letter.upper()) - 65
    if correct_idx >= len(opts): return options_str, correct_letter
    correct_text = opts[correct_idx]
    indices = list(range(len(opts)))
    random.shuffle(indices)
    shuffled = [opts[i] for i in indices]
    new_correct_idx = shuffled.index(correct_text)
    return "|".join(shuffled), chr(65 + new_correct_idx)

def check_open_answer(user_ans, correct_ans):
    """Ko'p to'g'ri javob, strip/lower bilan tekshirish"""
    user_clean = user_ans.strip().lower()
    answers_list = [a.strip().lower() for a in correct_ans.split("\n") if a.strip()]
    return user_clean in answers_list

async def groq_analyze(prompt: str) -> str:
    """Gemini API orqali matn tahlili"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]}
            ) as resp:
                data = await resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        # Xato bo'lsa Groq ga fallback
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                    json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 1000}
                ) as resp:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e2:
            return f"⚠️ AI tahlil xatolik: {str(e2)}"

# ── /start ────────────────────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    db.add_user(user.id, user.username or "", user.first_name or "")
    await message.answer(
        f"🧠 <b>BilimChallenge</b> ga xush kelibsiz, {user.first_name}!\n\n"
        f"🎯 Savollarga javob bering\n💰 Coinlar to'plang\n"
        f"🔥 Streak yig'ing — bonus coinlar\n🏆 Global reytingda o'rningizni egallang!\n"
        f"🎓 IELTS bo'limlari — AI bilan mashq qiling!\n\n"
        f"Boshlash uchun <b>Savol olish</b> tugmasini bosing!",
        parse_mode="HTML", reply_markup=main_menu(user.id)
    )

@dp.message(Command("cancel"))
async def cancel_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=main_menu(message.from_user.id))

# ── SAVOL OLISH ───────────────────────────────────────────────────────────────
@dp.message(F.text == "🎯 Savol olish")
async def get_question_start(message: types.Message, state: FSMContext):
    await state.clear()
    categories = db.get_categories()
    if not categories:
        await message.answer("😔 Hozircha savollar yo'q!")
        return

    # Kategoriya tanlash
    buttons = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat_{cat}"))
        if len(row) == 2:
            buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🌐 Aralash (barcha)", callback_data="cat_Barchasi")])
    await message.answer("📂 <b>Kategoriya tanlang:</b>", parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("cat_"))
async def category_chosen(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data[4:]
    await state.update_data(category=category)
    try: await callback.message.delete()
    except: pass

    # Test yoki Ochiq tanlash
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Test savollar", callback_data=f"qmode_test_{category}")],
        [InlineKeyboardButton(text="✍️ Ochiq savollar", callback_data=f"qmode_open_{category}")],
        [InlineKeyboardButton(text="🌐 Aralash", callback_data=f"qmode_all_{category}")],
    ])
    await callback.message.answer(f"📂 <b>{category}</b>\n\nSavol turini tanlang:", parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("qmode_"))
async def qmode_chosen(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_", 2)
    mode = parts[1]
    category = parts[2]
    await state.update_data(category=category, qmode=mode)
    try: await callback.message.delete()
    except: pass
    await send_question(callback.message, callback.from_user.id, state, category, mode)
    await callback.answer()

# Faol timer tasklarni kuzatish
active_timers = {}

DIFFICULTY_TIME = {"oson": 30, "orta": 60, "qiyin": 90}

async def send_question(message, user_id, state, category, mode="all"):
    if mode == "test":
        question = db.get_random_question(user_id, category, q_type="test")
    elif mode == "open":
        question = db.get_random_question(user_id, category, q_type="open")
    else:
        # Aralash — test, open va premium hammasidan (q_type=None = IELTS dan tashqari hammasi)
        question = db.get_random_question(user_id, category, q_type=None)

    if not question:
        cats = db.get_categories()
        buttons = []
        row = []
        for cat in cats:
            row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat_{cat}"))
            if len(row) == 2: buttons.append(row); row = []
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton(text="🌐 Aralash", callback_data="cat_Barchasi")])
        await message.answer("🎉 <b>Bu bo'limdagi savollar tugadi!</b>\n\nBoshqa kategoriyani tanlang:", parse_mode="HTML",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return

    q_id, q_text, q_type, options, correct, coins, cat, difficulty, explanation, image_id, time_limit = question

    # Premium savol kelsa — premium handlerga yo'naltir
    if q_type == "premium":
        await send_premium_question(message, user_id, state, category)
        return

    diff_icon = DIFFICULTY_ICONS.get(difficulty, "🟡")
    diff_name = DIFFICULTY_NAMES.get(difficulty, "O'rta")

    # Qiyinlikka qarab vaqt
    q_time = DIFFICULTY_TIME.get(difficulty, 30)

    header = (
        f"🆔 <b>#{q_id}</b>  📂 <b>{cat}</b>  {diff_icon} <b>{diff_name}</b>\n"
        f"💰 To'g'ri: <b>+{coins} coin</b>  ❌ Noto'g'ri: <b>-{round(coins*PENALTY_PERCENT,1)} coin</b>\n"
        f"⏱ Vaqt: <b>{q_time} soniya</b>\n\n"
        f"❓ <b>{q_text}</b>"
    )

    try: await bot.send_sticker(message.chat.id, sticker=STICKER_QUESTION)
    except: pass

    if q_type == "test":
        shuffled_opts, new_correct = shuffle_options(options, correct)
        opts_list = shuffled_opts.split("|")
        # Har bir variant alohida qatorda to'liq ko'rinsin
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{chr(65+i)}. {opt[:64]}", callback_data=f"ans_{q_id}_{chr(65+i)}_{new_correct}")]
            for i, opt in enumerate(opts_list)
        ])
        if image_id:
            try: sent = await bot.send_photo(message.chat.id, photo=image_id, caption=header, parse_mode="HTML", reply_markup=keyboard)
            except: sent = await message.answer(header, parse_mode="HTML", reply_markup=keyboard)
        else:
            sent = await message.answer(header, parse_mode="HTML", reply_markup=keyboard)
        await state.update_data(question_id=q_id, msg_id=sent.message_id, chat_id=message.chat.id)
        # Eski timerni bekor qil
        if user_id in active_timers:
            active_timers[user_id].cancel()
        task = asyncio.create_task(question_timeout(user_id, q_id, sent.message_id, message.chat.id, coins, state, q_time))
        active_timers[user_id] = task
    else:
        await state.set_state(UserStates.answering_open)
        await state.update_data(question_id=q_id, correct=correct, coins=coins, explanation=explanation)
        text = header + "\n\n✍️ <b>Javobingizni yozing:</b>"
        if image_id:
            try: sent = await bot.send_photo(message.chat.id, photo=image_id, caption=text, parse_mode="HTML")
            except: sent = await message.answer(text, parse_mode="HTML")
        else:
            sent = await message.answer(text, parse_mode="HTML")

        skip_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data=f"skip_open_{q_id}")]
        ])
        await message.answer("👆 Javob yozing:", reply_markup=skip_kb)
        # Eski timerni bekor qil
        if user_id in active_timers:
            active_timers[user_id].cancel()
        task = asyncio.create_task(question_timeout(user_id, q_id, sent.message_id, message.chat.id, coins, state, q_time))
        active_timers[user_id] = task

async def question_timeout(user_id, q_id, msg_id, chat_id, coins, state, q_time=30):
    total = q_time
    wait = total - 10
    if wait > 0: await asyncio.sleep(wait)

    timer_msg = None
    for remaining in range(10, 0, -1):
        if db.already_answered(user_id, q_id):
            if timer_msg:
                try: await timer_msg.delete()
                except: pass
            return
        filled = int((remaining / total) * 10)
        block = "🟥" if remaining <= 3 else ("🟧" if remaining <= 6 else "🟨")
        bar = block * filled + "⬜" * (10 - filled)
        text = f"⏱ <b>{remaining}s</b>  {bar}"
        try:
            if timer_msg is None: timer_msg = await bot.send_message(chat_id, text, parse_mode="HTML")
            else: await timer_msg.edit_text(text, parse_mode="HTML")
        except: pass
        await asyncio.sleep(1)

    if db.already_answered(user_id, q_id):
        if timer_msg:
            try: await timer_msg.delete()
            except: pass
        return

    db.save_answer(user_id, q_id, False)
    penalty = round(coins * TIMEOUT_PENALTY, 1)
    db.add_coins(user_id, -penalty)
    db.update_streak(user_id, False)

    if timer_msg:
        try: await timer_msg.delete()
        except: pass
    try: await bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=None)
    except: pass
    try: await bot.send_sticker(chat_id, sticker=random.choice(STICKERS_TIMEOUT))
    except: pass

    data = await state.get_data()
    category = data.get("category", "Barchasi")
    mode = data.get("qmode", "all")
    try:
        await bot.send_message(chat_id, f"⏰ <b>Vaqt tugadi!</b>\n❌ -{penalty} coin jarima (45%)", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data=f"next_{mode}_{category}")]
            ]))
    except: pass

# ── TEST JAVOB ────────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("ans_"))
async def handle_test_answer(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    q_id, user_answer, correct_letter = int(parts[1]), parts[2], parts[3]
    user_id = callback.from_user.id
    if db.already_answered(user_id, q_id):
        await callback.answer("⚠️ Allaqachon javob bergansiz!", show_alert=True); return
    question = db.get_question_by_id(q_id)
    if not question:
        await callback.answer("Savol topilmadi!", show_alert=True); return

    q_id, q_text, q_type, options, correct, coins, cat, diff, explanation, image_id, time_limit = question
    is_correct = user_answer.upper() == correct_letter.upper()
    db.save_answer(user_id, q_id, is_correct)

    # Timerni bekor qil
    if user_id in active_timers:
        active_timers[user_id].cancel()
        active_timers.pop(user_id, None)

    data = await state.get_data()
    category = data.get("category", "Barchasi")
    mode = data.get("qmode", "all")

    if is_correct:
        new_streak = db.update_streak(user_id, True)
        bonus = streak_bonus(new_streak)
        earned = round(coins * bonus, 1)
        db.add_coins(user_id, earned)
        text = f"✅ <b>To'g'ri!</b> +{earned} coin 🎉"
        if bonus > 1: text += f"\n🔥 Streak bonusi x{bonus}!"
        sm = streak_message(new_streak)
        if sm: text += f"\n{sm}"
    else:
        db.update_streak(user_id, False)
        penalty = round(coins * PENALTY_PERCENT, 1)
        db.add_coins(user_id, -penalty)
        opts_list = options.split("|")
        correct_idx = ord(correct.upper()) - 65
        correct_text = opts_list[correct_idx] if correct_idx < len(opts_list) else correct
        text = f"❌ <b>Noto'g'ri!</b> -{penalty} coin\n✅ To'g'ri javob: <b>{correct_text}</b>"

    if explanation: text += f"\n\n💡 <i>{explanation}</i>"
    user_data = db.get_user(user_id)
    total_coins = round(user_data[3], 1) if user_data else 0
    streak = user_data[6] if user_data else 0
    text += f"\n\n💰 Coinlar: <b>{total_coins}</b>  🔥 Streak: <b>{streak}</b>"

    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    try: await bot.send_sticker(callback.message.chat.id, sticker=get_correct_sticker(coins) if is_correct else get_wrong_sticker(coins))
    except: pass
    await callback.message.answer(text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data=f"next_{mode}_{category}")]
        ]))
    await callback.answer()

# ── OCHIQ SAVOL ───────────────────────────────────────────────────────────────
@dp.message(UserStates.answering_open)
async def handle_open_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_id = data["question_id"]
    correct = data["correct"]
    coins = data["coins"]
    explanation = data.get("explanation", "")
    category = data.get("category", "Barchasi")
    mode = data.get("qmode", "all")
    user_id = message.from_user.id

    if db.already_answered(user_id, q_id):
        await state.clear(); return

    is_correct = check_open_answer(message.text, correct)
    db.save_answer(user_id, q_id, is_correct)

    # Timerni bekor qil
    if user_id in active_timers:
        active_timers[user_id].cancel()
        active_timers.pop(user_id, None)

    if is_correct:
        new_streak = db.update_streak(user_id, True)
        bonus = streak_bonus(new_streak)
        earned = round(coins * bonus, 1)
        db.add_coins(user_id, earned)
        text = f"✅ <b>To'g'ri!</b> +{earned} coin 🎉"
        if bonus > 1: text += f"\n🔥 Streak bonusi x{bonus}!"
        sm = streak_message(new_streak)
        if sm: text += f"\n{sm}"
    else:
        db.update_streak(user_id, False)
        penalty = round(coins * PENALTY_PERCENT, 1)
        db.add_coins(user_id, -penalty)
        # Ko'rsatish uchun birinchi to'g'ri javob
        first_correct = correct.split("\n")[0].strip()
        text = f"❌ <b>Noto'g'ri!</b> -{penalty} coin\n✅ To'g'ri javob: <b>{first_correct}</b>"

    if explanation: text += f"\n\n💡 <i>{explanation}</i>"
    user_data = db.get_user(user_id)
    total_coins = round(user_data[3], 1) if user_data else 0
    streak = user_data[6] if user_data else 0
    text += f"\n\n💰 Coinlar: <b>{total_coins}</b>  🔥 Streak: <b>{streak}</b>"

    try: await bot.send_sticker(message.chat.id, sticker=get_correct_sticker(coins) if is_correct else get_wrong_sticker(coins))
    except: pass
    await message.answer(text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data=f"next_{mode}_{category}")]
        ]))
    await state.clear()

@dp.callback_query(F.data.startswith("skip_open_"))
async def skip_open_question(callback: types.CallbackQuery, state: FSMContext):
    q_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    category = data.get("category", "Barchasi")
    mode = data.get("qmode", "all")
    await state.clear()
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer("⏭ O'tkazib yuborildi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data=f"next_{mode}_{category}")]
        ]))
    await callback.answer()

# ── KEYINGI SAVOL ─────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("next_"))
async def next_question(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_", 2)
    mode = parts[1]
    category = parts[2]
    await state.update_data(category=category, qmode=mode)
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await send_question(callback.message, callback.from_user.id, state, category, mode)
    await callback.answer()

# ── PREMIUM SAVOL ─────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("premium_start_"))
async def premium_start(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data[14:]
    await send_premium_question(callback.message, callback.from_user.id, state, category)
    await callback.answer()

async def send_premium_question(message, user_id, state, category):
    question = db.get_random_question(user_id, category, q_type="premium")
    if not question:
        await message.answer("😔 Premium savollar tugadi! Boshqa kategoriyani tanlang.")
        return

    q_id, q_text, q_type, options, correct, coins, cat, difficulty, explanation, image_id, time_limit = question
    await state.set_state(UserStates.answering_premium)
    await state.update_data(
        question_id=q_id, correct=correct, coins=coins,
        explanation=explanation, category=category, attempts=0
    )

    header = (
        f"⭐ <b>PREMIUM SAVOL</b>  🆔 #{q_id}\n"
        f"📂 <b>{cat}</b>\n"
        f"💰 To'g'ri javob: <b>+{coins} coin</b>\n"
        f"🔄 <b>3 ta urinish</b>  |  ⏭ O'tkazish mumkin  |  ❌ Jarima yo'q\n\n"
        f"❓ <b>{q_text}</b>"
    )

    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data=f"skip_premium_{q_id}_{category}")]
    ])

    if image_id:
        try: await bot.send_photo(message.chat.id, photo=image_id, caption=header + "\n\n✍️ <b>Javobingizni yozing:</b>", parse_mode="HTML")
        except: await message.answer(header + "\n\n✍️ <b>Javobingizni yozing:</b>", parse_mode="HTML")
    else:
        await message.answer(header + "\n\n✍️ <b>Javobingizni yozing:</b>", parse_mode="HTML")
    await message.answer("👆 Javob yozing yoki o'tkazing:", reply_markup=skip_kb)

@dp.message(UserStates.answering_premium)
async def handle_premium_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_id = data["question_id"]
    correct = data["correct"]
    coins = data["coins"]
    explanation = data.get("explanation", "")
    category = data.get("category", "Barchasi")
    attempts = data.get("attempts", 0)
    user_id = message.from_user.id

    if db.already_answered(user_id, q_id):
        await state.clear(); return

    is_correct = check_open_answer(message.text, correct)

    if is_correct:
        db.save_answer(user_id, q_id, True)
        new_streak = db.update_streak(user_id, True)
        bonus = streak_bonus(new_streak)
        earned = round(coins * bonus, 1)
        db.add_coins(user_id, earned)
        text = f"✅ <b>To'g'ri!</b> +{earned} coin 🎉"
        if bonus > 1: text += f"\n🔥 Streak bonusi x{bonus}!"
        sm = streak_message(new_streak)
        if sm: text += f"\n{sm}"
        if explanation: text += f"\n\n💡 <i>{explanation}</i>"
        user_data = db.get_user(user_id)
        total_coins = round(user_data[3], 1) if user_data else 0
        text += f"\n\n💰 Coinlar: <b>{total_coins}</b>"
        try: await bot.send_sticker(message.chat.id, sticker=get_correct_sticker(coins))
        except: pass
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Keyingi premium savol", callback_data=f"premium_start_{category}")]
        ])
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        await state.clear()
    else:
        attempts += 1
        remaining = 3 - attempts
        if remaining > 0:
            await state.update_data(attempts=attempts)
            await message.answer(
                f"❌ Noto'g'ri! <b>{remaining} ta urinish</b> qoldi. Qayta urinib ko'ring:",
                parse_mode="HTML"
            )
        else:
            # 3 urinish tugadi — jarima yo'q
            db.save_answer(user_id, q_id, False)
            db.update_streak(user_id, False)
            try: await bot.send_sticker(message.chat.id, sticker=random.choice(STICKERS_WRONG_RANDOM))
            except: pass
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Keyingi premium savol", callback_data=f"premium_start_{category}")]
            ])
            await message.answer("😔 3 ta urinish tugadi. Savol o'tkazib yuborildi.", parse_mode="HTML", reply_markup=keyboard)
            await state.clear()

@dp.callback_query(F.data.startswith("skip_premium_"))
async def skip_premium(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    q_id = int(parts[2])
    category = parts[3]
    db.save_answer(callback.from_user.id, q_id, False)
    await state.clear()
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Keyingi premium savol", callback_data=f"premium_start_{category}")]
    ])
    await callback.message.answer("⏭ O'tkazib yuborildi.", reply_markup=keyboard)
    await callback.answer()

# ── IELTS BO'LIMI ─────────────────────────────────────────────────────────────
@dp.message(F.text == "🎓 IELTS")
async def ielts_menu(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Writing", callback_data="ielts_writing"),
         InlineKeyboardButton(text="✍️ Essay", callback_data="ielts_essay")],
        [InlineKeyboardButton(text="📖 Reading", callback_data="ielts_reading"),
         InlineKeyboardButton(text="🗣 Speaking", callback_data="ielts_speaking")],
        [InlineKeyboardButton(text="🎧 Listening", callback_data="ielts_listening")],
    ])
    await message.answer(
        "🎓 <b>IELTS bo'limlari</b>\n\n"
        "AI yordamida mashq qiling va batafsil fikr-mulohaza oling!\n\n"
        "📝 Writing — yozma topshiriq\n"
        "✍️ Essay — akademik insho\n"
        "📖 Reading — o'qib tushunish\n"
        "🗣 Speaking — gapirish (ovoz)\n"
        "🎧 Listening — eshitib tushunish",
        parse_mode="HTML", reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("ielts_"))
async def ielts_section(callback: types.CallbackQuery, state: FSMContext):
    section = callback.data[6:]
    question = db.get_random_question(callback.from_user.id, q_type=section)
    if not question:
        await callback.answer(
            f"🎉 Bu bo'limdagi barcha savollarga javob berdingiz! Tez orada yangilari qo'shiladi.",
            show_alert=True
        )
        return

    q_id, q_text, q_type, options, correct, coins, cat, diff, explanation, image_id, time_limit = question
    await state.set_state(UserStates.answering_ielts)
    await state.update_data(question_id=q_id, q_type=q_type, coins=coins, section=section)

    time_note = f"\n⏰ <b>Tavsiya etilgan vaqt:</b> {time_limit}" if time_limit else ""
    icons = {"writing": "📝", "essay": "✍️", "reading": "📖", "speaking": "🗣", "listening": "🎧"}
    icon = icons.get(section, "🎓")
    header = f"{icon} <b>{section.upper()}</b>  🆔 #{q_id}{time_note}\n\n❓ <b>{q_text}</b>"

    if section == "reading":
        header += "\n\n📌 <i>Javoblarni qatorma-qator yozing (har bir javob alohida qatorda)</i>"
    elif section == "speaking":
        header += "\n\n🎙 <i>Javobingizni ovozli xabar yoki matn sifatida yuboring</i>"
    elif section == "listening":
        header += "\n\n🎧 <i>Ovozli xabar yuboring (audioga javob) yoki matn yozing</i>"
    else:
        header += "\n\n✍️ <i>Javobingizni yozing (qanchalik to'liq bo'lsa, shunchalik yaxshi)</i>"

    if image_id:
        try: await bot.send_photo(callback.message.chat.id, photo=image_id, caption=header, parse_mode="HTML")
        except: await callback.message.answer(header, parse_mode="HTML")
    else:
        await callback.message.answer(header, parse_mode="HTML")

    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data=f"skip_ielts_{section}")]
    ])
    await callback.message.answer("👆 Javob yuboring:", reply_markup=skip_kb)
    await callback.answer()

@dp.message(UserStates.answering_ielts)
async def handle_ielts_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_id = data["question_id"]
    q_type = data["q_type"]
    coins = data["coins"]
    section = data["section"]
    user_id = message.from_user.id

    IELTS_ALL = ["writing", "essay", "reading", "speaking", "listening"]

    if section in ["speaking", "listening"]:
        if message.voice:
            await message.answer("⏳ Tahlil qilinmoqda...")
            voice_note = f"Foydalanuvchi {section} bo'yicha ovozli xabar yubordi."
            if section == "speaking":
                prompt = f"""Siz IELTS Speaking baholovchisiz. O'zbek tilida baholang:

Kontekst: {voice_note}

1. Talaffuz va ravonlik
2. Leksika boyligi  
3. Grammatika
4. Mavzuga aloqadorlik

Band Score: X.X/9.0
Tavsiyalar bering."""
            else:
                prompt = f"""Siz IELTS Listening baholovchisiz. O'zbek tilida baholang:

Kontekst: {voice_note}

Listening mashqi uchun umumiy tavsiyalar bering va qanday yaxshilash mumkinligini ayting.

Band Score: X.X/9.0"""
            analysis = await groq_analyze(prompt)
        elif message.text:
            await message.answer("⏳ AI tahlil qilmoqda...")
            if section == "speaking":
                prompt = f"Siz IELTS Speaking baholovchisiz. Quyidagi matnni Speaking sifatida o'zbek tilida baholang:\n\n{message.text}\n\nBand Score: X.X/9.0. Tavsiyalar bering."
            else:
                prompt = f"Siz IELTS Listening baholovchisiz. Foydalanuvchi quyidagi javobni yozdi:\n\n{message.text}\n\nListening ko'nikmalarini yaxshilash bo'yicha o'zbek tilida tavsiya bering. Band Score: X.X/9.0"
            analysis = await groq_analyze(prompt)
        else:
            await message.answer(f"🎙 Ovozli xabar yoki matn yuboring!")
            return
    elif section == "reading":
        if not message.text:
            await message.answer("✍️ Matn yuboring!")
            return
        user_text = message.text
        question = db.get_question_by_id(q_id)
        correct_answers = question[4] if question else ""
        user_answers = [a.strip().lower() for a in user_text.split("\n") if a.strip()]
        correct_list = [a.strip().lower() for a in correct_answers.split("\n") if a.strip()]
        correct_count = sum(1 for ans in user_answers if ans in correct_list)
        total = len(correct_list)
        score = round((correct_count / total * 9), 1) if total > 0 else 0
        analysis = f"📖 <b>Reading natijasi</b>\n\n✅ To'g'ri: <b>{correct_count}/{total}</b>\nBand Score: <b>{score}/9.0</b>"
        if correct_count < total:
            wrong = [a for a in correct_list if a not in user_answers]
            analysis += "\n\n❌ To'g'ri javoblar:\n" + "\n".join([f"• {w}" for w in wrong])
        earned = round(coins * (correct_count / total), 1) if total > 0 else 0
        db.add_coins(user_id, earned)
        db.save_answer(user_id, q_id, correct_count == total)  # Qayta chiqmasligi uchun
        analysis += f"\n\n💰 +{earned} coin"
        await message.answer(analysis, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"➡️ Keyingi {section.upper()}", callback_data=f"ielts_{section}")]
            ]))
        await state.clear()
        return
    else:
        if not message.text:
            await message.answer("✍️ Matn yuboring!")
            return
        user_text = message.text
        await message.answer("⏳ AI tahlil qilmoqda...")

        if section == "writing":
            prompt = f"""Siz IELTS Writing baholovchisiz. Quyidagi Writing javobini O'ZBEK TILIDA baholang:

Javob:
{user_text}

Quyidagilarni baholang:
1. Task Achievement
2. Coherence and Cohesion
3. Lexical Resource
4. Grammatical Range and Accuracy

Har mezon uchun qisqa izoh.
Band Score: X.X/9.0
3 ta yaxshilash tavsiyasi."""

        elif section == "essay":
            prompt = f"""Siz akademik insho mutaxassisisiz. Inshoni O'ZBEK TILIDA tahlil qiling:

Insho:
{user_text}

1. Kirish (thesis)
2. Argumentlar
3. Xulosa
4. Akademik uslub
5. Grammatika

Umumiy baho: X/10
5 ta tavsiya bering."""

        analysis = await groq_analyze(prompt)

    # Band score dan coin hisoblash — AI javobidan score qidirish
    import re
    band_score = None
    # Turli formatlarni qidirish: 7.5/9.0, 7.5/9, 7/9, Band: 7.5 va h.k.
    patterns = [
        r'Band\s*Score[:\s]+(\d+\.?\d*)',
        r'(\d+\.?\d*)\s*/\s*9(?:\.0)?',
        r'(\d+\.?\d*)\s*ball',
        r'baho[:\s]+(\d+\.?\d*)',
        r'score[:\s]+(\d+\.?\d*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, analysis, re.IGNORECASE)
        if match:
            try:
                band_score = float(match.group(1))
                band_score = min(band_score, 9.0)
                break
            except:
                pass

    if band_score is not None:
        earned = round(coins * (band_score / 9.0), 1)
    else:
        earned = round(coins * 0.5, 1)  # Agar score topilmasa 50%

    # Coin va answered saqlash
    db.add_coins(user_id, earned)
    try:
        db.save_answer(user_id, q_id, True)
    except Exception as e:
        logging.warning(f"save_answer error: {e}")

    score_text = f"\n🎯 Band Score: <b>{band_score}/9.0</b>" if band_score is not None else ""
    await message.answer(
        f"🤖 <b>AI Tahlil:</b>\n\n{analysis}"
        f"{score_text}\n\n💰 +{earned} coin (max {coins})",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"➡️ Keyingi {section.upper()}", callback_data=f"ielts_{section}")]
        ])
    )
    await state.clear()

@dp.callback_query(F.data.startswith("skip_ielts_"))
async def skip_ielts(callback: types.CallbackQuery, state: FSMContext):
    section = callback.data[11:]
    # O'tkazilgan savol qayta chiqishi mumkin (save_answer chaqirmaymiz)
    await state.clear()
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer("⏭ O'tkazib yuborildi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"➡️ Keyingi {section.upper()}", callback_data=f"ielts_{section}")]
        ]))
    await callback.answer()

# ── AI CHAT ───────────────────────────────────────────────────────────────────
BUSY_STATES = [
    UserStates.answering_open,
    UserStates.answering_premium,
    UserStates.answering_ielts,
]

@dp.message(F.text == "🤖 AI Chat")
async def ai_chat_start(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    # Savol yoki IELTS paytida ishlamaydi
    busy = [UserStates.answering_open.state, UserStates.answering_premium.state, UserStates.answering_ielts.state]
    if current_state in busy:
        await message.answer("⚠️ Avval joriy savolingizga javob bering yoki o'tkazib yuboring!")
        return

    user = db.get_user(message.from_user.id)
    coins = round(user[3], 1) if user else 0

    if coins <= 0:
        await message.answer(
            f"❌ <b>AI Chat ishlamaydi!</b>\n\n"
            f"💰 Sizning coinlaringiz: <b>{coins}</b>\n\n"
            f"Avval savollarga javob berib coin to'plang!",
            parse_mode="HTML"
        )
        return

    await state.set_state(UserStates.ai_chat)
    await state.update_data(chat_history=[])
    await message.answer(
        f"🤖 <b>AI Chat</b>\n\n"
        f"💰 Coinlaringiz: <b>{coins}</b>\n"
        f"💸 Narx: har 15 belgi = 1 coin\n\n"
        f"Savolingizni yozing!\n"
        f"<i>Chiqish uchun /stop yozing</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🚪 AI Chatdan chiqish")]],
            resize_keyboard=True
        )
    )

@dp.message(F.text == "🚪 AI Chatdan chiqish")
async def ai_chat_exit(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 AI Chatdan chiqdingiz!", reply_markup=main_menu(message.from_user.id))

@dp.message(Command("stop"))
async def stop_cmd(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == UserStates.ai_chat.state:
        await state.clear()
        await message.answer("👋 AI Chatdan chiqdingiz!", reply_markup=main_menu(message.from_user.id))

@dp.message(UserStates.ai_chat)
async def handle_ai_chat(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("✍️ Faqat matn yuboring!")
        return

    user_id = message.from_user.id
    user_text = message.text.strip()

    # Qonunbuzarlik tekshiruvi
    text_lower = user_text.lower()
    for word in ILLEGAL_WORDS:
        if word in text_lower:
            penalty = 10
            db.add_coins(user_id, -penalty)
            user = db.get_user(user_id)
            coins_left = round(user[3], 1) if user else 0
            await message.answer(
                f"🚫 <b>JARIMA!</b>\n\n"
                f"Siz qonunbuzarlikka doir so'rov yubordingiz.\n"
                f"❌ -{penalty} coin jarima.\n"
                f"💰 Qolgan coinlar: <b>{coins_left}</b>",
                parse_mode="HTML"
            )
            return

    # Coin tekshiruvi
    user = db.get_user(user_id)
    coins = round(user[3], 1) if user else 0

    if coins <= 0:
        await state.clear()
        await message.answer(
            "❌ <b>Coinlaringiz tugadi!</b>\n\nSavollarga javob berib coin to'plang.",
            parse_mode="HTML", reply_markup=main_menu(user_id)
        )
        return

    data = await state.get_data()
    chat_history = data.get("chat_history", [])

    # AI dan javob olish
    await message.answer("⏳ AI o'ylayapti...")

    # Tarix bilan prompt
    messages = [
        {"role": "system", "content": "Siz BilimChallenge botining yordamchi AI sisiz. O'zbek tilida qisqa, foydali va do'stona javob bering. Qonunbuzarlik, zararli yoki noetik so'rovlarga javob bermang."}
    ]
    for h in chat_history[-6:]:  # Oxirgi 6 ta xabar (kontekst)
        messages.append(h)
    messages.append({"role": "user", "content": user_text})

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        # Tarix bilan prompt
        full_prompt = "Siz BilimChallenge botining yordamchi AI sisiz. O'zbek tilida qisqa, foydali va do'stona javob bering. Qonunbuzarlik, zararli yoki noetik so'rovlarga javob bermang.\n\n"
        for h in chat_history[-6:]:
            role = "Foydalanuvchi" if h["role"] == "user" else "AI"
            full_prompt += f"{role}: {h['content']}\n"
        full_prompt += f"Foydalanuvchi: {user_text}\nAI:"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": full_prompt}]}]}
            ) as resp:
                resp_data = await resp.json()
                ai_reply = resp_data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        await message.answer(f"⚠️ AI xatolik: {str(e)}")
        return

    # Coin hisoblash: har 15 belgi = 1 coin
    reply_len = len(ai_reply)
    cost = max(1, reply_len // 15)

    if coins < cost:
        # Yetmaydi — qarz olsinmi?
        await state.update_data(
            pending_reply=ai_reply,
            pending_cost=cost,
            chat_history=chat_history
        )
        await state.set_state(UserStates.ai_chat_confirm_debt)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Ha, qarz olaman", callback_data="ai_debt_yes")],
            [InlineKeyboardButton(text="❌ Yo'q, kerak emas", callback_data="ai_debt_no")],
        ])
        await message.answer(
            f"⚠️ <b>Coin yetarli emas!</b>\n\n"
            f"💰 Sizda: <b>{coins}</b> coin\n"
            f"💸 Kerak: <b>{cost}</b> coin\n"
            f"📉 Qarz: <b>{cost - coins}</b> coin\n\n"
            f"Qarz olishni xohlaysizmi?",
            parse_mode="HTML", reply_markup=keyboard
        )
        return

    # Coin yetarli — to'lov
    db.add_coins(user_id, -cost)
    user = db.get_user(user_id)
    coins_left = round(user[3], 1) if user else 0

    # Tarixni yangilash
    chat_history.append({"role": "user", "content": user_text})
    chat_history.append({"role": "assistant", "content": ai_reply})
    await state.update_data(chat_history=chat_history)
    await state.set_state(UserStates.ai_chat)

    await message.answer(
        f"🤖 {ai_reply}\n\n💰 -{cost} coin  |  Qoldi: <b>{coins_left}</b>",
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "ai_debt_yes")
async def ai_debt_yes(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ai_reply = data.get("pending_reply", "")
    cost = data.get("pending_cost", 0)
    chat_history = data.get("chat_history", [])
    user_id = callback.from_user.id

    db.add_coins(user_id, -cost)
    user = db.get_user(user_id)
    coins_left = round(user[3], 1) if user else 0

    chat_history.append({"role": "assistant", "content": ai_reply})
    await state.update_data(chat_history=chat_history)
    await state.set_state(UserStates.ai_chat)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"🤖 {ai_reply}\n\n💰 -{cost} coin  |  Qoldi: <b>{coins_left}</b>",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "ai_debt_no")
async def ai_debt_no(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("❌ Bekor qilindi. Savol bering yoki chatdan chiqing.")
    await state.set_state(UserStates.ai_chat)
    await callback.answer()

# ── REYTING ───────────────────────────────────────────────────────────────────
@dp.message(F.text == "🏆 Reyting")
async def show_leaderboard(message: types.Message):
    top = db.get_leaderboard(10)
    if not top:
        await message.answer("😔 Hali hech kim reyting ro'yxatida yo'q!")
        return
    try: await bot.send_sticker(message.chat.id, sticker=STICKER_LEADERBOARD)
    except: pass
    medals = ["🥇", "🥈", "🥉"]
    text = "🏆 <b>Global Reyting — Top 10</b>\n\n"
    for i, (uid, fname, uname, coins) in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = fname or uname or f"User{uid}"
        text += f"{medal} <b>{name}</b> — {round(coins, 1)} coin\n"
    rank = db.get_user_rank(message.from_user.id)
    text += f"\n📍 Sizning o'rningiz: <b>#{rank}</b>"
    await message.answer(text, parse_mode="HTML")
    rank_sticker = get_rank_sticker(rank)
    if rank_sticker:
        try:
            await bot.send_sticker(message.chat.id, sticker=rank_sticker)
            msgs = {1: "🎉 BIRINCHI O'RIN! Ajoyib!", 2: "🎉 IKKINCHI O'RIN! Zo'r!", 3: "🎉 UCHINCHI O'RIN!"}
            msg = msgs.get(rank, f"🎉 Top {rank} da turibsiz!")
            await message.answer(f"<b>{msg}</b>", parse_mode="HTML")
        except: pass

# ── PROFIL ────────────────────────────────────────────────────────────────────
@dp.message(F.text == "👤 Profilim")
async def show_profile(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Profil topilmadi!")
        return
    uid, username, fname, coins, total_ans, correct_ans, streak, max_streak, join_date = user
    rank = db.get_user_rank(uid)
    accuracy = round((correct_ans / total_ans * 100), 1) if total_ans > 0 else 0
    await message.answer(
        f"👤 <b>Profil — {fname}</b>\n\n"
        f"💰 Coinlar: <b>{round(coins, 1)}</b>\n"
        f"🏆 Reyting: <b>#{rank}</b>\n"
        f"🔥 Streak: <b>{streak}</b>  ⚡ Max: <b>{max_streak}</b>\n"
        f"📝 Javob: <b>{total_ans}</b>  ✅ To'g'ri: <b>{correct_ans}</b>\n"
        f"🎯 Aniqlik: <b>{accuracy}%</b>\n"
        f"📅 Qo'shilgan: <b>{join_date[:10]}</b>",
        parse_mode="HTML"
    )

# ── YORDAM ────────────────────────────────────────────────────────────────────
@dp.message(F.text == "ℹ️ Yordam")
async def show_help(message: types.Message):
    await message.answer(
        "ℹ️ <b>BilimChallenge — Yordam</b>\n\n"
        "🎯 <b>Savol olish</b> — kategoriya va tur tanlang\n"
        "🎓 <b>IELTS</b> — AI bilan Writing, Essay, Reading, Speaking\n"
        "🏆 <b>Reyting</b> — top 10\n"
        "👤 <b>Profilim</b> — statistika\n"
        "📝 <b>Taklif/Shikoyat</b> — adminga xabar\n\n"
        "<b>Coin tizimi:</b>\n"
        "✅ To'g'ri — coin olasiz\n"
        "❌ Noto'g'ri — 30% jarima (manfiy ham bo'lishi mumkin)\n"
        "⏰ Vaqt tugasa — 45% jarima\n\n"
        "<b>Streak:</b> 🔥x3=1.5  🔥🔥x5=2.0  🔥🔥🔥x10=3.0",
        parse_mode="HTML"
    )

# ── TAKLIF/SHIKOYAT ───────────────────────────────────────────────────────────
@dp.message(F.text == "📝 Taklif/Shikoyat")
async def feedback_start(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.sending_feedback)
    await message.answer("📝 <b>Taklif yoki shikoyatingizni yozing:</b>\n\n<i>Bekor qilish uchun /cancel</i>", parse_mode="HTML")

@dp.message(UserStates.sending_feedback)
async def receive_feedback(message: types.Message, state: FSMContext):
    user = message.from_user
    db.save_feedback(user.id, user.first_name or "", user.username or "", message.text)
    await state.clear()
    await message.answer("✅ <b>Xabaringiz adminga yuborildi! Rahmat!</b>", parse_mode="HTML", reply_markup=main_menu(user.id))

# ═══════════════════════════════════════════════════════════════════════════════
#                           ADMIN PANEL
# ═══════════════════════════════════════════════════════════════════════════════
@dp.message(F.text == "⚙️ Admin Panel")
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("⚙️ <b>Admin Panel</b>", parse_mode="HTML", reply_markup=admin_menu())

@dp.message(F.text == "🔙 Asosiy menyu")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Asosiy menyu", reply_markup=main_menu(message.from_user.id))

# ── TAKLIFLAR (ADMIN) ─────────────────────────────────────────────────────────
@dp.message(F.text == "💬 Takliflar")
async def show_feedbacks(message: types.Message):
    if not is_admin(message.from_user.id): return
    feedbacks = db.get_feedbacks(20)
    if not feedbacks:
        await message.answer("💬 Hali taklif/shikoyat yo'q.")
        return
    for fb in feedbacks[:10]:
        fb_id, user_id, fname, username, fb_text, fb_date, is_read = fb
        read_icon = "🆕" if not is_read else "✅"
        uname = f"@{username}" if username else f"ID:{user_id}"
        text = (
            f"{read_icon} <b>#{fb_id}</b> — {fname} ({uname})\n"
            f"📅 {fb_date[:10]}\n\n"
            f"{fb_text}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del_fb_{fb_id}")]
        ])
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Barchasini o'qilgan + tozalash", callback_data="mark_all_read")]
    ])
    await message.answer(f"Jami: <b>{len(feedbacks)}</b> ta taklif", parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("del_fb_"))
async def delete_feedback(callback: types.CallbackQuery):
    fb_id = int(callback.data[7:])
    db.delete_feedback(fb_id)
    await callback.message.edit_text("🗑 O'chirildi.")
    await callback.answer()

@dp.callback_query(F.data == "mark_all_read")
async def mark_all_read(callback: types.CallbackQuery):
    db.mark_feedbacks_read()
    await callback.message.edit_text("✅ Barchasi o'qilgan deb belgilandi va tozalandi!")
    await callback.answer()

# ── KATEGORIYALAR ─────────────────────────────────────────────────────────────
@dp.message(F.text == "📂 Kategoriyalar")
async def manage_categories(message: types.Message):
    if not is_admin(message.from_user.id): return
    cats_with_count = db.get_categories_with_count()
    text = "📂 <b>Kategoriyalar</b>\n\n"
    for cat, count in cats_with_count:
        text += f"• <b>{cat}</b> — {count} ta savol\n"
    if not cats_with_count: text += "Hali kategoriya yo'q"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi kategoriya", callback_data="add_category")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data="del_category_list")],
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data == "add_category")
async def add_cat_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_new_category)
    await callback.message.answer("📂 Yangi kategoriya nomini kiriting:")
    await callback.answer()

@dp.message(AdminStates.waiting_new_category)
async def save_new_category(message: types.Message, state: FSMContext):
    db.add_category(message.text.strip())
    await state.clear()
    await message.answer(f"✅ <b>{message.text.strip()}</b> qo'shildi!", parse_mode="HTML", reply_markup=admin_menu())

@dp.callback_query(F.data == "del_category_list")
async def del_cat_list(callback: types.CallbackQuery):
    cats = db.get_categories()
    if not cats:
        await callback.answer("Kategoriya yo'q!", show_alert=True); return
    buttons = [[InlineKeyboardButton(text=f"🗑 {c}", callback_data=f"delcat_{c}")] for c in cats]
    await callback.message.answer("Qaysi kategoriyani o'chirish?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("delcat_"))
async def delete_category(callback: types.CallbackQuery):
    cat = callback.data[7:]
    db.delete_category(cat)
    await callback.message.edit_text(f"✅ <b>{cat}</b> o'chirildi!", parse_mode="HTML")
    await callback.answer()

# ── SAVOL QO'SHISH ────────────────────────────────────────────────────────────
@dp.message(F.text == "➕ Savol qo'shish")
async def add_question_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    await state.set_state(AdminStates.waiting_question_type)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Test (A,B,C,D)", callback_data="qtype_test")],
        [InlineKeyboardButton(text="✍️ Ochiq savol", callback_data="qtype_open")],
        [InlineKeyboardButton(text="⭐ Premium savol", callback_data="qtype_premium")],
        [InlineKeyboardButton(text="📝 IELTS Writing", callback_data="qtype_writing")],
        [InlineKeyboardButton(text="✍️ IELTS Essay", callback_data="qtype_essay")],
        [InlineKeyboardButton(text="📖 IELTS Reading", callback_data="qtype_reading")],
        [InlineKeyboardButton(text="🗣 IELTS Speaking", callback_data="qtype_speaking")],
        [InlineKeyboardButton(text="🎧 IELTS Listening", callback_data="qtype_listening")],
    ])
    await message.answer("📌 Savol turini tanlang:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("qtype_"))
async def choose_qtype(callback: types.CallbackQuery, state: FSMContext):
    qtype = callback.data[6:]
    await state.update_data(q_type=qtype)
    await state.set_state(AdminStates.waiting_question_text)
    await callback.message.edit_text("✏️ Savol matnini kiriting:")
    await callback.answer()

@dp.message(AdminStates.waiting_question_text)
async def get_question_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    qtype = data["q_type"]

    # /done buyrug'i — to'plangan matnni saqlash
    if message.text and message.text.strip() == "/done":
        accumulated = data.get("accumulated_text", "")
        if not accumulated:
            await message.answer("⚠️ Avval matn yuboring!")
            return
        await state.update_data(q_text=accumulated)
        data = await state.get_data()
        if qtype == "reading":
            await state.set_state(AdminStates.waiting_correct_answer)
            await message.answer("✅ To'g'ri javoblarni kiriting (har biri yangi qatorda):")
        elif qtype in IELTS_TYPES:
            await state.update_data(correct="", options="")
            await state.set_state(AdminStates.waiting_coin_reward)
            await message.answer("💰 Bu savol uchun necha coin?")
        else:
            await state.set_state(AdminStates.waiting_correct_answer)
            await message.answer("✅ To'g'ri javobni kiriting:")
        return

    # Matnni to'plash (uzun matnlar uchun)
    if qtype in ["reading"] + IELTS_TYPES:
        prev = data.get("accumulated_text", "")
        new_text = (prev + "\n" + message.text).strip() if prev else message.text
        await state.update_data(accumulated_text=new_text)
        char_count = len(new_text)
        await message.answer(
            f"✅ Matn qabul qilindi ({char_count} belgi)\n\n"
            f"📝 Yana matn yuborishingiz mumkin (uzun bo'lsa davom eting)\n"
            f"✅ Tugatish uchun <b>/done</b> yozing",
            parse_mode="HTML"
        )
        return

    # Oddiy savollar — bir xabar yetarli
    await state.update_data(q_text=message.text)
    if qtype == "test":
        await state.set_state(AdminStates.waiting_options)
        await message.answer("📋 Variantlarni kiriting (har biri yangi qatorda):\n\nMisol:\nOsiyo\nAfrika\nAmerika\nYevropa")
    else:
        await state.set_state(AdminStates.waiting_correct_answer)
        await message.answer("✅ To'g'ri javobni kiriting (bir nechta bo'lsa har birini yangi qatordan):")

@dp.message(AdminStates.waiting_options)
async def get_options(message: types.Message, state: FSMContext):
    options = [o.strip() for o in message.text.split("\n") if o.strip()]
    if len(options) < 2:
        await message.answer("⚠️ Kamida 2 ta variant!"); return
    await state.update_data(options="|".join(options))
    await state.set_state(AdminStates.waiting_correct_answer)
    opts_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)])
    await message.answer(f"📋 Variantlar:\n{opts_text}\n\n✅ To'g'ri variant harfini kiriting (A/B/C/D):")

@dp.message(AdminStates.waiting_correct_answer)
async def get_correct_answer(message: types.Message, state: FSMContext):
    await state.update_data(correct=message.text.strip())
    await state.set_state(AdminStates.waiting_coin_reward)
    await message.answer("💰 Necha coin?")

@dp.message(AdminStates.waiting_coin_reward)
async def get_coins(message: types.Message, state: FSMContext):
    if not message.text.replace(".", "").isdigit():
        await message.answer("⚠️ Faqat raqam!"); return
    await state.update_data(coins=float(message.text))
    data = await state.get_data()
    qtype = data["q_type"]

    if qtype in IELTS_TYPES + ["premium"]:
        # IELTS va premium uchun qiyinlik yo'q, vaqt so'raymiz
        await state.set_state(AdminStates.waiting_time_limit)
        await message.answer("⏰ Ajratilgan vaqtni kiriting (masalan: 20 daqiqa, 40 min)\n<i>Kerak bo'lmasa '-' yozing</i>", parse_mode="HTML")
    else:
        await state.set_state(AdminStates.waiting_difficulty)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Oson", callback_data="diff_oson")],
            [InlineKeyboardButton(text="🟡 O'rta", callback_data="diff_orta")],
            [InlineKeyboardButton(text="🔴 Qiyin", callback_data="diff_qiyin")],
        ])
        await message.answer("📊 Qiyinlik darajasi:", reply_markup=keyboard)

@dp.message(AdminStates.waiting_time_limit)
async def get_time_limit(message: types.Message, state: FSMContext):
    time_limit = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(time_limit=time_limit, difficulty="orta")
    data = await state.get_data()
    qtype = data["q_type"]
    if qtype in IELTS_TYPES:
        # IELTS uchun kategoriya yo'q
        await state.update_data(category=qtype.upper())
        await state.set_state(AdminStates.waiting_explanation)
        await message.answer("💡 Tavsif (ixtiyoriy):\n<i>Kerak bo'lmasa '-' yozing</i>", parse_mode="HTML")
    else:
        await state.set_state(AdminStates.waiting_category)
        cats = db.get_categories()
        buttons = []
        row = []
        for cat in cats:
            row.append(InlineKeyboardButton(text=cat, callback_data=f"selcat_{cat}"))
            if len(row) == 2: buttons.append(row); row = []
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton(text="➕ Yangi kategoriya", callback_data="selcat_NEW")])
        await message.answer("📂 Kategoriyani tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("diff_"))
async def get_difficulty(callback: types.CallbackQuery, state: FSMContext):
    difficulty = callback.data.split("_")[1]
    await state.update_data(difficulty=difficulty, time_limit="")
    await state.set_state(AdminStates.waiting_category)
    cats = db.get_categories()
    buttons = []
    row = []
    for cat in cats:
        row.append(InlineKeyboardButton(text=cat, callback_data=f"selcat_{cat}"))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="➕ Yangi kategoriya", callback_data="selcat_NEW")])
    await callback.message.edit_text("📂 Kategoriyani tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("selcat_"))
async def select_category(callback: types.CallbackQuery, state: FSMContext):
    cat = callback.data[7:]
    if cat == "NEW":
        await callback.message.edit_text("📂 Yangi kategoriya nomini kiriting:")
        await callback.answer(); return
    await state.update_data(category=cat)
    await state.set_state(AdminStates.waiting_explanation)
    await callback.message.edit_text("💡 Tavsif (ixtiyoriy):\n<i>Kerak bo'lmasa '-' yozing</i>", parse_mode="HTML")
    await callback.answer()

@dp.message(AdminStates.waiting_category)
async def get_new_category(message: types.Message, state: FSMContext):
    db.add_category(message.text.strip())
    await state.update_data(category=message.text.strip())
    await state.set_state(AdminStates.waiting_explanation)
    await message.answer("💡 Tavsif:\n<i>Kerak bo'lmasa '-' yozing</i>", parse_mode="HTML")

@dp.message(AdminStates.waiting_explanation)
async def get_explanation(message: types.Message, state: FSMContext):
    explanation = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(explanation=explanation)
    await state.set_state(AdminStates.waiting_image)
    await message.answer("🖼 Rasm (ixtiyoriy):\n• Rasm yuklang\n• URL yuboring\n• Kerak bo'lmasa <b>'-'</b>", parse_mode="HTML")

@dp.message(AdminStates.waiting_image)
async def get_image(message: types.Message, state: FSMContext):
    image_id = ""
    if message.text and message.text.strip() == "-": image_id = ""
    elif message.photo: image_id = message.photo[-1].file_id
    elif message.text and message.text.startswith("http"): image_id = message.text.strip()
    await state.update_data(image_id=image_id)
    data = await state.get_data()

    diff_icon = DIFFICULTY_ICONS.get(data.get("difficulty", "orta"), "🟡")
    options_display = ""
    if data["q_type"] == "test":
        opts = data.get("options", "").split("|")
        options_display = "\n" + "\n".join([f"  {chr(65+i)}. {opt}" for i, opt in enumerate(opts)])
        options_display += f"\n✅ To'g'ri: {data['correct'].upper()}"
    elif data["q_type"] not in IELTS_TYPES:
        options_display = f"\n✅ Javob: {data['correct']}"

    time_info = f"\n⏰ Vaqt: {data.get('time_limit', '')}" if data.get("time_limit") else ""
    confirm = (
        f"📋 <b>Tekshiring:</b>\n\n"
        f"Tur: {data['q_type'].upper()}\n"
        f"❓ {data['q_text']}{options_display}\n"
        f"💰 {data['coins']} coin\n"
        f"{diff_icon} {DIFFICULTY_NAMES.get(data.get('difficulty','orta'))}\n"
        f"📂 {data.get('category', '')}{time_info}\n"
        f"🖼 Rasm: {'Ha' if image_id else 'Yoq'}\n\nSaqlash?"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Saqlash", callback_data="save_question"),
         InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_question")],
    ])
    await message.answer(confirm, parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data == "save_question")
async def save_question_cb(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    db.add_question(
        text=data["q_text"], q_type=data["q_type"],
        options=data.get("options", ""), correct=data.get("correct", ""),
        coins=data["coins"], category=data.get("category", "Umumiy"),
        difficulty=data.get("difficulty", "orta"), explanation=data.get("explanation", ""),
        image_id=data.get("image_id", ""), time_limit=data.get("time_limit", "")
    )
    await state.clear()
    await callback.message.edit_text("✅ <b>Savol saqlandi!</b>", parse_mode="HTML")
    await callback.message.answer("⚙️ Admin Panel", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query(F.data == "cancel_question")
async def cancel_question(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.message.answer("⚙️ Admin Panel", reply_markup=admin_menu())
    await callback.answer()

# ── SAVOLLAR RO'YXATI ─────────────────────────────────────────────────────────
@dp.message(F.text == "📋 Savollar ro'yxati")
async def list_questions(message: types.Message):
    if not is_admin(message.from_user.id): return
    questions = db.get_all_questions()
    if not questions:
        await message.answer("😔 Savollar yo'q."); return
    text = f"📋 <b>Jami: {len(questions)} ta</b>\n\n"
    for q in questions[:20]:
        q_id, q_text, q_type, _, _, coins, category, difficulty = q
        short = q_text[:30] + "..." if len(q_text) > 30 else q_text
        diff_icon = DIFFICULTY_ICONS.get(difficulty, "🟡")
        text += f"#{q_id} {diff_icon} [{category}] {short} ({coins}💰)\n"
    if len(questions) > 20: text += f"\n...va yana {len(questions)-20} ta"
    await message.answer(text, parse_mode="HTML")

# ── SAVOL O'CHIRISH / TAHRIRLASH ──────────────────────────────────────────────
@dp.message(F.text == "🗑 Savol o'chirish")
async def delete_prompt(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("🗑 O'chiriladigan savol ID sini yuboring:")

@dp.message(F.text == "✏️ Savol tahrirlash")
async def edit_prompt(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("✏️ Tahrirlanadigan savol ID sini yuboring:")

@dp.message(F.text.regexp(r'^\d+$'))
async def handle_id_input(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    q_id = int(message.text)
    question = db.get_question_by_id(q_id)
    if not question:
        await message.answer(f"❌ #{q_id} topilmadi."); return
    q_id, q_text, q_type, options, correct, coins, cat, diff, explanation, image_id, time_limit = question
    diff_icon = DIFFICULTY_ICONS.get(diff, "🟡")
    short = q_text[:60] + "..." if len(q_text) > 60 else q_text
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del_{q_id}"),
         InlineKeyboardButton(text="❌ Bekor", callback_data="del_cancel")],
        [InlineKeyboardButton(text="✏️ Savol matnini o'zgartir", callback_data=f"edf_{q_id}_text")],
        [InlineKeyboardButton(text="📋 Variantlarni o'zgartir", callback_data=f"edf_{q_id}_options")],
        [InlineKeyboardButton(text="✅ To'g'ri javobni o'zgartir", callback_data=f"edf_{q_id}_correct")],
        [InlineKeyboardButton(text="💰 Coinni o'zgartir", callback_data=f"edf_{q_id}_coins")],
        [InlineKeyboardButton(text="💡 Tavsifni o'zgartir", callback_data=f"edf_{q_id}_explanation")],
        [InlineKeyboardButton(text="📂 Kategoriyani o'zgartir", callback_data=f"edf_{q_id}_category")],
        [InlineKeyboardButton(text="⏰ Vaqt limitini o'zgartir", callback_data=f"edf_{q_id}_time_limit")],
        [InlineKeyboardButton(text="🖼 Rasmni o'zgartir", callback_data=f"edf_{q_id}_image_id")],
    ])
    await message.answer(f"#{q_id} {diff_icon} [{cat}]\n❓ {short}\n💰 {coins} coin\nTur: {q_type}", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("edf_"))
async def edit_field(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    q_id = int(parts[1])
    field = parts[2]
    await state.update_data(edit_q_id=q_id, edit_field=field)
    await state.set_state(AdminStates.editing_field)

    # Hozirgi qiymatni ko'rsatish
    question = db.get_question_by_id(q_id)
    current_values = {}
    if question:
        q_id_r, q_text, q_type, options, correct, coins, cat, diff, explanation, image_id, time_limit = question
        current_values = {
            "text": q_text,
            "options": options.replace("|", "\n") if options else "",
            "correct": correct,
            "coins": str(coins),
            "explanation": explanation or "Yo'q",
            "category": cat,
            "time_limit": time_limit or "Yo'q",
            "image_id": "Bor ✅" if image_id else "Yo'q",
        }

    current = current_values.get(field, "")
    prompts = {
        "text": f"✏️ Hozirgi savol matni:\n<i>{current}</i>\n\nYangi matnni kiriting:",
        "options": f"📋 Hozirgi variantlar:\n<i>{current}</i>\n\nYangi variantlarni kiriting (har biri yangi qatorda):",
        "correct": f"✅ Hozirgi to'g'ri javob: <i>{current}</i>\n\nYangi javobni kiriting:",
        "coins": f"💰 Hozirgi coin: <i>{current}</i>\n\nYangi miqdorni kiriting:",
        "explanation": f"💡 Hozirgi tavsif: <i>{current}</i>\n\nYangi tavsifni kiriting ('-' = o'chirish):",
        "category": f"📂 Hozirgi kategoriya: <i>{current}</i>\n\nYangi kategoriya nomini kiriting:",
        "time_limit": f"⏰ Hozirgi vaqt: <i>{current}</i>\n\nYangi vaqtni kiriting ('-' = o'chirish):",
        "image_id": f"🖼 Rasm: <i>{current}</i>\n\nRasm yuboring yoki URL kiriting ('-' = o'chirish):",
    }
    await callback.message.answer(prompts.get(field, "Yangi qiymat:"), parse_mode="HTML")
    await callback.answer()

@dp.message(AdminStates.editing_field)
async def save_edit(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_id = data["edit_q_id"]
    field = data["edit_field"]
    if field == "image_id":
        value = message.photo[-1].file_id if message.photo else ("" if message.text.strip() == "-" else message.text.strip())
    elif field == "coins":
        if not message.text.replace(".", "").isdigit():
            await message.answer("⚠️ Faqat raqam!"); return
        value = float(message.text)
    elif field == "options":
        opts = [o.strip() for o in message.text.split("\n") if o.strip()]
        value = "|".join(opts)
    elif field in ("explanation", "time_limit"):
        value = "" if message.text.strip() == "-" else message.text.strip()
    else:
        value = message.text.strip()
    db.update_question_field(q_id, field, value)
    await state.clear()
    await message.answer(f"✅ #{q_id} yangilandi!", reply_markup=admin_menu())

@dp.callback_query(F.data.startswith("del_"))
async def confirm_delete(callback: types.CallbackQuery):
    if callback.data == "del_cancel":
        await callback.message.edit_text("❌ Bekor qilindi."); await callback.answer(); return
    q_id = int(callback.data.split("_")[1])
    db.delete_question(q_id)
    await callback.message.edit_text(f"✅ #{q_id} o'chirildi!")
    await callback.answer()

# ── STATISTIKA / FOYDALANUVCHILAR ─────────────────────────────────────────────
@dp.message(F.text == "👥 Foydalanuvchilar")
async def list_users(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer(f"👥 <b>Foydalanuvchilar</b>\n\nJami: <b>{db.get_total_users()}</b>\nFaol: <b>{db.get_active_users()}</b>", parse_mode="HTML")

@dp.message(F.text == "📊 Statistika")
async def show_stats(message: types.Message):
    if not is_admin(message.from_user.id): return
    s = db.get_stats()
    await message.answer(
        f"📊 <b>Statistika</b>\n\n👥 {s['users']}\n❓ {s['questions']}\n📝 {s['answers']}\n✅ {s['correct']}\n🎯 {s['accuracy']}%",
        parse_mode="HTML"
    )

# ── BROADCAST ─────────────────────────────────────────────────────────────────
@dp.message(F.text == "📢 Xabar yuborish")
async def broadcast_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdminStates.broadcast_text)
    await message.answer("📢 Xabar matnini kiriting:\n<i>/cancel — bekor qilish</i>", parse_mode="HTML")

@dp.message(AdminStates.broadcast_text)
async def broadcast_get_text(message: types.Message, state: FSMContext):
    await state.update_data(broadcast_text=message.text)
    await state.set_state(AdminStates.broadcast_image)
    await message.answer("🖼 Rasm (ixtiyoriy):\nRasm yuklang yoki <b>'-'</b> yozing", parse_mode="HTML")

@dp.message(AdminStates.broadcast_image)
async def broadcast_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data["broadcast_text"]
    image_id = message.photo[-1].file_id if message.photo else ("" if message.text and message.text.strip() == "-" else (message.text or ""))
    await state.update_data(broadcast_image=image_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Yuborish", callback_data="confirm_broadcast"),
         InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_broadcast")]
    ])
    await message.answer(f"📢 <b>Xabar:</b>\n\n{text}\n\n🖼 Rasm: {'Ha' if image_id else 'Yoq'}\n\nYuborilsinmi?", parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data == "confirm_broadcast")
async def do_broadcast(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data["broadcast_text"]
    image_id = data.get("broadcast_image", "")
    users = db.get_all_user_ids()
    await callback.message.edit_text(f"📢 Yuborilmoqda... ({len(users)} ta)")
    success = failed = 0
    for uid in users:
        try:
            if image_id: await bot.send_photo(uid, photo=image_id, caption=text, parse_mode="HTML")
            else: await bot.send_message(uid, text, parse_mode="HTML")
            success += 1
        except: failed += 1
        await asyncio.sleep(0.05)
    await state.clear()
    await callback.message.answer(f"✅ Yuborildi!\n\n✅ {success} ta\n❌ {failed} ta", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor.")
    await callback.message.answer("⚙️ Admin Panel", reply_markup=admin_menu())
    await callback.answer()

# ── RUN ───────────────────────────────────────────────────────────────────────
async def main():
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
