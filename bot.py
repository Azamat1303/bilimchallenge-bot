import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

import config
import database as db

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# States (Holatlar)
class AdminStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_options = State()
    waiting_for_correct = State()

class AdminListeningStates(StatesGroup):
    waiting_for_audio = State()
    waiting_for_text_or_image = State()
    waiting_for_options = State()
    waiting_for_correct = State()

class QuizStates(StatesGroup):
    in_progress = State()
    listening_in_progress = State()

# Bosh menyu tugmalari
def get_main_keyboard(user_id):
    builder = ReplyKeyboardBuilder()
    builder.button(text="🧠 Testni Boshlash")
    builder.button(text="🎧 IELTS Listening")
    builder.button(text="📊 Reyting")
    
    if user_id in config.ADMIN_IDS:
        builder.button(text="⚙️ Admin Panel")
        
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

# Admin menyu tugmalari
def get_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="➕ Oddiy Savol Qo'shish")
    builder.button(text="🎧 Listening Savol Qo'shish")
    builder.button(text="🗑️ Savollarni Ko'rish/O'chirish")
    builder.button(text="🏠 Bosh Menyu")
    builder.adjust(1, 1, 1)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    db.add_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    await message.answer(
        f"Salom, {message.from_user.full_name}! BilimChallenge botiga xush kelibsiz.\n"
        f"O'zingizga kerakli bo'limni tanlang:",
        reply_markup=get_main_keyboard(message.from_user.id)
    )

@dp.message(F.text == "🏠 Bosh Menyu")
async def back_to_main(message: types.Message):
    await message.answer("Bosh menyuga qaytdingiz:", reply_markup=get_main_keyboard(message.from_user.id))

# ================= ADMIN PANEL LOGIKASI =================

@dp.message(F.text == "⚙️ Admin Panel")
async def admin_panel(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    await message.answer("Admin panelga xush kelibsiz. Amallardan birini tanlang:", reply_markup=get_admin_keyboard())

# --- Oddiy Savol Qo'shish ---
@dp.message(F.text == "➕ Oddiy Savol Qo'shish")
async def add_q_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS: return
    await message.answer("Savol matnini kiriting:")
    await state.set_state(AdminStates.waiting_for_text)

@dp.message(AdminStates.waiting_for_text)
async def add_q_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("Variantlarni kiriting (vergul bilan ajrating, masalan: A,B,C,D):")
    await state.set_state(AdminStates.waiting_for_options)

@dp.message(AdminStates.waiting_for_options)
async def add_q_options(message: types.Message, state: FSMContext):
    await state.update_data(options=message.text)
    await message.answer("To'g'ri javobni kiriting (Variantlardan biri bilan aynan bir xil bo'lsin):")
    await state.set_state(AdminStates.waiting_for_correct)

@dp.message(AdminStates.waiting_for_correct)
async def add_q_correct(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db.add_question(data['text'], data['options'], message.text.strip())
    await message.answer("Savol muvaffaqiyatli qo'shildi!", reply_markup=get_admin_keyboard())
    await state.clear()

# --- Listening Savol Qo'shish ---
@dp.message(F.text == "🎧 Listening Savol Qo'shish")
async def add_listening_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS: return
    await message.answer("Listening uchun **Audio (.mp3)** faylini yuboring:")
    await state.set_state(AdminListeningStates.waiting_for_audio)

@dp.message(AdminListeningStates.waiting_for_audio, F.audio)
async def add_listening_audio(message: types.Message, state: FSMContext):
    await state.update_data(audio_file_id=message.audio.file_id)
    await message.answer("Endi savol matnini kiriting YOKI savol rasmini (Photo) yuboring:")
    await state.set_state(AdminListeningStates.waiting_for_text_or_image)

@dp.message(AdminListeningStates.waiting_for_text_or_image)
async def add_listening_media(message: types.Message, state: FSMContext):
    if message.photo:
        await state.update_data(image_file_id=message.photo[-1].file_id, question_text=message.caption or "")
    else:
        await state.update_data(question_text=message.text, image_file_id=None)
        
    await message.answer("Variantlarni kiriting (vergul bilan ajrating, masalan: A,B,C):")
    await state.set_state(AdminListeningStates.waiting_for_options)

@dp.message(AdminListeningStates.waiting_for_options)
async def add_listening_options(message: types.Message, state: FSMContext):
    await state.update_data(options=message.text)
    await message.answer("To'g'ri javobni kiriting (Masalan: A yoki B):")
    await state.set_state(AdminListeningStates.waiting_for_correct)

@dp.message(AdminListeningStates.waiting_for_correct)
async def add_listening_correct(message: types.Message, state: FSMContext):
    data = await state.get_data()
    # TUZATILGAN QISM: "image_file_id=" kalit so'zi olib tashlandi, faqat qiymat o'zi uzatilyapti
    db.add_listening_question(
        data['audio_file_id'], 
        data['question_text'], 
        data['image_file_id'], 
        data['options'], 
        message.text.strip()
    )
    await message.answer("Listening savoli tizimga qo'shildi!", reply_markup=get_admin_keyboard())
    await state.clear()

# --- Savollarni o'chirish paneli ---
@dp.message(F.text == "🗑️ Savollarni Ko'rish/O'chirish")
async def show_questions_delete(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS: return
    
    # Oddiy savollar
    qs = db.get_all_questions()
    if qs:
        await message.answer("⬇️ **Oddiy Test Savollari:**")
        for q in qs:
            builder = InlineKeyboardBuilder()
            builder.button(text="❌ O'chirish", callback_data=f"del_normal_{q[0]}")
            await message.answer(f"ID: {q[0]}\nSavol: {q[1]}", reply_markup=builder.as_markup())
            
    # Listening savollar
    l_qs = db.get_all_listening_questions()
    if l_qs:
        await message.answer("⬇️ **IELTS Listening Savollari:**")
        for l_q in l_qs:
            builder = InlineKeyboardBuilder()
            builder.button(text="❌ O'chirish", callback_data=f"del_listen_{l_q[0]}")
            await message.answer(f"ID: {l_q[0]}\nSavol/Matn: {l_q[2]}", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("del_"))
async def delete_callback(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    q_type = parts[1]
    q_id = int(parts[2])
    
    if q_type == "normal":
        db.delete_question(q_id)
    elif q_type == "listen":
        db.delete_listening_question(q_id)
        
    await callback.answer("Savol o'chirildi!")
    await callback.message.delete()


# ================= FOYDALANUVCHILAR UCHUN TEST CHIQARISH =================

# --- 1. Oddiy test tizimi ---
@dp.message(F.text == "🧠 Testni Boshlash")
async def start_quiz(message: types.Message, state: FSMContext):
    questions = db.get_all_questions()
    if not questions:
        await message.answer("Hozircha bazada savollar yo'q.")
        return
    
    await state.set_state(QuizStates.in_progress)
    await state.update_data(questions=questions, current_index=0, correct_count=0)
    await send_next_question(message, state)

async def send_next_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    idx = data['current_index']
    questions = data['questions']
    
    if idx >= len(questions):
        db.update_score(message.from_user.id, data['correct_count'])
        await message.answer(f"🎉 Test yakunlandi!\nSiz {len(questions)} ta savoldan {data['correct_count']} tasiga to'g'ri javob berdingiz.", reply_markup=get_main_keyboard(message.from_user.id))
        await state.clear()
        return

    q = questions[idx]
    options = [opt.strip() for opt in q[2].split(",")]
    
    builder = InlineKeyboardBuilder()
    for opt in options:
        builder.button(text=opt, callback_data=f"quiz_ans_{opt}")
    builder.adjust(2)
    
    await message.answer(f"❓ Savol {idx+1}:\n\n{q[1]}", reply_markup=builder.as_markup())

@dp.callback_query(QuizStates.in_progress, F.data.startswith("quiz_ans_"))
async def handle_quiz_answer(callback: types.CallbackQuery, state: FSMContext):
    user_ans = callback.data.replace("quiz_ans_", "")
    data = await state.get_data()
    idx = data['current_index']
    q = data['questions'][idx]
    correct_ans = q[3]
    
    correct_count = data['correct_count']
    if user_ans.lower() == correct_ans.lower():
        correct_count += 1
        await callback.answer("To'g'ri! 🎉")
    else
