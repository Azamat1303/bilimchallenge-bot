
import logging
import asyncio
import random
import re
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from database import db
from config import BOT_TOKEN, ADMIN_IDS, QUESTION_TIME, PENALTY_PERCENT, TIMEOUT_PENALTY, STREAK_BONUSES, GROQ_API_KEY, GROQ_MODEL

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DIFFICULTY_ICONS = {"oson": "🟢", "orta": "🟡", "qiyin": "🔴"}
DIFFICULTY_NAMES = {"oson": "Oson", "orta": "O'rta", "qiyin": "Qiyin"}
IELTS_TYPES = ["writing", "essay", "reading", "speaking"]

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
    broadcast_text = State()
    broadcast_image = State()

class UserStates(StatesGroup):
    answering_open = State()
    answering_premium = State()
    sending_feedback = State()
    answering_ielts = State()

# ── HELPERS ───────────────────────────────────────────────────────────────────
def is_admin(uid): return uid in ADMIN_IDS

def main_menu(uid):
    buttons = [
        [KeyboardButton(text="🎯 Savol olish"), KeyboardButton(text="🏆 Reyting")],
        [KeyboardButton(text="👤 Profilim"), KeyboardButton(text="ℹ️ Yordam")],
        [KeyboardButton(text="📝 Taklif/Shikoyat"), KeyboardButton(text="🎓 IELTS")],
    ]
    if is_admin(uid):
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])
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
    user_clean = user_ans.strip().lower()
    answers_list = [a.strip().lower() for a in correct_ans.split("\n") if a.strip()]
    return user_clean in answers_list

async def groq_analyze(prompt: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 1000, "temperature": 0.7},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ AI tahlil xatolik: {str(e)}"

def parse_band_score(text: str):
    match = re.search(r'[Bb]and\s*[Ss]core[:\s]+(\d+\.?\d*)\s*/\s*9', text)
    if match: return float(match.group(1))
    match2 = re.search(r'[Bb]aho[:\s]+(\d+\.?\d*)\s*/\s*10', text)
    if match2: return round(float(match2.group(1)) * 9 / 10, 1)
    return None

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
    await message.answer("Bekor qilindi.", reply_markup=main_menu(message.from_user.id))

# ── SAVOL OLISH ───────────────────────────────────────────────────────────────
@dp.message(F.text == "🎯 Savol olish")
async def get_question_start(message: types.Message, state: FSMContext):
    await state.clear()
    categories = db.get_categories()
    if not categories:
        await message.answer("😔 Hozircha savollar yo'q!")
        return
    buttons = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat_{cat}"))
        if len(row) == 2: buttons.append(row); row = []
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
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Test savollar", callback_data=f"qmode_test_{category}")],
        [InlineKeyboardButton(text="✍️ Ochiq savollar", callback_data=f"qmode_open_{category}")],
        [InlineKeyboardButton(text="🌐 Aralash", callback_data=f"qmode_all_{category}")],
    ])
    await callback.message.answer(f"📂 <b>{category}</b>\n\nSavol turini tanlang:",
                                  parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("qmode_"))
async def qmode_chosen(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_", 2)
    mode, category = parts[1], parts[2]
    await state.update_data(category=category, qmode=mode)
    try: await callback.message.delete()
    except: pass
    await send_question(callback.message, callback.from_user.id, state, category, mode)
    await callback.answer()

async def send_question(message, user_id, state, category, mode="all"):
    if mode == "test": types_to_try = ["test"]
    elif mode == "open": types_to_try = ["open"]
    else: types_to_try = ["test", "open"]

    question = None
    random.shuffle(types_to_try)
    for qt in types_to_try:
        question = db.get_random_question(user_id, category, q_type=qt)
        if question: break

    if not question:
        cats = db.get_categories()
        buttons = []
        row = []
        for cat in cats:
            row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat_{cat}"))
            if len(row) == 2: buttons.append(row); row = []
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton(text="🌐 Aralash", callback_data="cat_Barchasi")])
        await message.answer("🎉 <b>Bu bo'limdagi savollar tugadi!</b>\n\nBoshqa kategoriyani tanlang:",
                             parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return

    q_id, q_text, q_type, options, correct, coins, cat, difficulty, explanation, image_id, time_limit = question
    diff_icon = DIFFICULTY_ICONS.get(difficulty, "🟡")
    diff_name = DIFFICULTY_NAMES.get(difficulty, "O'rta")

    header = (
        f"🆔 <b>#{q_id}</b>  📂 <b>{cat}</b>  {diff_icon} <b>{diff_name}</b>\n"
        f"💰 To'g'ri: <b>+{coins} coin</b>  ❌ Noto'g'ri: <b>-{round(coins*PENALTY_PERCENT,1)} coin</b>\n"
        f"⏱ Vaqt: <b>{QUESTION_TIME} soniya</b>\n\n"
        f"❓ <b>{q_text}</b>"
    )

    try: await bot.send_sticker(message.chat.id, sticker=STICKER_QUESTION)
    except: pass

    if q_type == "test":
        shuffled_opts, new_correct = shuffle_options(options, correct)
        opts_list = shuffled_opts.split("|")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{chr(65+i)}. {opt}",
                                  callback_data=f"ans_{q_id}_{chr(65+i)}_{new_correct}")]
            for i, opt in enumerate(opts_list)
        ])
        if image_id:
            try: sent = await bot.send_photo(message.chat.id, photo=image_id, caption=header, parse_mode="HTML", reply_markup=keyboard)
            except: sent = await message.answer(header, parse_mode="HTML", reply_markup=keyboard)
        else:
            sent = await message.answer(header, parse_mode="HTML", reply_markup=keyboard)
        await state.update_data(question_id=q_id, msg_id=sent.message_id, chat_id=message.chat.id)
        asyncio.create_task(question_timeout(user_id, q_id, sent.message_id, message.chat.id, coins, state))

    else:  # open
        await state.set_state(UserStates.answering_open)
        await state.update_data(question_id=q_id, correct=correct, coins=coins, explanation=explanation)
        text = header + "\n\n✍️ <b>Javobingizni yozing:</b>"
        if image_id:
            try: await bot.send_photo(message.chat.id, photo=image_id, caption=text, parse_mode="HTML")
            except: await message.answer(text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
        asyncio.create_task(question_timeout(user_id, q_id, None, message.chat.id, coins, state))

async def question_timeout(user_id, q_id, msg_id, chat_id, coins, state):
    total = QUESTION_TIME
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
        try:
            if timer_msg is None: timer_msg = await bot.send_message(chat_id, f"⏱ <b>{remaining}s</b>  {bar}", parse_mode="HTML")
            else: await timer_msg.edit_text(f"⏱ <b>{remaining}s</b>  {bar}", parse_mode="HTML")
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
    if msg_id:
        try: await bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=None)
        except: pass
    try: await bot.send_sticker(chat_id, sticker=random.choice(STICKERS_TIMEOUT))
    except: pass

    data = await state.get_data()
    category = data.get("category", "Barchasi")
    mode = data.get("qmode", "all")
    try:
        await bot.send_message(
            chat_id,
            f"⏰ <b>Vaqt tugadi!</b>\n❌ -{penalty} coin jarima",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data=f"nextq_{mode}_{category}")]
            ])
        )
    except: pass

# ── TEST JAVOB ────────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("ans_"))
async def handle_test_answer(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    q_id, user_answer, correct_letter = int(parts[1]), parts[2], parts[3]
    user_id = callback.from_user.id

    if db.already_answered(user_id, q_id):
        await callback.answer("Allaqachon javob bergansiz!", show_alert=True)
        return

    question = db.get_question_by_id(q_id)
    if not question:
        await callback.answer("Savol topilmadi!", show_alert=True)
        return

    q_id, q_text, q_type, options, correct, coins, cat, diff, explanation, image_id, time_limit = question
    is_correct = user_answer.upper() == correct_letter.upper()
    db.save_answer(user_id, q_id, is_correct)

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
    text += f"\n\n💰 Coinlar: <b>{round(user_data[3], 1) if user_data else 0}</b>  🔥 Streak: <b>{user_data[6] if user_data else 0}</b>"

    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    try: await bot.send_sticker(callback.message.chat.id, sticker=get_correct_sticker(coins) if is_correct else get_wrong_sticker(coins))
    except: pass

    # Oddiy savol — "Keyingi savol" tugmasisiz, faqat natija
    await callback.message.answer(text, parse_mode="HTML")

    # 1.5 soniya kutib keyingi savolni avtomatik yuborish
    await asyncio.sleep(1.5)
    await send_question(callback.message, user_id, state, category, mode)
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
        await state.clear()
        return

    is_correct = check_open_answer(message.text, correct)
    db.save_answer(user_id, q_id, is_correct)

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
        first_correct = correct.split("\n")[0].strip()
        text = f"❌ <b>Noto'g'ri!</b> -{penalty} coin\n✅ To'g'ri javob: <b>{first_correct}</b>"

    if explanation: text += f"\n\n💡 <i>{explanation}</i>"
    user_data = db.get_user(user_id)
    text += f"\n\n💰 Coinlar: <b>{round(user_data[3], 1) if user_data else 0}</b>  🔥 Streak: <b>{user_data[6] if user_data else 0}</b>"

    try: await bot.send_sticker(message.chat.id, sticker=get_correct_sticker(coins) if is_correct else get_wrong_sticker(coins))
    except: pass

    await message.answer(text, parse_mode="HTML")
    await state.clear()

    # 1.5 soniya kutib keyingi savolni avtomatik yuborish
    await asyncio.sleep(1.5)
    await send_question(message, user_id, state, category, mode)

# ── TIMEOUT KEYINGI SAVOL (faqat timeout uchun tugma) ────────────────────────
@dp.callback_query(F.data.startswith("nextq_"))
async def next_question_after_timeout(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_", 2)
    mode, category = parts[1], parts[2]
    await state.update_data(category=category, qmode=mode)
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await send_question(callback.message, callback.from_user.id, state, category, mode)
    await callback.answer()

# ── PREMIUM SAVOL ─────────────────────────────────────────────────────────────
async def send_premium_question(message, user_id, state, category):
    question = db.get_random_question(user_id, category, q_type="premium")
    if not question:
        await message.answer(
            "😔 Bu kategoriyada premium savollar tugadi!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Boshqa kategoriya", callback_data="cat_Barchasi")]
            ])
        )
        return

    q_id, q_text, q_type, options, correct, coins, cat, difficulty, explanation, image_id, time_limit = question
    diff_icon = DIFFICULTY_ICONS.get(difficulty, "🟡")

    header = (
        f"⭐ <b>PREMIUM SAVOL</b>  {diff_icon}  🆔 <b>#{q_id}</b>\n"
        f"📂 <b>{cat}</b>\n"
        f"💰 To'g'ri: <b>+{coins} coin</b>  ✅ Jarima yo'q  ⏱ Vaqt yo'q\n"
        f"🔄 <b>3 ta urinish</b>  |  ⏭ O'tkazish mumkin\n\n"
        f"❓ <b>{q_text}</b>"
    )

    try: await bot.send_sticker(message.chat.id, sticker=STICKER_QUESTION)
    except: pass

    await state.update_data(
        prem_q_id=q_id, prem_correct=correct, prem_coins=coins,
        prem_explanation=explanation, prem_category=category,
        prem_attempts=0, prem_options=options
    )

    skip_btn = InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data=f"prem_skip_{category}")

    if options:
        shuffled_opts, new_correct = shuffle_options(options, correct)
        opts_list = shuffled_opts.split("|")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{chr(65+i)}. {opt}",
                                  callback_data=f"prem_ans_{q_id}_{chr(65+i)}_{new_correct}_1")]
            for i, opt in enumerate(opts_list)
        ] + [[skip_btn]])
        if image_id:
            try: await bot.send_photo(message.chat.id, photo=image_id, caption=header, parse_mode="HTML", reply_markup=keyboard)
            except: await message.answer(header, parse_mode="HTML", reply_markup=keyboard)
        else:
            await message.answer(header, parse_mode="HTML", reply_markup=keyboard)
    else:
        await state.set_state(UserStates.answering_premium)
        text = header + "\n\n✍️ <b>Javobingizni yozing:</b>"
        await message.answer(text, parse_mode="HTML",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[[skip_btn]]))

@dp.callback_query(F.data.startswith("prem_ans_"))
async def handle_premium_test_answer(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    q_id = int(parts[2])
    user_answer = parts[3]
    correct_letter = parts[4]
    attempt = int(parts[5])
    user_id = callback.from_user.id

    question = db.get_question_by_id(q_id)
    if not question:
        await callback.answer("Savol topilmadi!", show_alert=True)
        return

    q_id2, q_text, q_type, options, correct, coins, cat, diff, explanation, image_id, time_limit = question
    is_correct = user_answer.upper() == correct_letter.upper()
    data = await state.get_data()
    category = data.get("prem_category", "Barchasi")

    if is_correct:
        db.save_answer(user_id, q_id, True)
        new_streak = db.update_streak(user_id, True)
        bonus = streak_bonus(new_streak)
        earned = round(coins * bonus, 1)
        db.add_coins(user_id, earned)
        try: await callback.message.edit_reply_markup(reply_markup=None)
        except: pass
        try: await bot.send_sticker(callback.message.chat.id, sticker=get_correct_sticker(coins))
        except: pass
        text = f"✅ <b>To'g'ri!</b> +{earned} coin 🎉\n⭐ Premium — jarima yo'q edi!"
        if bonus > 1: text += f"\n🔥 Streak bonusi x{bonus}!"
        sm = streak_message(new_streak)
        if sm: text += f"\n{sm}"
        if explanation: text += f"\n\n💡 <i>{explanation}</i>"
        user_data = db.get_user(user_id)
        text += f"\n\n💰 Coinlar: <b>{round(user_data[3], 1) if user_data else 0}</b>"
        await callback.message.answer(text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Keyingi premium savol", callback_data=f"prem_next_{category}")]
            ]))
    else:
        try: await bot.send_sticker(callback.message.chat.id, sticker=get_wrong_sticker(coins))
        except: pass
        if attempt < 3:
            shuffled_opts, new_correct = shuffle_options(options, correct)
            opts_list = shuffled_opts.split("|")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{chr(65+i)}. {opt}",
                                      callback_data=f"prem_ans_{q_id}_{chr(65+i)}_{new_correct}_{attempt+1}")]
                for i, opt in enumerate(opts_list)
            ] + [[InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data=f"prem_skip_{category}")]])
            await callback.message.answer(
                f"❌ <b>Noto'g'ri!</b> Yana urinib ko'ring!\n"
                f"🔄 Qolgan urinishlar: <b>{3 - attempt}</b> ta  ⭐ Jarima yo'q!",
                parse_mode="HTML", reply_markup=keyboard
            )
        else:
            db.save_answer(user_id, q_id, False)
            db.update_streak(user_id, False)
            opts_list = options.split("|")
            correct_idx = ord(correct.upper()) - 65
            correct_text = opts_list[correct_idx] if correct_idx < len(opts_list) else correct
            try: await callback.message.edit_reply_markup(reply_markup=None)
            except: pass
            text = f"❌ <b>3 ta urinish tugadi!</b>\n✅ To'g'ri javob: <b>{correct_text}</b>\n⭐ Coin minuslenmadi!"
            if explanation: text += f"\n\n💡 <i>{explanation}</i>"
            await callback.message.answer(text, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⭐ Keyingi premium savol", callback_data=f"prem_next_{category}")]
                ]))
    await callback.answer()

@dp.message(UserStates.answering_premium)
async def handle_premium_open_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_id = data["prem_q_id"]
    correct = data["prem_correct"]
    coins = data["prem_coins"]
    explanation = data.get("prem_explanation", "")
    category = data.get("prem_category", "Barchasi")
    attempts = data.get("prem_attempts", 0)
    user_id = message.from_user.id

    is_correct = check_open_answer(message.text, correct)

    if is_correct:
        db.save_answer(user_id, q_id, True)
        new_streak = db.update_streak(user_id, True)
        bonus = streak_bonus(new_streak)
        earned = round(coins * bonus, 1)
        db.add_coins(user_id, earned)
        try: await bot.send_sticker(message.chat.id, sticker=get_correct_sticker(coins))
        except: pass
        text = f"✅ <b>To'g'ri!</b> +{earned} coin 🎉\n⭐ Premium — jarima yo'q edi!"
        if bonus > 1: text += f"\n🔥 Streak bonusi x{bonus}!"
        if explanation: text += f"\n\n💡 <i>{explanation}</i>"
        await message.answer(text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Keyingi premium savol", callback_data=f"prem_next_{category}")]
            ]))
        await state.clear()
    else:
        try: await bot.send_sticker(message.chat.id, sticker=get_wrong_sticker(coins))
        except: pass
        attempts += 1
        if attempts < 3:
            await state.update_data(prem_attempts=attempts)
            await message.answer(
                f"❌ <b>Noto'g'ri!</b> Yana urinib ko'ring!\n"
                f"🔄 Qolgan urinishlar: <b>{3 - attempts}</b> ta  ⭐ Jarima yo'q!",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data=f"prem_skip_{category}")]
                ])
            )
        else:
            db.save_answer(user_id, q_id, False)
            db.update_streak(user_id, False)
            text = f"❌ <b>3 ta urinish tugadi!</b>\n✅ To'g'ri javob: <b>{correct.split(chr(10))[0]}</b>\n⭐ Coin minuslenmadi!"
            if explanation: text += f"\n\n💡 <i>{explanation}</i>"
            await message.answer(text, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⭐ Keyingi premium savol", callback_data=f"prem_next_{category}")]
                ]))
            await state.clear()

@dp.callback_query(F.data.startswith("prem_skip_"))
async def premium_skip(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data[10:]
    await state.clear()
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer("⏭ O'tkazildi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Keyingi premium savol", callback_data=f"prem_next_{category}")]
        ]))
    await callback.answer()

@dp.callback_query(F.data.startswith("prem_next_"))
async def next_premium(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data[10:]
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await send_premium_question(callback.message, callback.from_user.id, state, category)
    await callback.answer()

# ── PREMIUM TUGMA (asosiy menyudan) ──────────────────────────────────────────
@dp.message(F.text == "⭐ Premium savollar")
async def premium_menu(message: types.Message, state: FSMContext):
    await state.clear()
    cats = db.get_categories()
    if not cats:
        await message.answer("😔 Hozircha premium savollar yo'q!")
        return
    buttons = []
    row = []
    for cat in cats:
        row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"prem_cat_{cat}"))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🌐 Aralash", callback_data="prem_cat_Barchasi")])
    await message.answer("⭐ <b>Premium — Kategoriya tanlang:</b>", parse_mode="HTML",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("prem_cat_"))
async def premium_cat_chosen(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data[9:]
    try: await callback.message.delete()
    except: pass
    await send_premium_question(callback.message, callback.from_user.id, state, category)
    await callback.answer()

# ── IELTS BO'LIMI ─────────────────────────────────────────────────────────────
@dp.message(F.text == "🎓 IELTS")
async def ielts_menu(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Writing", callback_data="ielts_writing")],
        [InlineKeyboardButton(text="✍️ Insho (Essay)", callback_data="ielts_essay")],
        [InlineKeyboardButton(text="📖 Reading", callback_data="ielts_reading")],
        [InlineKeyboardButton(text="🗣 Speaking", callback_data="ielts_speaking")],
    ])
    await message.answer(
        "🎓 <b>IELTS bo'limlari</b>\n\nAI yordamida mashq qiling va batafsil fikr-mulohaza oling!",
        parse_mode="HTML", reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("ielts_") & ~F.data.startswith("ielts_next_"))
async def ielts_section(callback: types.CallbackQuery, state: FSMContext):
    section = callback.data[6:]
    if section not in IELTS_TYPES:
        await callback.answer()
        return

    question = db.get_random_question(callback.from_user.id, q_type=section)
    if not question:
        await callback.answer(f"😔 Bu bo'limda hozircha savollar yo'q!", show_alert=True)
        return

    q_id, q_text, q_type, options, correct, coins, cat, diff, explanation, image_id, time_limit = question

    await state.set_state(UserStates.answering_ielts)
    await state.update_data(
        ielts_q_id=q_id, ielts_q_type=q_type, ielts_coins=coins,
        ielts_section=section, ielts_correct=correct
    )

    time_note = f"\n⏰ <b>Tavsiya etilgan vaqt:</b> {time_limit}" if time_limit else ""
    icons = {"writing": "📝", "essay": "✍️", "reading": "📖", "speaking": "🗣"}
    icon = icons.get(section, "🎓")

    header = f"{icon} <b>{section.upper()}</b>  🆔 #{q_id}{time_note}\n\n❓ <b>{q_text}</b>"

    if section == "reading":
        header += "\n\n📌 <i>Javoblarni qatorma-qator yozing (har bir javob alohida qatorda)</i>"
    elif section == "speaking":
        header += "\n\n🎙 <i>Javobingizni ovozli xabar sifatida yuboring</i>"
    else:
        header += "\n\n✍️ <i>Javobingizni yozing (qanchalik to'liq bo'lsa, shunchalik yaxshi baholanadi)</i>"

    if image_id:
        try: await bot.send_photo(callback.message.chat.id, photo=image_id, caption=header, parse_mode="HTML")
        except: await callback.message.answer(header, parse_mode="HTML")
    else:
        await callback.message.answer(header, parse_mode="HTML")

    # IELTS uchun O'tkazib yuborish tugmasi
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data=f"ielts_skip_{section}")]
    ])
    await callback.message.answer("👆 Javob yuboring:", reply_markup=skip_kb)
    await callback.answer()

@dp.message(UserStates.answering_ielts)
async def handle_ielts_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_id = data["ielts_q_id"]
    coins = data["ielts_coins"]
    section = data["ielts_section"]
    correct_raw = data.get("ielts_correct", "")
    user_id = message.from_user.id

    # Allaqachon javob berilganmi
    if db.already_answered(user_id, q_id):
        await state.clear()
        return

    # Speaking: faqat ovozli xabar
    if section == "speaking":
        if not message.voice:
            await message.answer("🎙 Iltimos, ovozli xabar yuboring!")
            return
        thinking = await message.answer("⏳ AI tahlil qilmoqda...")
        prompt = (
            f"Siz IELTS Speaking baholovchisiz. Foydalanuvchi ovozli javob yubordi.\n"
            f"Quyidagilarni o'zbek tilida baholang:\n"
            f"1. Talaffuz va ravonlik\n2. Leksika boyligi\n"
            f"3. Grammatika to'g'riligi\n4. Mazmu va aloqadorlik\n\n"
            f"Oxirida ALBATTA shu formatda yozing: Band Score: X.X/9.0"
        )
        analysis = await groq_analyze(prompt)

    elif section in ("writing", "essay"):
        if not message.text:
            await message.answer("✍️ Iltimos, matn yuboring!")
            return
        user_text = message.text
        thinking = await message.answer("⏳ AI tahlil qilmoqda...")
        if section == "writing":
            prompt = (
                f"Siz IELTS Writing baholovchisiz. Quyidagi Writing javobini o'zbek tilida baholang:\n\n"
                f"{user_text}\n\n"
                f"1. Task Achievement\n2. Coherence and Cohesion\n"
                f"3. Lexical Resource\n4. Grammatical Range and Accuracy\n\n"
                f"Oxirida ALBATTA shu formatda yozing: Band Score: X.X/9.0\n"
                f"Yaxshilash uchun 3 ta tavsiya bering."
            )
        else:
            prompt = (
                f"Siz akademik insho mutaxassisisiz. Quyidagi inshoni o'zbek tilida chuqur baholang:\n\n"
                f"{user_text}\n\n"
                f"1. Kirish qismi\n2. Argumentlar\n3. Xulosa\n"
                f"4. Akademik uslub\n5. Grammatika\n\n"
                f"Oxirida ALBATTA shu formatda yozing: Band Score: X.X/9.0\n"
                f"5 ta muhim tavsiya bering."
            )
        analysis = await groq_analyze(prompt)

    elif section == "reading":
        if not message.text:
            await message.answer("✍️ Iltimos, javob yozing!")
            return
        thinking = await message.answer("⏳ Tekshirilmoqda...")
        user_answers = [a.strip().lower() for a in message.text.split("\n") if a.strip()]
        correct_list = [a.strip().lower() for a in correct_raw.split("\n") if a.strip()]
        total = len(correct_list) if correct_list else 1
        correct_count = sum(1 for ans in user_answers if ans in correct_list)
        score_ratio = correct_count / total
        band_score = round(score_ratio * 9, 1)
        earned = round(coins * score_ratio, 1)

        db.save_answer(user_id, q_id, correct_count == total)
        db.add_coins(user_id, earned)

        try: await thinking.delete()
        except: pass

        result = (
            f"📖 <b>Reading natijasi</b>\n\n"
            f"✅ To'g'ri: <b>{correct_count}/{total}</b>\n"
            f"📊 Band Score: <b>{band_score}/9.0</b>\n"
            f"💰 +{earned} coin ({int(score_ratio*100)}%)"
        )
        if correct_count < total:
            missed = [a for a in correct_list if a not in user_answers]
            result += "\n\n❌ To'g'ri javoblar:\n" + "\n".join([f"• {w}" for w in missed])

        user_data = db.get_user(user_id)
        result += f"\n\n💰 Jami coinlar: <b>{round(user_data[3], 1) if user_data else 0}</b>"

        await message.answer(result, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➡️ Keyingi READING", callback_data="ielts_reading")]
            ]))
        await state.clear()
        return
    else:
        await state.clear()
        return

    # Writing/Essay/Speaking uchun Band Score ajratish
    band_score = parse_band_score(analysis)
    if band_score is not None:
        earned = round(coins * (band_score / 9), 1)
    else:
        earned = round(coins * 0.5, 1)

    db.save_answer(user_id, q_id, band_score is not None and band_score >= 5)
    db.add_coins(user_id, earned)

    try: await thinking.delete()
    except: pass

    user_data = db.get_user(user_id)
    score_text = f"📊 Band Score: <b>{band_score}/9.0</b>\n" if band_score else ""
    pct = int(earned / coins * 100) if coins > 0 else 0

    result_text = (
        f"🤖 <b>AI Tahlil:</b>\n\n{analysis}\n\n"
        f"{'─'*20}\n"
        f"{score_text}"
        f"💰 Coin: <b>+{earned}</b> ({pct}% — {band_score}/9.0 ballga qarab)\n"
        f"💰 Jami: <b>{round(user_data[3], 1) if user_data else 0}</b>"
    )

    section_names = {"writing": "WRITING", "essay": "ESSAY", "speaking": "SPEAKING"}
    await message.answer(result_text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"➡️ Keyingi {section_names.get(section, section.upper())}",
                                  callback_data=f"ielts_{section}")]
        ]))
    await state.clear()

@dp.callback_query(F.data.startswith("ielts_skip_"))
async def ielts_skip(callback: types.CallbackQuery, state: FSMContext):
    section = callback.data[11:]
    await state.clear()
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    section_names = {"writing": "WRITING", "essay": "ESSAY", "reading": "READING", "speaking": "SPEAKING"}
    await callback.message.answer("⏭ O'tkazildi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"➡️ Keyingi {section_names.get(section, section.upper())}",
                                  callback_data=f"ielts_{section}")]
        ]))
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
    coin_icon = "💰" if coins >= 0 else "📉"
    await message.answer(
        f"👤 <b>Profil — {fname}</b>\n\n"
        f"{coin_icon} Coinlar: <b>{round(coins, 1)}</b>\n"
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
        "🏆 <b>Reyting</b> — top 10\n👤 <b>Profilim</b> — statistika\n\n"
        "<b>Coin tizimi:</b>\n"
        "✅ To'g'ri — coin olasiz\n"
        "❌ Noto'g'ri — 30% jarima (manfiy ham bo'lishi mumkin)\n"
        "⏰ Vaqt tugasa — 45% jarima\n\n"
        "<b>IELTS coin:</b> AI Band Score ga qarab beriladi\n"
        "9.0/9.0 → 100%  |  5.0/9.0 → 55%\n\n"
        "<b>Streak:</b> 🔥x3=1.5  🔥🔥x5=2.0  🔥🔥🔥x10=3.0",
        parse_mode="HTML"
    )

# ── TAKLIF/SHIKOYAT ───────────────────────────────────────────────────────────
@dp.message(F.text == "📝 Taklif/Shikoyat")
async def feedback_start(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.sending_feedback)
    await message.answer(
        "📝 <b>Taklif yoki shikoyatingizni yozing:</b>\n\n<i>Bekor qilish: /cancel</i>",
        parse_mode="HTML"
    )

@dp.message(UserStates.sending_feedback)
async def receive_feedback(message: types.Message, state: FSMContext):
    user = message.from_user
    db.save_feedback(user.id, user.first_name or "", user.username or "", message.text)
    await state.clear()
    await message.answer("✅ <b>Xabaringiz adminga yuborildi! Rahmat!</b>",
                         parse_mode="HTML", reply_markup=main_menu(user.id))

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

# ── TAKLIFLAR ─────────────────────────────────────────────────────────────────
@dp.message(F.text == "💬 Takliflar")
async def show_feedbacks(message: types.Message):
    if not is_admin(message.from_user.id): return
    feedbacks = db.get_feedbacks(20)
    if not feedbacks:
        await message.answer("💬 Hali taklif/shikoyat yo'q.")
        return
    for fb in feedbacks[:10]:
        fb_id, user_id, fname, username, fb_text, fb_date, is_read = fb
        uname = f"@{username}" if username else f"ID:{user_id}"
        text = f"🆕 <b>#{fb_id}</b> — {fname} ({uname})\n📅 {fb_date[:10]}\n\n{fb_text}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del_fb_{fb_id}")]
        ])
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Barchasini o'chirish", callback_data="mark_all_read")]
    ])
    await message.answer(f"Jami: <b>{len(feedbacks)}</b> ta", parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("del_fb_"))
async def delete_feedback(callback: types.CallbackQuery):
    fb_id = int(callback.data[7:])
    db.delete_feedback(fb_id)
    await callback.message.edit_text("🗑 O'chirildi.")
    await callback.answer()

@dp.callback_query(F.data == "mark_all_read")
async def mark_all_read(callback: types.CallbackQuery):
    db.mark_feedbacks_read()
    await callback.message.edit_text("✅ Barchasi o'chirildi!")
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
        [InlineKeyboardButton(text="➕ Yangi", callback_data="add_category")],
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
    await callback.message.answer("Qaysi kategoriyani o'chirish?",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
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
    await state.update_data(q_text=message.text)
    data = await state.get_data()
    qtype = data["q_type"]
    if qtype == "test":
        await state.set_state(AdminStates.waiting_options)
        await message.answer("📋 Variantlarni kiriting (har biri yangi qatorda):\n\nMisol:\nOsiyo\nAfrika\nAmerika\nYevropa")
    elif qtype == "reading":
        await state.set_state(AdminStates.waiting_correct_answer)
        await message.answer("✅ To'g'ri javoblarni kiriting (har biri yangi qatorda):")
    elif qtype in IELTS_TYPES:
        await state.update_data(correct="", options="")
        await state.set_state(AdminStates.waiting_coin_reward)
        await message.answer("💰 Bu savol uchun necha coin (maksimum)?")
    else:
        await state.set_state(AdminStates.waiting_correct_answer)
        await message.answer(
            "✅ To'g'ri javob(lar)ni kiriting:\n\n"
            "<i>Bir nechta to'g'ri javob bo'lsa, har birini yangi qatordan yozing</i>",
            parse_mode="HTML"
        )

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
    try:
        coins = float(message.text.replace(",", "."))
    except:
        await message.answer("⚠️ Faqat raqam!"); return
    await state.update_data(coins=coins)
    data = await state.get_data()
    qtype = data["q_type"]
    if qtype in IELTS_TYPES + ["premium"]:
        await state.set_state(AdminStates.waiting_time_limit)
        await message.answer(
            "⏰ Ajratilgan vaqtni kiriting (masalan: 20 daqiqa, 40 min)\n"
            "<i>Kerak bo'lmasa '-' yozing</i>", parse_mode="HTML"
        )
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
        await state.update_data(category=qtype.upper())
        await state.set_state(AdminStates.waiting_image)
        await message.answer("🖼 Rasm (ixtiyoriy):\nRasm yuklang yoki <b>'-'</b> yozing", parse_mode="HTML")
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
    await callback.message.edit_text("📂 Kategoriyani tanlang:",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
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
    await message.answer("🖼 Rasm (ixtiyoriy):\nRasm yuklang yoki <b>'-'</b> yozing", parse_mode="HTML")

@dp.message(AdminStates.waiting_image)
async def get_image(message: types.Message, state: FSMContext):
    image_id = ""
    if message.photo: image_id = message.photo[-1].file_id
    elif message.text and message.text.strip() != "-" and message.text.startswith("http"): image_id = message.text.strip()
    await state.update_data(image_id=image_id)
    data = await state.get_data()

    diff_icon = DIFFICULTY_ICONS.get(data.get("difficulty", "orta"), "🟡")
    options_display = ""
    if data["q_type"] == "test":
        opts = data.get("options", "").split("|")
        options_display = "\n" + "\n".join([f"  {chr(65+i)}. {opt}" for i, opt in enumerate(opts)])
        options_display += f"\n✅ To'g'ri: {data.get('correct', '').upper()}"
    elif data["q_type"] not in IELTS_TYPES:
        c = data.get("correct", "")
        options_display = f"\n✅ Javob: {c[:50]}"
    time_info = f"\n⏰ Vaqt: {data.get('time_limit', '')}" if data.get("time_limit") else ""
    confirm = (
        f"📋 <b>Tekshiring:</b>\n\n"
        f"Tur: <b>{data['q_type'].upper()}</b>\n"
        f"❓ {data['q_text'][:80]}{options_display}\n"
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

    # Foydalanuvchilarga bildirishnoma
    users = db.get_all_user_ids()
    if users and data["q_type"] not in IELTS_TYPES:
        diff_icon = DIFFICULTY_ICONS.get(data.get("difficulty", "orta"), "🟡")
        type_icon = {"test": "📝", "open": "✍️", "premium": "⭐"}.get(data["q_type"], "📌")
        notify = (
            f"🆕 <b>Yangi savol qo'shildi!</b>\n\n"
            f"📂 <b>{data.get('category', '')}</b>  {type_icon}  {diff_icon}\n"
            f"💰 Coin: <b>{data['coins']}</b>\n\n"
            f"🎯 <b>Savol olish</b> tugmasini bosing!"
        )
        sent = 0
        for uid in users:
            try:
                await bot.send_message(uid, notify, parse_mode="HTML")
                sent += 1
            except: pass
        await callback.message.answer(f"📢 {sent} ta foydalanuvchiga xabar yuborildi!", reply_markup=admin_menu())
    else:
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
    type_icons = {"test": "📝", "open": "✍️", "premium": "⭐", "writing": "📝W", "essay": "✍️E", "reading": "📖R", "speaking": "🗣S"}
    text = f"📋 <b>Jami: {len(questions)} ta</b>\n\n"
    for q in questions[:20]:
        q_id, q_text, q_type, _, _, coins, category, difficulty = q
        short = q_text[:30] + "..." if len(q_text) > 30 else q_text
        diff_icon = DIFFICULTY_ICONS.get(difficulty, "🟡")
        text += f"#{q_id} {type_icons.get(q_type,'📌')}{diff_icon} [{category}] {short} ({coins}💰)\n"
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
        [InlineKeyboardButton(text="✅ To'g'ri javobni o'zgartir", callback_data=f"edf_{q_id}_correct")],
        [InlineKeyboardButton(text="💰 Coinni o'zgartir", callback_data=f"edf_{q_id}_coins")],
        [InlineKeyboardButton(text="💡 Tavsifni o'zgartir", callback_data=f"edf_{q_id}_explanation")],
        [InlineKeyboardButton(text="📂 Kategoriyani o'zgartir", callback_data=f"edf_{q_id}_category")],
        [InlineKeyboardButton(text="⏰ Vaqt limitini o'zgartir", callback_data=f"edf_{q_id}_time_limit")],
        [InlineKeyboardButton(text="🖼 Rasmni o'zgartir", callback_data=f"edf_{q_id}_image_id")],
    ])
    await message.answer(
        f"#{q_id} {diff_icon} [{cat}] {q_type.upper()}\n❓ {short}\n💰 {coins} coin",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("edf_"))
async def edit_field(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    q_id = int(parts[1])
    field = parts[2]
    await state.update_data(edit_q_id=q_id, edit_field=field)
    await state.set_state(AdminStates.editing_field)
    prompts = {
        "text": "Yangi savol matnini kiriting:",
        "correct": "Yangi to'g'ri javobni kiriting:",
        "coins": "Yangi coin miqdorini kiriting:",
        "explanation": "Yangi tavsifni kiriting:",
        "category": "Yangi kategoriya nomini kiriting:",
        "time_limit": "Yangi vaqt limitini kiriting ('-' = o'chirish):",
        "image_id": "Rasm yuboring yoki URL kiriting ('-' = o'chirish):",
    }
    await callback.message.answer(prompts.get(field, "Yangi qiymat:"))
    await callback.answer()

@dp.message(AdminStates.editing_field)
async def save_edit(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_id = data["edit_q_id"]
    field = data["edit_field"]
    if field == "image_id":
        value = message.photo[-1].file_id if message.photo else ("" if message.text.strip() == "-" else message.text.strip())
    elif field == "coins":
        try: value = float(message.text.replace(",", "."))
        except:
            await message.answer("⚠️ Faqat raqam!"); return
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
        await callback.message.edit_text("Bekor qilindi."); await callback.answer(); return
    q_id = int(callback.data.split("_")[1])
    db.delete_question(q_id)
    await callback.message.edit_text(f"✅ #{q_id} o'chirildi!")
    await callback.answer()

# ── STATISTIKA / FOYDALANUVCHILAR ─────────────────────────────────────────────
@dp.message(F.text == "👥 Foydalanuvchilar")
async def list_users(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer(
        f"👥 <b>Foydalanuvchilar</b>\n\nJami: <b>{db.get_total_users()}</b>\nFaol: <b>{db.get_active_users()}</b>",
        parse_mode="HTML"
    )

@dp.message(F.text == "📊 Statistika")
async def show_stats(message: types.Message):
    if not is_admin(message.from_user.id): return
    s = db.get_stats()
    await message.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{s['users']}</b>\n"
        f"❓ Savollar: <b>{s['questions']}</b>\n"
        f"📝 Javoblar: <b>{s['answers']}</b>\n"
        f"✅ To'g'ri: <b>{s['correct']}</b>\n"
        f"🎯 Aniqlik: <b>{s['accuracy']}%</b>",
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
    await message.answer(
        f"📢 <b>Xabar:</b>\n\n{text}\n\n🖼 Rasm: {'Ha' if image_id else 'Yoq'}\n\nYuborilsinmi?",
        parse_mode="HTML", reply_markup=keyboard
    )

@dp.callback_query(F.data == "confirm_broadcast")
async def do_broadcast(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data["broadcast_text"]
    image_id = data.get("broadcast_image", "")
    users = db.get_all_user_ids()
    await callback.message.edit_text(f"📢 Yuborilmoqda... ({len(users)} ta)")
    success = failed = 0
    for i, uid in enumerate(users):
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
ENDOFFILE
echo "done"
