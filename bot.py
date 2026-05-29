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

STICKER_QUESTION = "CAACAgIAAxkBAAFKw2JqFrdsWk9htpRwDxq9eAwYUa1ZXQACA1oAAnkIAUpLU6bVp7_sLDsE"
STICKER_CORRECT  = "CAACAgIAAxkBAAFKw5VqFrluy9UnO2MewXZNLbJwB7J_ygACejIAAiaOCEnMbgcQ72sJ_DsE"
STICKER_WRONG    = "CAACAgIAAxkBAAFKw5NqFrle6l0Hv4ROqH0ISrfk5cK5bQAC7C8AAoa6-EjuktV0xKYEMTsE"
STICKER_TIMEOUT  = "CAACAgIAAxkBAAFKw2ZqFrdzK3_NmWUcbh60u3WKoYfVygACb2AAAo386UkHCMIb6broyTsE"

TIMEOUT_PENALTY = 0.45

def timer_bar(seconds_left: int, total: int) -> str:
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
    waiting_new_category = State()
    editing_field = State()
    editing_value = State()
    waiting_feedback_reply = State()
    edit_choosing_field = State()
    edit_field_value = State()
    waiting_broadcast = State()

class UserStates(StatesGroup):
    answering_open = State()
    sending_feedback = State()
    answering_premium = State()

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def is_admin(user_id): return user_id in ADMIN_IDS

def main_menu(user_id):
    buttons = [
        [KeyboardButton(text="🎯 Savol olish"), KeyboardButton(text="🏆 Reyting")],
        [KeyboardButton(text="👤 Profilim"), KeyboardButton(text="ℹ️ Yordam")],
        [KeyboardButton(text="📝 Taklif/Shikoyat")],
    ]
    if is_admin(user_id):
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def admin_menu():
    buttons = [
        [KeyboardButton(text="➕ Savol qo'shish"), KeyboardButton(text="📋 Savollar ro'yxati")],
        [KeyboardButton(text="✏️ Savol tahrirlash"), KeyboardButton(text="🗑 Savol o'chirish")],
        [KeyboardButton(text="📂 Kategoriyalar"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="👥 Foydalanuvchilar"), KeyboardButton(text="💬 Takliflar")],
        [KeyboardButton(text="📢 Xabar yuborish")],
        [KeyboardButton(text="🔙 Asosiy menyu")],
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

@dp.message(Command("cancel"))
async def cancel_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=main_menu(message.from_user.id))

# ─── TAKLIF / SHIKOYAT ────────────────────────────────────────────────────────
@dp.message(F.text == "📝 Taklif/Shikoyat")
async def feedback_start(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.sending_feedback)
    await message.answer(
        "📝 <b>Taklif yoki shikoyatingizni yozing:</b>\n\n"
        "<i>Xabaringiz adminlarga yuboriladi. Bekor qilish uchun /cancel</i>",
        parse_mode="HTML"
    )

@dp.message(UserStates.sending_feedback)
async def receive_feedback(message: types.Message, state: FSMContext):
    user = message.from_user
    db.save_feedback(user.id, user.first_name or "", user.username or "", message.text)
    await state.clear()
    await message.answer(
        "✅ <b>Xabaringiz adminga yuborildi!</b>\nRahmat!",
        parse_mode="HTML",
        reply_markup=main_menu(user.id)
    )

# ─── SAVOL OLISH ──────────────────────────────────────────────────────────────
@dp.message(F.text == "🎯 Savol olish")
async def get_question_start(message: types.Message, state: FSMContext):
    await state.clear()
    categories = db.get_categories()
    if not categories:
        await message.answer("Hozircha savollar yo'q. Admin tez orada qo'shadi!")
        return

    buttons = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat_{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🌐 Aralash (barcha kategoriya)", callback_data="cat_Barchasi")])

    await message.answer(
        "📂 <b>Kategoriya tanlang:</b>\n\n"
        "<i>🌐 Aralash — barcha kategoriyalardan tasodifiy savollar</i>",
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
        buttons.append([InlineKeyboardButton(text="🌐 Aralash", callback_data="cat_Barchasi")])
        await message.answer(
            "🎉 <b>Tabriklaymiz!</b>\nBu kategoriyaning barcha savollariga javob berdingiz!\n\nBoshqa kategoriyani tanlang:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        return

    q_id, q_text, q_type, options, correct, coins, cat, difficulty, explanation, image_id = question
    diff_icon = DIFFICULTY_ICONS.get(difficulty, "🟡")
    diff_name = DIFFICULTY_NAMES.get(difficulty, "O'rta")

    if q_type == "premium":
        await send_premium_question(message, user_id, state, category, question)
        return

    header = (
        f"📂 <b>{cat}</b>  {diff_icon} <b>{diff_name}</b>\n"
        f"💰 To'g'ri: <b>+{coins} coin</b>  ❌ Noto'g'ri: <b>-{round(coins*PENALTY_PERCENT,1)} coin</b>\n"
        f"⏱ Vaqt: <b>{QUESTION_TIME} soniya</b>\n\n"
        f"❓ <b>{q_text}</b>"
    )

    try:
        await bot.send_sticker(message.chat.id, sticker=STICKER_QUESTION)
    except:
        pass

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
                sent = await bot.send_photo(message.chat.id, photo=image_id, caption=header, parse_mode="HTML", reply_markup=keyboard)
            except:
                sent = await message.answer(header, parse_mode="HTML", reply_markup=keyboard)
        else:
            sent = await message.answer(header, parse_mode="HTML", reply_markup=keyboard)
        await state.update_data(question_id=q_id, msg_id=sent.message_id, chat_id=message.chat.id, category=category)
        asyncio.create_task(question_timeout(user_id, q_id, sent.message_id, message.chat.id, coins, state))
    else:
        await state.set_state(UserStates.answering_open)
        await state.update_data(question_id=q_id, correct=correct, coins=coins, explanation=explanation, category=category)
        text = header + "\n\n✍️ <b>Javobingizni yozing:</b>"
        if image_id:
            try:
                sent = await bot.send_photo(message.chat.id, photo=image_id, caption=text, parse_mode="HTML")
            except:
                sent = await message.answer(text, parse_mode="HTML")
        else:
            sent = await message.answer(text, parse_mode="HTML")
        asyncio.create_task(question_timeout(user_id, q_id, sent.message_id, message.chat.id, coins, state))

# ─── PREMIUM SAVOL ────────────────────────────────────────────────────────────
async def send_premium_question(message, user_id, state, category, question):
    q_id, q_text, q_type, options, correct, coins, cat, difficulty, explanation, image_id = question
    diff_icon = DIFFICULTY_ICONS.get(difficulty, "🟡")
    diff_name = DIFFICULTY_NAMES.get(difficulty, "O'rta")

    header = (
        f"⭐ <b>PREMIUM SAVOL</b>\n"
        f"📂 <b>{cat}</b>  {diff_icon} <b>{diff_name}</b>\n"
        f"💰 To'g'ri: <b>+{coins} coin</b>  ✅ Jarima yo'q\n"
        f"🔄 Urinishlar: <b>3 ta</b>  ⏱ Vaqt: <b>Cheksiz</b>\n\n"
        f"❓ <b>{q_text}</b>"
    )

    try:
        await bot.send_sticker(message.chat.id, sticker=STICKER_QUESTION)
    except:
        pass

    skip_btn = InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data=f"premskip_{q_id}_{category}")

    if options:
        shuffled_opts, new_correct = shuffle_options(options, correct)
        opts_list = shuffled_opts.split("|")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{chr(65+i)}. {opt}",
                callback_data=f"prem_{q_id}_{chr(65+i)}_{new_correct}_1"
            )]
            for i, opt in enumerate(opts_list)
        ] + [[skip_btn]])

        if image_id:
            try:
                await bot.send_photo(message.chat.id, photo=image_id, caption=header, parse_mode="HTML", reply_markup=keyboard)
            except:
                await message.answer(header, parse_mode="HTML", reply_markup=keyboard)
        else:
            await message.answer(header, parse_mode="HTML", reply_markup=keyboard)
    else:
        await state.set_state(UserStates.answering_premium)
        await state.update_data(
            question_id=q_id, correct=correct, coins=coins,
            explanation=explanation, category=category, premium_attempts=1
        )
        text = header + "\n\n✍️ <b>Javobingizni yozing:</b>\n<i>3 ta urinish mavjud</i>"
        await message.answer(text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[skip_btn]])
        )
    await state.update_data(question_id=q_id, category=category)

@dp.callback_query(F.data.startswith("premskip_"))
async def premium_skip(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    category = parts[2]
    await state.clear()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass
    await callback.message.answer(
        "⏭ <b>O'tkazildi!</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data=f"next_{category}")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("prem_"))
async def handle_premium_answer(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    q_id = int(parts[1])
    user_answer = parts[2]
    correct_letter = parts[3]
    attempt = int(parts[4])
    user_id = callback.from_user.id

    question = db.get_question_by_id(q_id)
    if not question:
        await callback.answer("Savol topilmadi!", show_alert=True)
        return

    q_id2, q_text, q_type, options, correct, coins, cat, difficulty, explanation, image_id = question
    is_correct = user_answer.upper() == correct_letter.upper()
    data = await state.get_data()
    category = data.get("category", "Barchasi")

    if is_correct:
        db.save_answer(user_id, q_id, True)
        new_streak = db.update_streak(user_id, True)
        bonus = streak_bonus(new_streak)
        earned = round(coins * bonus, 1)
        db.add_coins(user_id, earned)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except:
            pass
        try:
            await bot.send_sticker(callback.message.chat.id, sticker=STICKER_CORRECT)
        except:
            pass
        text = f"✅ <b>To'g'ri!</b> +{earned} coin 🎉\n⭐ Premium savol — jarima yo'q edi!"
        if bonus > 1:
            text += f"\n🔥 Streak bonusi x{bonus}!"
        sm = streak_message(new_streak)
        if sm:
            text += f"\n{sm}"
        if explanation:
            text += f"\n\n💡 <i>{explanation}</i>"
        user_data = db.get_user(user_id)
        total_coins = round(user_data[3], 1) if user_data else 0
        text += f"\n\n💰 Coinlar: <b>{total_coins}</b>"
        await callback.message.answer(text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data=f"next_{category}")]
            ])
        )
    else:
        try:
            await bot.send_sticker(callback.message.chat.id, sticker=STICKER_WRONG)
        except:
            pass
        if attempt < 3:
            shuffled_opts, new_correct = shuffle_options(options, correct)
            opts_list = shuffled_opts.split("|")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{chr(65+i)}. {opt}",
                    callback_data=f"prem_{q_id}_{chr(65+i)}_{new_correct}_{attempt+1}"
                )]
                for i, opt in enumerate(opts_list)
            ] + [[InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data=f"premskip_{q_id}_{category}")]])
            await callback.message.answer(
                f"❌ <b>Noto'g'ri!</b> Yana urinib ko'ring!\n"
                f"🔄 Qolgan urinishlar: <b>{3 - attempt}</b>\n"
                f"⭐ Jarima yo'q!",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            db.save_answer(user_id, q_id, False)
            db.update_streak(user_id, False)
            opts_list = options.split("|")
            correct_orig_idx = ord(correct.upper()) - 65
            correct_text = opts_list[correct_orig_idx] if correct_orig_idx < len(opts_list) else correct
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except:
                pass
            text = (
                f"❌ <b>3 ta urinish tugadi!</b>\n"
                f"✅ To'g'ri javob: <b>{correct_text}</b>\n"
                f"⭐ Premium savol — coin minuslenmadi!"
            )
            if explanation:
                text += f"\n\n💡 <i>{explanation}</i>"
            await callback.message.answer(text, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data=f"next_{category}")]
                ])
            )
    await callback.answer()

@dp.message(UserStates.answering_premium)
async def handle_premium_open_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_id = data["question_id"]
    correct = data["correct"]
    coins = data["coins"]
    explanation = data.get("explanation", "")
    category = data.get("category", "Barchasi")
    attempt = data.get("premium_attempts", 1)
    user_id = message.from_user.id

    is_correct = message.text.strip().lower() == correct.strip().lower()

    if is_correct:
        db.save_answer(user_id, q_id, True)
        new_streak = db.update_streak(user_id, True)
        bonus = streak_bonus(new_streak)
        earned = round(coins * bonus, 1)
        db.add_coins(user_id, earned)
        try:
            await bot.send_sticker(message.chat.id, sticker=STICKER_CORRECT)
        except:
            pass
        text = f"✅ <b>To'g'ri!</b> +{earned} coin 🎉\n⭐ Premium savol — jarima yo'q edi!"
        if bonus > 1:
            text += f"\n🔥 Streak bonusi x{bonus}!"
        sm = streak_message(new_streak)
        if sm:
            text += f"\n{sm}"
        if explanation:
            text += f"\n\n💡 <i>{explanation}</i>"
        await message.answer(text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data=f"next_{category}")]
            ])
        )
        await state.clear()
    else:
        try:
            await bot.send_sticker(message.chat.id, sticker=STICKER_WRONG)
        except:
            pass
        if attempt < 3:
            await state.update_data(premium_attempts=attempt + 1)
            await message.answer(
                f"❌ <b>Noto'g'ri!</b> Yana urinib ko'ring!\n"
                f"🔄 Qolgan urinishlar: <b>{3 - attempt}</b>\n"
                f"⭐ Jarima yo'q!",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data=f"premskip_{q_id}_{category}")]
                ])
            )
        else:
            db.save_answer(user_id, q_id, False)
            db.update_streak(user_id, False)
            text = (
                f"❌ <b>3 ta urinish tugadi!</b>\n"
                f"✅ To'g'ri javob: <b>{correct}</b>\n"
                f"⭐ Premium savol — coin minuslenmadi!"
            )
            if explanation:
                text += f"\n\n💡 <i>{explanation}</i>"
            await message.answer(text, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➡️ Keyingi savol", callback_data=f"next_{category}")]
                ])
            )
            await state.clear()

# ─── TIMEOUT ──────────────────────────────────────────────────────────────────
async def question_timeout(user_id, q_id, msg_id, chat_id, coins, state):
    total = QUESTION_TIME
    wait_before_timer = total - 10
    if wait_before_timer > 0:
        await asyncio.sleep(wait_before_timer)

    timer_msg = None
    for remaining in range(10, 0, -1):
        if db.already_answered(user_id, q_id):
            if timer_msg:
                try: await timer_msg.delete()
                except: pass
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
    try:
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=None)
    except:
        pass
    try:
        await bot.send_sticker(chat_id, sticker=STICKER_TIMEOUT)
    except:
        pass
    data = await state.get_data()
    category = data.get("category", "Barchasi")
    try:
        await bot.send_message(
            chat_id,
            f"⏰ <b>Vaqt tugadi!</b>\n❌ -{penalty} coin jarima (45%)",
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
        await callback.answer("Allaqachon javob bergansiz!", show_alert=True)
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
        if sm: text += f"\n{sm}"
    else:
        db.update_streak(user_id, False)
        penalty = round(coins * PENALTY_PERCENT, 1)
        db.add_coins(user_id, -penalty)
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
    try:
        await bot.send_sticker(callback.message.chat.id, sticker=STICKER_CORRECT if is_correct else STICKER_WRONG)
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
        await message.answer("Bu savolga allaqachon javob bergansiz!")
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
        if sm: text += f"\n{sm}"
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
    try:
        await bot.send_sticker(message.chat.id, sticker=STICKER_CORRECT if is_correct else STICKER_WRONG)
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
        await message.answer("Hali hech kim reyting ro'yxatida yo'q!")
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
        "👤 <b>Profilim</b> — sizning statistikangiz\n"
        "📝 <b>Taklif/Shikoyat</b> — adminga xabar yuboring\n\n"
        "<b>Coin tizimi:</b>\n"
        "✅ To'g'ri javob — coin olasiz\n"
        "❌ Noto'g'ri javob — 30% jarima\n"
        "⏰ Vaqt tugasa — 45% jarima\n\n"
        "<b>Streak bonuslari:</b>\n"
        "🔥 3 ta ketma-ket — x1.5\n"
        "🔥🔥 5 ta ketma-ket — x2.0\n"
        "🔥🔥🔥 10 ta ketma-ket — x3.0\n\n"
        "⭐ <b>Premium savollar:</b>\n"
        "3 ta urinish, vaqt yo'q, jarima yo'q!\n\n"
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

# ─── BROADCAST ────────────────────────────────────────────────────────────────
@dp.message(F.text == "📢 Xabar yuborish")
async def broadcast_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdminStates.waiting_broadcast)
    await message.answer(
        "📢 <b>Barcha foydalanuvchilarga xabar yuboring</b>\n\n"
        "Xabar matnini yozing:\n\n"
        "<i>Bekor qilish: /cancel</i>",
        parse_mode="HTML"
    )

@dp.message(AdminStates.waiting_broadcast)
async def broadcast_send(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()

    cur = db.get_conn().cursor()
    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()

    total = len(users)
    success = 0
    failed = 0

    status_msg = await message.answer(f"📤 Yuborilmoqda... 0/{total}")
    broadcast_text = f"📢 <b>BilimChallenge xabari:</b>\n\n{message.text}"

    for i, (user_id,) in enumerate(users):
        try:
            await bot.send_message(user_id, broadcast_text, parse_mode="HTML")
            success += 1
        except:
            failed += 1
        if (i + 1) % 20 == 0:
            try:
                await status_msg.edit_text(f"📤 Yuborilmoqda... {i+1}/{total}")
            except:
                pass

    await status_msg.edit_text(
        f"✅ <b>Xabar yuborildi!</b>\n\n"
        f"👥 Jami: {total}\n"
        f"✅ Muvaffaqiyatli: {success}\n"
        f"❌ Blok/yo'q: {failed}",
        parse_mode="HTML"
    )

# ─── SAVOL QO'SHISH ───────────────────────────────────────────────────────────
@dp.message(F.text == "➕ Savol qo'shish")
async def add_question_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdminStates.waiting_question_type)
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 Test (variantli)"), KeyboardButton(text="✍️ Ochiq (yozma)")],
        [KeyboardButton(text="⭐ Premium (3 urinish, jarimasi yo'q)")],
        [KeyboardButton(text="🔙 Asosiy menyu")]
    ], resize_keyboard=True)
    await message.answer(
        "➕ <b>Savol turi:</b>\n\n"
        "📝 <b>Test</b> — 4 ta variant, bitta to'g'ri\n"
        "✍️ <b>Ochiq</b> — foydalanuvchi matn yozadi\n"
        "⭐ <b>Premium</b> — 3 urinish, vaqt yo'q, jarima yo'q",
        parse_mode="HTML",
        reply_markup=keyboard
    )

@dp.message(AdminStates.waiting_question_type)
async def process_question_type(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    text = message.text
    if text == "📝 Test (variantli)":
        q_type = "test"
    elif text == "✍️ Ochiq (yozma)":
        q_type = "open"
    elif text == "⭐ Premium (3 urinish, jarimasi yo'q)":
        q_type = "premium"
    else:
        await message.answer("Iltimos, tugmalardan birini tanlang!")
        return
    await state.update_data(q_type=q_type)
    await state.set_state(AdminStates.waiting_question_text)
    await message.answer(
        "📝 <b>Savol matnini yozing:</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Asosiy menyu")]], resize_keyboard=True)
    )

@dp.message(AdminStates.waiting_question_text)
async def process_question_text(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.update_data(q_text=message.text)
    data = await state.get_data()
    q_type = data.get("q_type")
    if q_type in ("test", "premium"):
        await state.set_state(AdminStates.waiting_options)
        await message.answer(
            "📋 <b>Variantlarni yozing</b> (| bilan ajrating):\n\nMisol: <code>Paris|London|Berlin|Madrid</code>",
            parse_mode="HTML"
        )
    else:
        await state.set_state(AdminStates.waiting_correct_answer)
        await message.answer("✅ <b>To'g'ri javobni yozing:</b>", parse_mode="HTML")

@dp.message(AdminStates.waiting_options)
async def process_options(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    options = message.text.strip()
    opts_list = options.split("|")
    if len(opts_list) < 2:
        await message.answer("Kamida 2 ta variant kerak! | bilan ajrating.")
        return
    await state.update_data(options=options)
    await state.set_state(AdminStates.waiting_correct_answer)
    opts_display = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(opts_list)])
    await message.answer(
        f"✅ <b>To'g'ri javob harfini yozing:</b>\n\n{opts_display}\n\nMisol: <code>A</code>",
        parse_mode="HTML"
    )

@dp.message(AdminStates.waiting_correct_answer)
async def process_correct_answer(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.update_data(correct=message.text.strip())
    await state.set_state(AdminStates.waiting_coin_reward)
    await message.answer("💰 <b>Necha coin berilsin?</b> (Misol: 5)", parse_mode="HTML")

@dp.message(AdminStates.waiting_coin_reward)
async def process_coins(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try:
        coins = float(message.text.strip())
    except:
        await message.answer("Son kiriting! Masalan: 5")
        return
    await state.update_data(coins=coins)
    await state.set_state(AdminStates.waiting_difficulty)
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🟢 Oson"), KeyboardButton(text="🟡 O'rta"), KeyboardButton(text="🔴 Qiyin")]
    ], resize_keyboard=True)
    await message.answer("📊 <b>Qiyinlik darajasi:</b>", parse_mode="HTML", reply_markup=keyboard)

@dp.message(AdminStates.waiting_difficulty)
async def process_difficulty(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    diff_map = {"🟢 Oson": "oson", "🟡 O'rta": "orta", "🔴 Qiyin": "qiyin"}
    difficulty = diff_map.get(message.text, "orta")
    await state.update_data(difficulty=difficulty)
    await state.set_state(AdminStates.waiting_category)
    cats = db.get_categories()
    buttons = [[KeyboardButton(text=cat)] for cat in cats]
    buttons.append([KeyboardButton(text="➕ Yangi kategoriya")])
    await message.answer(
        "📂 <b>Kategoriyani tanlang:</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    )

@dp.message(AdminStates.waiting_category)
async def process_category(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if message.text == "➕ Yangi kategoriya":
        await state.set_state(AdminStates.waiting_new_category)
        await message.answer("📂 <b>Yangi kategoriya nomini yozing:</b>", parse_mode="HTML")
        return
    await state.update_data(category=message.text.strip())
    await state.set_state(AdminStates.waiting_explanation)
    await message.answer(
        "💡 <b>Izoh yozing:</b>\n<i>Yo'q bo'lsa — 'Yo'q' yozing</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Yo'q")]], resize_keyboard=True)
    )

@dp.message(AdminStates.waiting_new_category)
async def process_new_category(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    new_cat = message.text.strip()
    db.add_category(new_cat)
    await state.update_data(category=new_cat)
    await state.set_state(AdminStates.waiting_explanation)
    await message.answer(
        f"✅ Kategoriya '{new_cat}' qo'shildi!\n\n💡 <b>Izoh yozing:</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Yo'q")]], resize_keyboard=True)
    )

@dp.message(AdminStates.waiting_explanation)
async def process_explanation(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    explanation = "" if message.text.lower() in ("yo'q", "yoq", "-") else message.text.strip()
    await state.update_data(explanation=explanation)
    await state.set_state(AdminStates.waiting_image)
    await message.answer(
        "🖼 <b>Rasm yuborish (ixtiyoriy):</b>\n<i>Kerak bo'lmasa — 'Yo'q' yozing</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Yo'q")]], resize_keyboard=True)
    )

@dp.message(AdminStates.waiting_image)
async def process_image(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    image_id = ""
    if message.photo:
        image_id = message.photo[-1].file_id

    data = await state.get_data()
    await state.clear()

    q_type = data.get("q_type", "test")
    q_text = data.get("q_text", "")
    options = data.get("options", "")
    correct = data.get("correct", "")
    coins = data.get("coins", 5)
    difficulty = data.get("difficulty", "orta")
    category = data.get("category", "Umumiy")
    explanation = data.get("explanation", "")

    db.add_question(q_text, q_type, options, correct, coins, category, difficulty, explanation, image_id)

    type_names = {"test": "📝 Test", "open": "✍️ Ochiq", "premium": "⭐ Premium"}
    type_name = type_names.get(q_type, q_type)

    await message.answer(
        f"✅ <b>Savol qo'shildi!</b>\n\n"
        f"📌 Tur: {type_name}\n"
        f"❓ Savol: {q_text[:50]}\n"
        f"💰 Coin: {coins}\n"
        f"📂 Kategoriya: {category}",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )

    # Barcha foydalanuvchilarga bildirishnoma yuborish
    cur = db.get_conn().cursor()
    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()

    if users:
        notify_text = (
            f"🆕 <b>Yangi savol qo'shildi!</b>\n\n"
            f"📂 Kategoriya: <b>{category}</b>\n"
            f"{type_name}  {DIFFICULTY_ICONS.get(difficulty, '🟡')} {DIFFICULTY_NAMES.get(difficulty, 'Orta')}\n"
            f"💰 Coin: <b>{coins}</b>\n\n"
            f"🎯 Hoziroq <b>Savol olish</b> tugmasini bosing!"
        )
        sent = 0
        for (uid,) in users:
            try:
                await bot.send_message(uid, notify_text, parse_mode="HTML")
                sent += 1
            except:
                pass
        await message.answer(f"📢 {sent} ta foydalanuvchiga xabar yuborildi!", reply_markup=admin_menu())

# ─── SAVOLLAR RO'YXATI ────────────────────────────────────────────────────────
@dp.message(F.text == "📋 Savollar ro'yxati")
async def list_questions(message: types.Message):
    if not is_admin(message.from_user.id): return
    questions = db.get_all_questions()
    if not questions:
        await message.answer("Hozircha savollar yo'q!", reply_markup=admin_menu())
        return
    type_icons = {"test": "📝", "open": "✍️", "premium": "⭐"}
    text = f"📋 <b>Savollar ({len(questions)} ta):</b>\n\n"
    for q in questions[:20]:
        q_id, q_text, q_type, options, correct, coins, category, difficulty = q
        icon = type_icons.get(q_type, "📝")
        diff_icon = DIFFICULTY_ICONS.get(difficulty, "🟡")
        short = q_text[:40] + "..." if len(q_text) > 40 else q_text
        text += f"{icon} <b>#{q_id}</b> [{category}] {diff_icon}\n{short}\n💰 {coins} coin\n\n"
    await message.answer(text, parse_mode="HTML", reply_markup=admin_menu())

# ─── STATISTIKA ───────────────────────────────────────────────────────────────
@dp.message(F.text == "📊 Statistika")
async def show_stats(message: types.Message):
    if not is_admin(message.from_user.id): return
    stats = db.get_stats()
    text = (
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{stats['users']}</b>\n"
        f"❓ Savollar: <b>{stats['questions']}</b>\n"
        f"📝 Javoblar: <b>{stats['answers']}</b>\n"
        f"✅ To'g'ri: <b>{stats['correct']}</b>\n"
        f"🎯 Aniqlik: <b>{stats['accuracy']}%</b>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=admin_menu())

# ─── FOYDALANUVCHILAR ─────────────────────────────────────────────────────────
@dp.message(F.text == "👥 Foydalanuvchilar")
async def show_users(message: types.Message):
    if not is_admin(message.from_user.id): return
    top = db.get_leaderboard(20)
    total = db.get_total_users()
    text = f"👥 <b>Foydalanuvchilar ({total} ta)</b>\n\n"
    for i, (uid, fname, uname, coins) in enumerate(top[:15]):
        name = fname or uname or f"User{uid}"
        text += f"{i+1}. <b>{name}</b> — {round(coins, 1)} coin\n"
    await message.answer(text, parse_mode="HTML", reply_markup=admin_menu())

# ─── TAKLIFLAR ────────────────────────────────────────────────────────────────
@dp.message(F.text == "💬 Takliflar")
async def show_feedbacks(message: types.Message):
    if not is_admin(message.from_user.id): return
    feedbacks = db.get_feedbacks(10)
    if not feedbacks:
        await message.answer("Hozircha takliflar yo'q!", reply_markup=admin_menu())
        return
    text = "💬 <b>So'nggi takliflar:</b>\n\n"
    for fb in feedbacks:
        fb_id, uid, fname, uname, fb_text, created_at, is_read = fb
        status = "✅" if is_read else "🆕"
        text += f"{status} <b>{fname}</b> (@{uname})\n{fb_text[:100]}\n<i>{created_at[:16]}</i>\n\n"
    db.mark_feedbacks_read()
    await message.answer(text, parse_mode="HTML", reply_markup=admin_menu())

# ─── KATEGORIYALAR ────────────────────────────────────────────────────────────
@dp.message(F.text == "📂 Kategoriyalar")
async def show_categories(message: types.Message):
    if not is_admin(message.from_user.id): return
    cats = db.get_categories_with_count()
    if not cats:
        await message.answer("Kategoriyalar yo'q!", reply_markup=admin_menu())
        return
    text = "📂 <b>Kategoriyalar:</b>\n\n"
    for cat, count in cats:
        text += f"📁 <b>{cat}</b> — {count} ta savol\n"
    await message.answer(text, parse_mode="HTML", reply_markup=admin_menu())

# ─── MAIN ─────────────────────────────────────────────────────────────────────
async def main():
    logger.info("Bot ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
