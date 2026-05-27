import logging
import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from database import db
from config import BOT_TOKEN, ADMIN_IDS, QUESTION_TIME, PENALTY_PERCENT, STREAK_BONUSES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

DIFFICULTY_ICONS = {"oson": "🟢", "orta": "🟡", "qiyin": "🔴"}
DIFFICULTY_NAMES = {"oson": "Oson", "orta": "O'rta", "qiyin": "Qiyin"}

# ── Stikerlar ─────────────────────────────────────────────────────────────────
STICKER_QUESTION = "CAACAgIAAxkBAAFKw2JqFrdsWk9htpRwDxq9eAwYUa1ZXQACA1oAAnkIAUpLU6bVp7_sLDsE"  # 🤔 savol kelganda
STICKER_CORRECT  = "CAACAgIAAxkBAAFKw5VqFrluy9UnO2MewXZNLbJwB7J_ygACejIAAiaOCEnMbgcQ72sJ_DsE"  # ✅ to'g'ri javob
STICKER_WRONG    = "CAACAgIAAxkBAAFKw5NqFrle6l0Hv4ROqH0ISrfk5cK5bQAC7C8AAoa6-EjuktV0xKYEMTsE"  # ❌ noto'g'ri
STICKER_TIMEOUT  = "CAACAgIAAxkBAAFKw2ZqFrdzK3_NmWUcbh60u3WKoYfVygACb2AAAo386UkHCMIb6broyTsE"  # ⏰ vaqt tugadi

def timer_bar(seconds_left: int, total: int) -> str:
    """Oxirgi 10 soniyada ko'rinadigan progress bar"""
    filled = int((seconds_left / total) * 10)
    if seconds_left <= 3:
        block = "🟥"
    elif seconds_left <= 6:
        block = "🟧"
    else:
        block = "🟨"
    bar = block * filled + "⬜" * (10 - filled)
    return f"⏱ <b>{seconds_left}s</b>  {bar}"

# ─── STATES ───────────────────────────────────────────────────────────────────
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
    # Kategoriya boshqaruvi
    waiting_new_category = State()
    # Savol tahrirlash
    editing_field = State()
    editing_value = State()

class UserStates(StatesGroup):
    answering_open = State()

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def is_admin(user_id): return user_id in ADMIN_IDS

def main_menu(user_id):
    buttons = [
        [KeyboardButton(text="🎯 Savol olish"), KeyboardButton(text="🏆 Reyting")],
        [KeyboardButton(text="👤 Profilim"), KeyboardButton(text="ℹ️ Yordam")],
    ]
    if is_admin(user_id):
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def admin_menu():
    buttons = [
        [KeyboardButton(text="➕ Savol qo'shish"), KeyboardButton(text="📋 Savollar ro'yxati")],
        [KeyboardButton(text="✏️ Savol tahrirlash"), KeyboardButton(text="🗑 Savol o'chirish")],
        [KeyboardButton(text="📂 Kategoriyalar"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="👥 Foydalanuvchilar"), KeyboardButton(text="🔙 Asosiy menyu")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def streak_bonus(streak):
    bonus = 1.0
    for threshold in sorted(STREAK_BONUSES.keys()):
        if streak >= threshold:
            bonus = STREAK_BONUSES[threshold]
    return bonus

def streak_message(streak):
    if streak >= 10: return f"🔥🔥🔥 SUPER STREAK x{streak}!"
    if streak >= 5: return f"🔥🔥 STREAK x{streak}! Zo'r!"
    if streak >= 3: return f"🔥 STREAK x{streak}!"
    return ""

def shuffle_options(options_str, correct_letter):
    """Variantlarni aralashtiradi va yangi to'g'ri harf qaytaradi"""
    opts = options_str.split("|")
    correct_idx = ord(correct_letter.upper()) - 65
    if correct_idx >= len(opts):
        return options_str, correct_letter

    correct_text = opts[correct_idx]
    indices = list(range(len(opts)))
    random.shuffle(indices)
    shuffled = [opts[i] for i in indices]
    new_correct_idx = shuffled.index(correct_text)
    new_correct_letter = chr(65 + new_correct_idx)
    return "|".join(shuffled), new_correct_letter

# ─── /start ───────────────────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    db.add_user(user.id, user.username or "", user.first_name or "")
    text = (
        f"🧠 <b>BilimChallenge</b> ga xush kelibsiz, {user.first_name}!\n\n"
        f"🎯 Savollarga javob bering\n"
        f"💰 Coinlar to'plang\n"
        f"🔥 Streak yig'ing — bonus coinlar oling\n"
        f"🏆 Global reytingda o'z o'rningizni egallang!\n\n"
        f"Boshlash uchun <b>Savol olish</b> tugmasini bosing!"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu(user.id))

# ─── SAVOL OLISH ──────────────────────────────────────────────────────────────
@dp.message(F.text == "🎯 Savol olish")
async def get_question_start(message: types.Message, state: FSMContext):
    await state.clear()
    categories = db.get_categories()

    if not categories:
        await message.answer("😔 Hozircha savollar yo'q. Admin tez orada qo'shadi!")
        return

    buttons = []
    row = []
    for i, cat in enumerate(categories):
        row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat_{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🌐 Barchasi", callback_data="cat_Barchasi")])

    await message.answer(
        "📂 <b>Kategoriya tanlang:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@dp.callback_query(F.data.startswith("cat_"))
async def category_chosen(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data[4:]
    await state.update_data(category=category)
    try:
        await callback.message.delete()
    except:
        pass
    await send_question(callback.message, callback.from_user.id, state, category)
    await callback.answer()

async def send_question(message, user_id, state, category):
    question = db.get_random_question(user_id, category)

    if not question:
        cats = db.get_categories()
        buttons = []
        row = []
        for cat in cats:
            row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat_{cat}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton(text="🌐 Barchasi", callback_data="cat_Barchasi")])

        await message.answer(
            "🎉 <b>Tabriklaymiz!</b>\nBu kategoriyaning barcha savollariga javob berdingiz!\n\nBoshqa kategoriyani tanlang:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        return

    q_id, q_text, q_type, options, correct, coins, cat, difficulty, explanation, image_id = question
    diff_icon = DIFFICULTY_ICONS.get(difficulty, "🟡")
    diff_name = DIFFICULTY_NAMES.get(difficulty, "O'rta")

    header = (
        f"📂 <b>{cat}</b>  {diff_icon} <b>{diff_name}</b>\n"
        f"💰 To'g'ri: <b>+{coins} coin</b>  ❌ Noto'g'ri: <b>-{round(coins*PENALTY_PERCENT,1)} coin</b>\n"
        f"⏱ Vaqt: <b>{QUESTION_TIME} soniya</b>\n\n"
        f"❓ <b>{q_text}</b>"
    )

    # 🤔 Savol kelganda stiker yuborish
    try:
        sticker_msg = await bot.send_sticker(message.chat.id, sticker=STICKER_QUESTION)
    except:
        sticker_msg = None

    if q_type == "test":
        shuffled_opts, new_correct = shuffle_options(options, correct)
        opts_list = shuffled_opts.split("|")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{chr(65+i)}. {opt}",
                callback_data=f"ans_{q_id}_{chr(65+i)}_{new_correct}"
            )]
            for i, opt in enumerate(opts_list)
        ])

        if image_id:
            try:
                sent = await bot.send_photo(
                    message.chat.id, photo=image_id,
                    caption=header, parse_mode="HTML", reply_markup=keyboard
                )
            except:
                sent = await message.answer(header, parse_mode="HTML", reply_markup=keyboard)
        else:
            sent = await message.answer(header, parse_mode="HTML", reply_markup=keyboard)

        await state.update_data(
            question_id=q_id, msg_id=sent.message_id,
            chat_id=message.chat.id, category=category
        )
        asyncio.create_task(
            question_timeout(user_id, q_id, sent.message_id, message.chat.id, coins, state)
        )
    else:
        await state.set_state(UserStates.answering_open)
        await state.update_data(
            question_id=q_id, correct=correct,
            coins=coins, explanation=explanation, category=category
        )
        text = header + "\n\n✍️ <b>Javobingizni yozing:</b>"
        if image_id:
            try:
                sent = await bot.send_photo(
                    message.chat.id, photo=image_id,
                    caption=text, parse_mode="HTML"
                )
            except:
                sent = await message.answer(text, parse_mode="HTML")
        else:
            sent = await message.answer(text, parse_mode="HTML")

        asyncio.create_task(
            question_timeout(user_id, q_id, sent.message_id, message.chat.id, coins, state)
        )

async def question_timeout(user_id, q_id, msg_id, chat_id, coins, state):
    total = QUESTION_TIME
    # Vaqt tugashidan 10 soniya oldin taymer ko'rsatish
    wait_before_timer = total - 10
    if wait_before_timer > 0:
        await asyncio.sleep(wait_before_timer)

    # Oxirgi 10 soniya: har soniyada yangilanadi
    timer_msg = None
    for remaining in range(10, 0, -1):
        if db.already_answered(user_id, q_id):
            if timer_msg:
                try:
                    await timer_msg.delete()
                except:
                    pass
            return
        bar = timer_bar(remaining, total)
        try:
            if timer_msg is None:
                timer_msg = await bot.send_message(chat_id, bar, parse_mode="HTML")
            else:
                await timer_msg.edit_text(bar, parse_mode="HTML")
        except:
            pass
        await asyncio.sleep(1)

    # Vaqt tugadi
    if db.already_answered(user_id, q_id):
        if timer_msg:
            try: await timer_msg.delete()
            except: pass
        return

    db.save_answer(user_id, q_id, False)
    penalty = round(coins * PENALTY_PERCENT, 1)
    db.add_coins(user_id, -penalty)
    db.update_streak(user_id, False)

    if timer_msg:
        try: await timer_msg.delete()
        except: pass

    try:
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=None)
    except:
        pass

    # ⏰ Vaqt tugadi stikeri
    try:
        await bot.send_sticker(chat_id, sticker=STICKER_TIMEOUT)
    except:
        pass

    data = await state.get_data()
    category = data.get("category", "Barchasi")
    try:
        await bot.send_message(
            chat_id,
            f"⏰ <b>Vaqt tugadi!</b>\n❌ -{penalty} coin jarima",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data=f"next_{category}")]
            ])
        )
    except:
        pass

# ─── TEST JAVOB ───────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("ans_"))
async def handle_test_answer(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    q_id = int(parts[1])
    user_answer = parts[2]
    correct_letter = parts[3]
    user_id = callback.from_user.id

    if db.already_answered(user_id, q_id):
        await callback.answer("⚠️ Allaqachon javob bergansiz!", show_alert=True)
        return

    question = db.get_question_by_id(q_id)
    if not question:
        await callback.answer("Savol topilmadi!", show_alert=True)
        return

    q_id, q_text, q_type, options, correct, coins, cat, difficulty, explanation, image_id = question
    is_correct = user_answer.upper() == correct_letter.upper()
    db.save_answer(user_id, q_id, is_correct)

    data = await state.get_data()
    category = data.get("category", "Barchasi")

    if is_correct:
        new_streak = db.update_streak(user_id, True)
        bonus = streak_bonus(new_streak)
        earned = round(coins * bonus, 1)
        db.add_coins(user_id, earned)
        text = f"✅ <b>To'g'ri!</b> +{earned} coin 🎉"
        if bonus > 1:
            text += f"\n🔥 Streak bonusi x{bonus}!"
        sm = streak_message(new_streak)
        if sm:
            text += f"\n{sm}"
    else:
        db.update_streak(user_id, False)
        penalty = round(coins * PENALTY_PERCENT, 1)
        db.add_coins(user_id, -penalty)
        # To'g'ri javobni ko'rsatish
        opts_list = options.split("|")
        correct_orig_idx = ord(correct.upper()) - 65
        correct_text = opts_list[correct_orig_idx] if correct_orig_idx < len(opts_list) else correct
        text = f"❌ <b>Noto'g'ri!</b> -{penalty} coin\n✅ To'g'ri javob: <b>{correct_text}</b>"

    if explanation:
        text += f"\n\n💡 <i>{explanation}</i>"

    user_data = db.get_user(user_id)
    total_coins = round(user_data[3], 1) if user_data else 0
    streak = user_data[6] if user_data else 0
    text += f"\n\n💰 Coinlar: <b>{total_coins}</b>  🔥 Streak: <b>{streak}</b>"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data=f"next_{category}")]
    ])

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass

    # Stiker yuborish
    try:
        await bot.send_sticker(
            callback.message.chat.id,
            sticker=STICKER_CORRECT if is_correct else STICKER_WRONG
        )
    except:
        pass

    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

# ─── OCHIQ SAVOL ──────────────────────────────────────────────────────────────
@dp.message(UserStates.answering_open)
async def handle_open_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_id = data["question_id"]
    correct = data["correct"]
    coins = data["coins"]
    explanation = data.get("explanation", "")
    category = data.get("category", "Barchasi")
    user_id = message.from_user.id

    if db.already_answered(user_id, q_id):
        await message.answer("⚠️ Bu savolga allaqachon javob bergansiz!")
        await state.clear()
        return

    is_correct = message.text.strip().lower() == correct.strip().lower()
    db.save_answer(user_id, q_id, is_correct)

    if is_correct:
        new_streak = db.update_streak(user_id, True)
        bonus = streak_bonus(new_streak)
        earned = round(coins * bonus, 1)
        db.add_coins(user_id, earned)
        text = f"✅ <b>To'g'ri!</b> +{earned} coin 🎉"
        if bonus > 1:
            text += f"\n🔥 Streak bonusi x{bonus}!"
        sm = streak_message(new_streak)
        if sm:
            text += f"\n{sm}"
    else:
        db.update_streak(user_id, False)
        penalty = round(coins * PENALTY_PERCENT, 1)
        db.add_coins(user_id, -penalty)
        text = f"❌ <b>Noto'g'ri!</b> -{penalty} coin\n✅ To'g'ri javob: <b>{correct}</b>"

    if explanation:
        text += f"\n\n💡 <i>{explanation}</i>"

    user_data = db.get_user(user_id)
    total_coins = round(user_data[3], 1) if user_data else 0
    streak = user_data[6] if user_data else 0
    text += f"\n\n💰 Coinlar: <b>{total_coins}</b>  🔥 Streak: <b>{streak}</b>"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data=f"next_{category}")]
    ])
    # Stiker yuborish
    try:
        await bot.send_sticker(
            message.chat.id,
            sticker=STICKER_CORRECT if is_correct else STICKER_WRONG
        )
    except:
        pass

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await state.clear()

# ─── KEYINGI SAVOL ────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("next_"))
async def next_question(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data[5:]
    await state.update_data(category=category)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    await send_question(callback.message, callback.from_user.id, state, category)
    await callback.answer()

# ─── REYTING ──────────────────────────────────────────────────────────────────
@dp.message(F.text == "🏆 Reyting")
async def show_leaderboard(message: types.Message):
    top = db.get_leaderboard(10)
    if not top:
        await message.answer("😔 Hali hech kim reyting ro'yxatida yo'q!")
        return
    medals = ["🥇", "🥈", "🥉"]
    text = "🏆 <b>Global Reyting — Top 10</b>\n\n"
    for i, (uid, fname, uname, coins) in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = fname or uname or f"User{uid}"
        text += f"{medal} <b>{name}</b> — {round(coins, 1)} coin\n"
    rank = db.get_user_rank(message.from_user.id)
    text += f"\n📍 Sizning o'rningiz: <b>#{rank}</b>"
    await message.answer(text, parse_mode="HTML")

# ─── PROFIL ───────────────────────────────────────────────────────────────────
@dp.message(F.text == "👤 Profilim")
async def show_profile(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Profil topilmadi!")
        return
    uid, username, fname, coins, total_ans, correct_ans, streak, max_streak, join_date = user
    rank = db.get_user_rank(uid)
    accuracy = round((correct_ans / total_ans * 100), 1) if total_ans > 0 else 0
    text = (
        f"👤 <b>Profil — {fname}</b>\n\n"
        f"💰 Coinlar: <b>{round(coins, 1)}</b>\n"
        f"🏆 Reyting: <b>#{rank}</b>\n"
        f"🔥 Hozirgi streak: <b>{streak}</b>\n"
        f"⚡ Eng yuqori streak: <b>{max_streak}</b>\n"
        f"📝 Javob berilgan: <b>{total_ans}</b>\n"
        f"✅ To'g'ri: <b>{correct_ans}</b>\n"
        f"🎯 Aniqlik: <b>{accuracy}%</b>\n"
        f"📅 Qo'shilgan: <b>{join_date[:10]}</b>"
    )
    await message.answer(text, parse_mode="HTML")

# ─── YORDAM ───────────────────────────────────────────────────────────────────
@dp.message(F.text == "ℹ️ Yordam")
async def show_help(message: types.Message):
    text = (
        "ℹ️ <b>BilimChallenge — Yordam</b>\n\n"
        "🎯 <b>Savol olish</b> — kategoriya tanlab savol oling\n"
        "🏆 <b>Reyting</b> — top 10 o'yinchilar\n"
        "👤 <b>Profilim</b> — sizning statistikangiz\n\n"
        "<b>Coin tizimi:</b>\n"
        "✅ To'g'ri javob — coin olasiz\n"
        "❌ Noto'g'ri javob — 30% jarima\n"
        "⏰ Vaqt tugasa — 30% jarima\n\n"
        "<b>Streak bonuslari:</b>\n"
        "🔥 3 ta ketma-ket — x1.5\n"
        "🔥🔥 5 ta ketma-ket — x2.0\n"
        "🔥🔥🔥 10 ta ketma-ket — x3.0\n\n"
        "🟢 Oson  🟡 O'rta  🔴 Qiyin"
    )
    await message.answer(text, parse_mode="HTML")

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

# ─── KATEGORIYALAR ────────────────────────────────────────────────────────────
@dp.message(F.text == "📂 Kategoriyalar")
async def manage_categories(message: types.Message):
    if not is_admin(message.from_user.id): return
    cats = db.get_categories()
    text = "📂 <b>Kategoriyalar</b>\n\n"
    if cats:
        text += "\n".join([f"• {c}" for c in cats])
    else:
        text += "Hali kategoriya yo'q"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi kategoriya", callback_data="add_category")],
        [InlineKeyboardButton(text="🗑 Kategoriya o'chirish", callback_data="del_category_list")],
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data == "add_category")
async def add_category_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_new_category)
    await callback.message.answer("📂 Yangi kategoriya nomini kiriting:")
    await callback.answer()

@dp.message(AdminStates.waiting_new_category)
async def save_new_category(message: types.Message, state: FSMContext):
    db.add_category(message.text.strip())
    await state.clear()
    await message.answer(f"✅ <b>{message.text.strip()}</b> kategoriyasi qo'shildi!", parse_mode="HTML", reply_markup=admin_menu())

@dp.callback_query(F.data == "del_category_list")
async def del_category_list(callback: types.CallbackQuery):
    cats = db.get_categories()
    if not cats:
        await callback.answer("Kategoriya yo'q!", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(text=f"🗑 {c}", callback_data=f"delcat_{c}")] for c in cats]
    await callback.message.answer("Qaysi kategoriyani o'chirish?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("delcat_"))
async def delete_category(callback: types.CallbackQuery):
    cat = callback.data[7:]
    db.delete_category(cat)
    await callback.message.edit_text(f"✅ <b>{cat}</b> o'chirildi!", parse_mode="HTML")
    await callback.answer()

# ─── SAVOL QO'SHISH ───────────────────────────────────────────────────────────
@dp.message(F.text == "➕ Savol qo'shish")
async def add_question_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    await state.set_state(AdminStates.waiting_question_type)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Test (A,B,C,D)", callback_data="qtype_test")],
        [InlineKeyboardButton(text="✍️ Ochiq savol", callback_data="qtype_open")],
    ])
    await message.answer("📌 Savol turini tanlang:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("qtype_"))
async def choose_question_type(callback: types.CallbackQuery, state: FSMContext):
    qtype = callback.data.split("_")[1]
    await state.update_data(q_type=qtype)
    await state.set_state(AdminStates.waiting_question_text)
    await callback.message.edit_text("✏️ Savol matnini kiriting:")
    await callback.answer()

@dp.message(AdminStates.waiting_question_text)
async def get_question_text(message: types.Message, state: FSMContext):
    await state.update_data(q_text=message.text)
    data = await state.get_data()
    if data["q_type"] == "test":
        await state.set_state(AdminStates.waiting_options)
        await message.answer(
            "📋 Variantlarni kiriting (har biri yangi qatorda):\n\n"
            "Misol:\nOsiyo\nAfrika\nAmerika\nYevropa"
        )
    else:
        await state.set_state(AdminStates.waiting_correct_answer)
        await message.answer("✅ To'g'ri javobni kiriting:")

@dp.message(AdminStates.waiting_options)
async def get_options(message: types.Message, state: FSMContext):
    options = [o.strip() for o in message.text.split("\n") if o.strip()]
    if len(options) < 2:
        await message.answer("⚠️ Kamida 2 ta variant kiriting!")
        return
    await state.update_data(options="|".join(options))
    await state.set_state(AdminStates.waiting_correct_answer)
    opts_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)])
    await message.answer(f"📋 Variantlar:\n{opts_text}\n\n✅ To'g'ri variant harfini kiriting (A, B, C yoki D):")

@dp.message(AdminStates.waiting_correct_answer)
async def get_correct_answer(message: types.Message, state: FSMContext):
    await state.update_data(correct=message.text.strip())
    await state.set_state(AdminStates.waiting_coin_reward)
    await message.answer("💰 Bu savol uchun necha coin? (raqam):")

@dp.message(AdminStates.waiting_coin_reward)
async def get_coin_reward(message: types.Message, state: FSMContext):
    if not message.text.replace(".", "").isdigit():
        await message.answer("⚠️ Faqat raqam kiriting!")
        return
    await state.update_data(coins=float(message.text))
    await state.set_state(AdminStates.waiting_difficulty)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Oson", callback_data="diff_oson")],
        [InlineKeyboardButton(text="🟡 O'rta", callback_data="diff_orta")],
        [InlineKeyboardButton(text="🔴 Qiyin", callback_data="diff_qiyin")],
    ])
    await message.answer("📊 Qiyinlik darajasi:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("diff_"))
async def get_difficulty(callback: types.CallbackQuery, state: FSMContext):
    difficulty = callback.data.split("_")[1]
    await state.update_data(difficulty=difficulty)
    await state.set_state(AdminStates.waiting_category)

    # Mavjud kategoriyalar + yangi yaratish
    cats = db.get_categories()
    buttons = []
    row = []
    for cat in cats:
        row.append(InlineKeyboardButton(text=cat, callback_data=f"selcat_{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="➕ Yangi kategoriya", callback_data="selcat_NEW")])

    await callback.message.edit_text(
        "📂 Kategoriyani tanlang yoki yangi yarating:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("selcat_"))
async def select_category(callback: types.CallbackQuery, state: FSMContext):
    cat = callback.data[7:]
    if cat == "NEW":
        await callback.message.edit_text("📂 Yangi kategoriya nomini kiriting:")
        await callback.answer()
        return
    await state.update_data(category=cat)
    await state.set_state(AdminStates.waiting_explanation)
    await callback.message.edit_text(
        "💡 Tavsif kiriting (nega bu javob to'g'ri?):\n\n<i>Kerak bo'lmasa '-' yozing</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(AdminStates.waiting_category)
async def get_new_category_inline(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text.strip())
    db.add_category(message.text.strip())
    await state.set_state(AdminStates.waiting_explanation)
    await message.answer(
        "💡 Tavsif kiriting (nega bu javob to'g'ri?):\n\n<i>Kerak bo'lmasa '-' yozing</i>",
        parse_mode="HTML"
    )

@dp.message(AdminStates.waiting_explanation)
async def get_explanation(message: types.Message, state: FSMContext):
    explanation = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(explanation=explanation)
    await state.set_state(AdminStates.waiting_image)
    await message.answer(
        "🖼 Rasm qo'shish (ixtiyoriy):\n\n"
        "• Rasm yuklang (telefon/kompyuterdan)\n"
        "• Yoki rasm URL manzilini yuboring\n"
        "• Kerak bo'lmasa <b>'-'</b> yozing",
        parse_mode="HTML"
    )

@dp.message(AdminStates.waiting_image)
async def get_image(message: types.Message, state: FSMContext):
    image_id = ""

    if message.text and message.text.strip() == "-":
        image_id = ""
    elif message.photo:
        image_id = message.photo[-1].file_id
    elif message.text and (message.text.startswith("http://") or message.text.startswith("https://")):
        image_id = message.text.strip()
    
    await state.update_data(image_id=image_id)
    data = await state.get_data()

    diff_icon = DIFFICULTY_ICONS.get(data.get("difficulty", "orta"), "🟡")
    options_display = ""
    if data["q_type"] == "test":
        opts = data.get("options", "").split("|")
        options_display = "\n" + "\n".join([f"  {chr(65+i)}. {opt}" for i, opt in enumerate(opts)])
        options_display += f"\n✅ To'g'ri: {data['correct'].upper()}"
    else:
        options_display = f"\n✅ Javob: {data['correct']}"

    confirm_text = (
        f"📋 <b>Tekshiring:</b>\n\n"
        f"📝 Tur: {'Test' if data['q_type'] == 'test' else 'Ochiq'}\n"
        f"❓ Savol: {data['q_text']}"
        f"{options_display}\n"
        f"💰 Coin: {data['coins']}\n"
        f"{diff_icon} Qiyinlik: {DIFFICULTY_NAMES.get(data.get('difficulty','orta'))}\n"
        f"📂 Kategoriya: {data['category']}\n"
        f" Tavsif: {data.get('explanation') or 'Yoq'}\n"
        f" Rasm: {'Ha' if image_id else 'Yoq'}\n\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Saqlash", callback_data="save_question"),
            InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_question"),
        ],
        [
            InlineKeyboardButton(text="✏️ Savol matnini o'zgart.", callback_data="edit_q_text"),
            InlineKeyboardButton(text="💰 Coinni o'zgartir", callback_data="edit_q_coins"),
        ],
    ])
    await message.answer(confirm_text, parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("edit_q_"))
async def edit_before_save(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data[7:]
    field_names = {
        "text": "Yangi savol matnini kiriting:",
        "coins": "Yangi coin miqdorini kiriting:",
    }
    await state.update_data(editing_field=field)
    await state.set_state(AdminStates.editing_value)
    await callback.message.answer(field_names.get(field, "Yangi qiymatni kiriting:"))
    await callback.answer()

@dp.message(AdminStates.editing_value)
async def save_edited_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    field = data.get("editing_field", "")
    if field == "text":
        await state.update_data(q_text=message.text)
    elif field == "coins":
        if not message.text.replace(".", "").isdigit():
            await message.answer("⚠️ Faqat raqam!")
            return
        await state.update_data(coins=float(message.text))
    await state.set_state(AdminStates.waiting_image)
    await message.answer(f"✅ O'zgartirildi! Endi davom etamiz.\n\n🖼 Rasm (kerak bo'lmasa '-' yozing):")

@dp.callback_query(F.data == "save_question")
async def save_question_cb(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    db.add_question(
        text=data["q_text"],
        q_type=data["q_type"],
        options=data.get("options", ""),
        correct=data["correct"],
        coins=data["coins"],
        category=data["category"],
        difficulty=data.get("difficulty", "orta"),
        explanation=data.get("explanation", ""),
        image_id=data.get("image_id", "")
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

# ─── SAVOL TAHRIRLASH ─────────────────────────────────────────────────────────
@dp.message(F.text == "✏️ Savol tahrirlash")
async def edit_question_prompt(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("✏️ Tahrirlanadigan savol ID sini yuboring:")

# ─── SAVOLLAR RO'YXATI ────────────────────────────────────────────────────────
@dp.message(F.text == "📋 Savollar ro'yxati")
async def list_questions(message: types.Message):
    if not is_admin(message.from_user.id): return
    questions = db.get_all_questions()
    if not questions:
        await message.answer("😔 Savollar yo'q.")
        return
    text = f"📋 <b>Jami: {len(questions)} ta savol</b>\n\n"
    for q in questions[:20]:
        q_id, q_text, q_type, _, _, coins, category, difficulty = q
        short = q_text[:35] + "..." if len(q_text) > 35 else q_text
        diff_icon = DIFFICULTY_ICONS.get(difficulty, "🟡")
        type_icon = "📝" if q_type == "test" else "✍️"
        text += f"#{q_id} {type_icon}{diff_icon} [{category}] {short} ({coins}💰)\n"
    if len(questions) > 20:
        text += f"\n...va yana {len(questions)-20} ta"
    await message.answer(text, parse_mode="HTML")

# ─── SAVOL O'CHIRISH ──────────────────────────────────────────────────────────
@dp.message(F.text == "🗑 Savol o'chirish")
async def delete_question_prompt(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("🗑 O'chiriladigan savol ID sini yuboring:")

# ─── ID bilan ishlash (o'chirish / tahrirlash) ────────────────────────────────
@dp.message(F.text.regexp(r'^\d+$'))
async def handle_id_input(message: types.Message):
    if not is_admin(message.from_user.id): return
    q_id = int(message.text)
    question = db.get_question_by_id(q_id)
    if not question:
        await message.answer(f"❌ #{q_id} ID li savol topilmadi.")
        return

    q_id, q_text, q_type, options, correct, coins, cat, diff, explanation, image_id = question
    diff_icon = DIFFICULTY_ICONS.get(diff, "🟡")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del_{q_id}"),
            InlineKeyboardButton(text="❌ Bekor", callback_data="del_cancel"),
        ],
        [InlineKeyboardButton(text="✏️ Savol matnini o'zgartir", callback_data=f"edf_{q_id}_text")],
        [InlineKeyboardButton(text="💰 Coinni o'zgartir", callback_data=f"edf_{q_id}_coins")],
        [InlineKeyboardButton(text="💡 Tavsifni o'zgartir", callback_data=f"edf_{q_id}_explanation")],
        [InlineKeyboardButton(text="🖼 Rasmni o'zgartir", callback_data=f"edf_{q_id}_image_id")],
    ])

    short = q_text[:80] + "..." if len(q_text) > 80 else q_text
    await message.answer(
        f"#{q_id} {diff_icon} [{cat}]\n❓ {short}\n💰 {coins} coin",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("edf_"))
async def edit_existing_field(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    q_id = int(parts[1])
    field = parts[2]
    await state.update_data(edit_q_id=q_id, edit_field=field)
    await state.set_state(AdminStates.editing_field)

    prompts = {
        "text": "Yangi savol matnini kiriting:",
        "coins": "Yangi coin miqdorini kiriting:",
        "explanation": "Yangi tavsifni kiriting:",
        "image_id": "Rasm yuboring yoki URL kiriting ('-' = o'chirish):",
    }
    await callback.message.answer(prompts.get(field, "Yangi qiymat:"))
    await callback.answer()

@dp.message(AdminStates.editing_field)
async def save_existing_edit(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_id = data["edit_q_id"]
    field = data["edit_field"]

    if field == "image_id":
        if message.photo:
            value = message.photo[-1].file_id
        elif message.text and message.text.strip() == "-":
            value = ""
        else:
            value = message.text.strip()
    elif field == "coins":
        if not message.text.replace(".", "").isdigit():
            await message.answer("⚠️ Faqat raqam!")
            return
        value = float(message.text)
    else:
        value = message.text.strip()

    db.update_question_field(q_id, field, value)
    await state.clear()
    await message.answer(f"✅ #{q_id} savol yangilandi!", reply_markup=admin_menu())

@dp.callback_query(F.data.startswith("del_"))
async def confirm_delete(callback: types.CallbackQuery):
    if callback.data == "del_cancel":
        await callback.message.edit_text("❌ Bekor qilindi.")
        await callback.answer()
        return
    q_id = int(callback.data.split("_")[1])
    db.delete_question(q_id)
    await callback.message.edit_text(f"✅ #{q_id} savol o'chirildi!")
    await callback.answer()

# ─── FOYDALANUVCHILAR & STATISTIKA ───────────────────────────────────────────
@dp.message(F.text == "👥 Foydalanuvchilar")
async def list_users(message: types.Message):
    if not is_admin(message.from_user.id): return
    total = db.get_total_users()
    active = db.get_active_users()
    await message.answer(
        f"👥 <b>Foydalanuvchilar</b>\n\n📊 Jami: <b>{total}</b>\n🟢 Faol: <b>{active}</b>",
        parse_mode="HTML"
    )

@dp.message(F.text == "📊 Statistika")
async def show_stats(message: types.Message):
    if not is_admin(message.from_user.id): return
    stats = db.get_stats()
    await message.answer(
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{stats['users']}</b>\n"
        f"❓ Savollar: <b>{stats['questions']}</b>\n"
        f"📝 Javoblar: <b>{stats['answers']}</b>\n"
        f"✅ To'g'ri: <b>{stats['correct']}</b>\n"
        f"🎯 Aniqlik: <b>{stats['accuracy']}%</b>",
        parse_mode="HTML"
    )

# ─── RUN ──────────────────────────────────────────────────────────────────────
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
