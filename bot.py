import logging
import asyncio
import random
import re
import aiohttp
from datetime import datetime, timedelta
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
DIFFICULTY_TIME = {"oson": 30, "orta": 60, "qiyin": 90}
active_timers = {}
ILLEGAL_WORDS = ["bomb", "portlat", "qotil", "terror", "narkotik", "hack"]
REPORT_DEADLINE_DAYS = 3
SUB_ADMIN_TERM_DAYS = 21

STICKER_QUESTION = "CAACAgQAAxkBAAFK2GFqGBZkvOQYIqxuYRxOg8yZ_kGpCQACLhMAAqtUsFGayERH0PRbYTsE"
STICKER_CORRECT_LOW  = "CAACAgIAAxkBAAFK2HxqGBcuYTvi4L__VuLGnOmw_0h3MQACT6cAAiS3qEprLmY89x6ufjsE"
STICKER_CORRECT_MID  = "CAACAgQAAxkBAAFK2FxqGBZODMIw26R9HpabXj_GXXHY_QAC9wsAAsVA0FKiYzU0cZkIATsE"
STICKER_CORRECT_HIGH = "CAACAgIAAxkBAAFK2HFqGBa54WJlIjngkLvRxQyv_iejvAACUqEAAs2uqEoU5ts6XT2m-DsE"
STICKERS_CORRECT_RANDOM = ["CAACAgIAAxkBAAFK2BdqGBSDpT9UJGnf8A933SkujhR1ugAC7i4AAu2JwEjbRw5y8ATySTsE","CAACAgIAAxkBAAFK2B1qGBSg7YLcDzG45IMbWD9yLQd2twACxCwAAmyCwUhW4u2V7FLn2jsE","CAACAgIAAxkBAAFK2ChqGBT8ht7vPfWPVNZSJ99eSrO4aAACpy4AAlsmwUgiQZe-63v_8DsE"]
STICKER_WRONG_LOW  = "CAACAgIAAxkBAAFK2I5qGBe3fhF_QafwvVtn9eZZJ2wyYgACwnEAAj3NaUpk2l3tCbDGJTsE"
STICKER_WRONG_MID  = "CAACAgIAAxkBAAFK2GZqGBaGcsKcNXFNKzEjnwAB_N6SLx4AAiZjAAIexglIbW6k0yQK8f47BA"
STICKER_WRONG_HIGH = "CAACAgIAAxkBAAFK2ABqGBdBbZ364p3pJn7rIUWgmYP_ZwACe5gAArNyiUj8ULr6FLOqsTsE"
STICKERS_WRONG_RANDOM = ["CAACAgIAAxkBAAFK2B9qGBSy53xM_fWFSR3_QB-b-96PzwACuUIAAkSZyEj30qYDy3h_-TsE","CAACAgIAAxkBAAFK2CFqGBTQxCg8PTNAy8ELJPO1ekiKQAACcSkAAthiwUi7vlkGdgu7SjsE"]
STICKERS_TIMEOUT = ["CAACAgIAAxkBAAFK2CpqGBT9Y8JM8DQ_k5oZ_koPS4fNlgACWiYAAlDgwEhOxSLS4ALrSDsE","CAACAgIAAxkBAAFK2CVqGBTpcrLFTrOLIF6ZRjaUHU_NxwACei0AAhRdCUkIUGBOZbVgrjsE"]
STICKER_LEADERBOARD = "CAACAgQAAxkBAAFK2F5qGBZib8V7GFYDhDMw8H10BaJIfgAChBYAAkfnsFEm5zMVxs4-nDsE"
STICKER_TOP1 = "CAACAgQAAxkBAAFK2pVqGC8QLY1z08fADOc-QGogLJWn2AACFxsAAvdb0FEvAAGtAAFifD0MOwQ"
STICKER_TOP2 = "CAACAgQAAxkBAAFK2E9qGBXpsYQFe_Q2qKm4WQcn5lZeRAACGhYAAkQp2VGaVMouneMzrjsE"
STICKER_TOP3 = "CAACAgQAAxkBAAFK2FJqGBXrg1BmRPSdqE663UwwKVFsWAACnxQAAk8s6FDKghp6_6nUJDsE"
STICKER_TOP5 = "CAACAgQAAxkBAAFK2FZqGBX4e7mmRfTgeyt3WLZCD4xSdQADFwACZFbRUYAvpAABVerDrjsE"
STICKER_TOP10= "CAACAgQAAxkBAAFK2FhqGBYKX7aALmALEnidgp-wFO-3nQAC2RYAAj6CKVFONJy-EgNA5TsE"

def get_correct_sticker(c):
    if c<=1: return STICKER_CORRECT_LOW
    elif c<=5: return random.choice(STICKERS_CORRECT_RANDOM)
    else: return STICKER_CORRECT_HIGH

def get_wrong_sticker(c):
    if c<=1: return STICKER_WRONG_LOW
    elif c<=5: return STICKER_WRONG_MID
    else: return STICKER_WRONG_HIGH

def get_rank_sticker(r):
    if r==1: return STICKER_TOP1
    elif r==2: return STICKER_TOP2
    elif r==3: return STICKER_TOP3
    elif r<=5: return STICKER_TOP5
    elif r<=10: return STICKER_TOP10
    return None

def is_admin(uid): return uid in ADMIN_IDS
def is_sub_admin(uid): return db.is_sub_admin(uid)
def is_any_admin(uid): return is_admin(uid) or is_sub_admin(uid)

class AdminStates(StatesGroup):
    waiting_question_type=State(); waiting_question_text=State(); waiting_options=State()
    waiting_correct_answer=State(); waiting_coin_reward=State(); waiting_difficulty=State()
    waiting_category=State(); waiting_explanation=State(); waiting_image=State()
    waiting_time_limit=State(); waiting_new_category=State(); editing_field=State()
    editing_value=State(); broadcast_text=State(); broadcast_image=State()
    payment_amount=State(); payment_note=State(); payment_target=State()
    sub_admin_select=State(); sub_admin_salary=State(); fb_reply_text=State()

class SubAdminStates(StatesGroup):
    waiting_question_type=State(); waiting_question_text=State(); waiting_options=State()
    waiting_correct_answer=State(); waiting_coin_reward=State(); waiting_difficulty=State()
    waiting_category=State(); waiting_explanation=State()
    writing_report=State(); fb_reply=State(); broadcast_text=State(); broadcast_image=State()

class UserStates(StatesGroup):
    answering_open=State(); sending_feedback=State(); answering_premium=State()
    answering_ielts=State(); ai_chat=State(); ai_chat_confirm_debt=State()

def main_menu(uid):
    b=[[KeyboardButton(text="🎯 Savol olish"),KeyboardButton(text="🏆 Reyting")],
       [KeyboardButton(text="👤 Profilim"),KeyboardButton(text="ℹ️ Yordam")],
       [KeyboardButton(text="📝 Taklif/Shikoyat"),KeyboardButton(text="🎓 IELTS")],
       [KeyboardButton(text="🤖 AI Chat")]]
    if is_admin(uid): b.append([KeyboardButton(text="⚙️ Admin Panel")])
    if is_sub_admin(uid) and not is_admin(uid): b.append([KeyboardButton(text="🛡 Yordamchi Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=b, resize_keyboard=True)

def admin_menu():
    b=[[KeyboardButton(text="➕ Savol qo'shish"),KeyboardButton(text="📋 Savollar ro'yxati")],
       [KeyboardButton(text="✏️ Savol tahrirlash"),KeyboardButton(text="🗑 Savol o'chirish")],
       [KeyboardButton(text="📂 Kategoriyalar"),KeyboardButton(text="📊 Statistika")],
       [KeyboardButton(text="👥 Foydalanuvchilar"),KeyboardButton(text="💬 Takliflar")],
       [KeyboardButton(text="📢 Xabar yuborish"),KeyboardButton(text="⏳ Kutayotgan savollar")],
       [KeyboardButton(text="🛡 Yordamchi Adminlar"),KeyboardButton(text="🗳 Saylov boshqaruvi")],
       [KeyboardButton(text="💰 Mukofot/Jarima"),KeyboardButton(text="📜 Hisobotlar")],
       [KeyboardButton(text="🔙 Asosiy menyu")]]
    return ReplyKeyboardMarkup(keyboard=b, resize_keyboard=True)

def sub_admin_menu():
    b=[[KeyboardButton(text="➕ Savol yuborish"),KeyboardButton(text="📝 Hisobot yozish")],
       [KeyboardButton(text="💬 Takliflar o'qish"),KeyboardButton(text="💬 Javob yozish")],
       [KeyboardButton(text="📢 Xabar tarqatish"),KeyboardButton(text="💰 Moashim")],
       [KeyboardButton(text="🔙 Asosiy menyu")]]
    return ReplyKeyboardMarkup(keyboard=b, resize_keyboard=True)

def streak_bonus(s):
    b=1.0
    for t in sorted(STREAK_BONUSES.keys()):
        if s>=t: b=STREAK_BONUSES[t]
    return b

def streak_msg(s):
    if s>=10: return f"🔥🔥🔥 SUPER STREAK x{s}!"
    if s>=5: return f"🔥🔥 STREAK x{s}!"
    if s>=3: return f"🔥 STREAK x{s}!"
    return ""

def shuffle_options(opts_str, correct_letter):
    opts=opts_str.split("|")
    ci=ord(correct_letter.upper())-65
    if ci>=len(opts): return opts_str, correct_letter
    ct=opts[ci]; idx=list(range(len(opts))); random.shuffle(idx)
    shuffled=[opts[i] for i in idx]; nci=shuffled.index(ct)
    return "|".join(shuffled), chr(65+nci)

def check_answer(user_ans, correct_ans):
    uc=user_ans.strip().lower()
    return uc in [a.strip().lower() for a in correct_ans.split("\n") if a.strip()]

async def ai_req(prompt):
    try:
        url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        async with aiohttp.ClientSession() as s:
            async with s.post(url, headers={"Content-Type":"application/json"},
                json={"contents":[{"parts":[{"text":prompt}]}]},
                timeout=aiohttp.ClientTimeout(total=30)) as r:
                d=await r.json()
                if "candidates" in d and d["candidates"]:
                    return d["candidates"][0]["content"]["parts"][0]["text"]
    except: pass
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},
                json={"model":GROQ_MODEL,"messages":[{"role":"user","content":prompt}],"max_tokens":1000},
                timeout=aiohttp.ClientTimeout(total=30)) as r:
                d=await r.json()
                return d["choices"][0]["message"]["content"]
    except: pass
    return "⚠️ AI hozirda ishlamayapti."

async def ai_chat_req(history, user_text):
    sys_p="Siz BilimChallenge botining yordamchi AI sisiz. O'zbek tilida qisqa va foydali javob bering."
    try:
        prompt=sys_p+"\n\n"
        for h in history[-6:]:
            role="Foydalanuvchi" if h["role"]=="user" else "AI"
            prompt+=f"{role}: {h['content']}\n"
        prompt+=f"Foydalanuvchi: {user_text}\nAI:"
        url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        async with aiohttp.ClientSession() as s:
            async with s.post(url, headers={"Content-Type":"application/json"},
                json={"contents":[{"parts":[{"text":prompt}]}]},
                timeout=aiohttp.ClientTimeout(total=30)) as r:
                d=await r.json()
                if "candidates" in d and d["candidates"]:
                    return d["candidates"][0]["content"]["parts"][0]["text"]
    except: pass
    try:
        msgs=[{"role":"system","content":sys_p}]+history[-6:]+[{"role":"user","content":user_text}]
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},
                json={"model":GROQ_MODEL,"messages":msgs,"max_tokens":800},
                timeout=aiohttp.ClientTimeout(total=30)) as r:
                d=await r.json()
                return d["choices"][0]["message"]["content"]
    except: pass
    return "⚠️ AI hozirda ishlamayapti."

def parse_band(text):
    for p in [r'Band\s*Score[:\s]+(\d+\.?\d*)',r'(\d+\.?\d*)\s*/\s*9(?:\.0)?',r'(\d+\.?\d*)\s*ball']:
        m=re.search(p, text, re.IGNORECASE)
        if m:
            try:
                v=float(m.group(1))
                if v<=9: return v
            except: pass
    return None

# ═══════════════ START ═══════════════
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user=message.from_user
    args=message.text.split()
    referrer_id=None
    if len(args)>1 and args[1].startswith("ref"):
        try:
            referrer_id=int(args[1][3:])
            if referrer_id==user.id: referrer_id=None
        except: pass
    db.add_user(user.id, user.username or "", user.first_name or "", referrer_id)
    ref_msg=""
    if referrer_id:
        ref_msg="\n\n🎁 <b>Referal orqali qo'shildingiz!</b>\nDo'stingiz <b>+30 coin</b> oldi!"
    await message.answer(
        f"🧠 <b>BilimChallenge</b> ga xush kelibsiz, {user.first_name}!\n\n"
        "🎯 Savollarga javob bering\n💰 Coinlar to'plang\n"
        "🔥 Streak yig'ing\n🏆 Global reyting\n🎓 IELTS — AI bilan\n🤖 AI Chat\n"
        "👥 Do'stlarni taklif qiling — har biri uchun +30 coin!\n\n"
        "Boshlash uchun <b>Savol olish</b>!"+ref_msg,
        parse_mode="HTML", reply_markup=main_menu(user.id))

@dp.message(Command("cancel"))
@dp.message(Command("stop"))
async def cancel_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=main_menu(message.from_user.id))

# ═══════════════ SAVOL OLISH ═══════════════
@dp.message(F.text=="🎯 Savol olish")
async def get_question_start(message: types.Message, state: FSMContext):
    await state.clear()
    cats=db.get_categories()
    if not cats:
        await message.answer("😔 Hozircha savollar yo'q!"); return
    buttons=[]; row=[]
    for cat in cats:
        row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat_{cat}"))
        if len(row)==2: buttons.append(row); row=[]
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🌐 Aralash (barcha)", callback_data="cat_Barchasi")])
    await message.answer("📂 <b>Kategoriya tanlang:</b>", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("cat_"))
async def category_chosen(callback: types.CallbackQuery, state: FSMContext):
    category=callback.data[4:]
    await state.update_data(category=category)
    try: await callback.message.delete()
    except: pass
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Test savollar", callback_data=f"qmode_test_{category}")],
        [InlineKeyboardButton(text="✍️ Ochiq savollar", callback_data=f"qmode_open_{category}")],
        [InlineKeyboardButton(text="🌐 Aralash", callback_data=f"qmode_all_{category}")]])
    await callback.message.answer(f"📂 <b>{category}</b>\n\nSavol turini tanlang:", parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("qmode_"))
async def qmode_chosen(callback: types.CallbackQuery, state: FSMContext):
    parts=callback.data.split("_",2); mode,category=parts[1],parts[2]
    await state.update_data(category=category, qmode=mode)
    try: await callback.message.delete()
    except: pass
    await send_question(callback.message, callback.from_user.id, state, category, mode)
    await callback.answer()

async def send_question(message, user_id, state, category, mode="all"):
    if mode=="test": q=db.get_random_question(user_id, category, q_type="test")
    elif mode=="open": q=db.get_random_question(user_id, category, q_type="open")
    else: q=db.get_random_question(user_id, category, q_type=None)
    if not q:
        cats=db.get_categories(); buttons=[]; row=[]
        for cat in cats:
            row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat_{cat}"))
            if len(row)==2: buttons.append(row); row=[]
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton(text="🌐 Aralash", callback_data="cat_Barchasi")])
        await message.answer("🎉 <b>Bu bo'limdagi savollar tugadi!</b>\n\nBoshqa kategoriyani tanlang:",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)); return
    q_id,q_text,q_type,options,correct,coins,cat,difficulty,explanation,image_id,time_limit=q
    if q_type=="premium":
        await send_premium_question(message, user_id, state, category); return
    diff_icon=DIFFICULTY_ICONS.get(difficulty,"🟡"); diff_name=DIFFICULTY_NAMES.get(difficulty,"O'rta")
    q_time=DIFFICULTY_TIME.get(difficulty,30)
    header=(f"🆔 <b>#{q_id}</b>  📂 <b>{cat}</b>  {diff_icon} <b>{diff_name}</b>\n"
            f"💰 To'g'ri: <b>+{coins} coin</b>  ❌ Noto'g'ri: <b>-{round(coins*PENALTY_PERCENT,1)} coin</b>\n"
            f"⏱ Vaqt: <b>{q_time} soniya</b>\n\n❓ <b>{q_text}</b>")
    try: await bot.send_sticker(message.chat.id, sticker=STICKER_QUESTION)
    except: pass
    if q_type=="test":
        shuffled_opts,new_correct=shuffle_options(options, correct)
        opts_list=shuffled_opts.split("|")
        kb=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{chr(65+i)}. {opt[:64]}", callback_data=f"ans_{q_id}_{chr(65+i)}_{new_correct}")]
            for i,opt in enumerate(opts_list)])
        if image_id:
            try: sent=await bot.send_photo(message.chat.id, photo=image_id, caption=header, parse_mode="HTML", reply_markup=kb)
            except: sent=await message.answer(header, parse_mode="HTML", reply_markup=kb)
        else: sent=await message.answer(header, parse_mode="HTML", reply_markup=kb)
        await state.update_data(question_id=q_id, msg_id=sent.message_id, chat_id=message.chat.id)
        if user_id in active_timers: active_timers[user_id].cancel()
        active_timers[user_id]=asyncio.create_task(
            question_timeout(user_id,q_id,sent.message_id,message.chat.id,coins,state,q_time))
    else:
        await state.set_state(UserStates.answering_open)
        await state.update_data(question_id=q_id, correct=correct, coins=coins, explanation=explanation)
        text=header+"\n\n✍️ <b>Javobingizni yozing:</b>"
        if image_id:
            try: sent=await bot.send_photo(message.chat.id, photo=image_id, caption=text, parse_mode="HTML")
            except: sent=await message.answer(text, parse_mode="HTML")
        else: sent=await message.answer(text, parse_mode="HTML")
        await message.answer("👆 Javob yozing:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data=f"skip_open_{q_id}")]]))
        if user_id in active_timers: active_timers[user_id].cancel()
        active_timers[user_id]=asyncio.create_task(
            question_timeout(user_id,q_id,sent.message_id,message.chat.id,coins,state,q_time))

async def question_timeout(user_id,q_id,msg_id,chat_id,coins,state,q_time=30):
    total=q_time; wait=total-10
    if wait>0: await asyncio.sleep(wait)
    timer_msg=None
    for remaining in range(10,0,-1):
        if db.already_answered(user_id,q_id):
            if timer_msg:
                try: await timer_msg.delete()
                except: pass
            return
        filled=int((remaining/total)*10)
        block="🟥" if remaining<=3 else ("🟧" if remaining<=6 else "🟨")
        bar=block*filled+"⬜"*(10-filled)
        try:
            if timer_msg is None: timer_msg=await bot.send_message(chat_id,f"⏱ <b>{remaining}s</b>  {bar}",parse_mode="HTML")
            else: await timer_msg.edit_text(f"⏱ <b>{remaining}s</b>  {bar}",parse_mode="HTML")
        except: pass
        await asyncio.sleep(1)
    if db.already_answered(user_id,q_id):
        if timer_msg:
            try: await timer_msg.delete()
            except: pass
        return
    db.save_answer(user_id,q_id,False); penalty=round(coins*TIMEOUT_PENALTY,1)
    db.add_coins(user_id,-penalty); db.update_streak(user_id,False)
    if timer_msg:
        try: await timer_msg.delete()
        except: pass
    try: await bot.edit_message_reply_markup(chat_id=chat_id,message_id=msg_id,reply_markup=None)
    except: pass
    try: await bot.send_sticker(chat_id,sticker=random.choice(STICKERS_TIMEOUT))
    except: pass
    data=await state.get_data()
    cat=data.get("category","Barchasi"); mode=data.get("qmode","all")
    try:
        await bot.send_message(chat_id,f"⏰ <b>Vaqt tugadi!</b>\n❌ -{penalty} coin (45%)",parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="➡️ Keyingi savol",callback_data=f"next_{mode}_{cat}")]]))
    except: pass
    active_timers.pop(user_id,None)

@dp.callback_query(F.data.startswith("ans_"))
async def handle_test_answer(callback: types.CallbackQuery, state: FSMContext):
    parts=callback.data.split("_")
    q_id,ua,cl=int(parts[1]),parts[2],parts[3]
    uid=callback.from_user.id
    if db.already_answered(uid,q_id):
        await callback.answer("⚠️ Allaqachon javob bergansiz!",show_alert=True); return
    q=db.get_question_by_id(q_id)
    if not q:
        await callback.answer("Savol topilmadi!",show_alert=True); return
    q_id,q_text,q_type,options,correct,coins,cat,diff,explanation,image_id,tl=q
    is_correct=ua.upper()==cl.upper()
    db.save_answer(uid,q_id,is_correct)
    if uid in active_timers: active_timers[uid].cancel(); active_timers.pop(uid,None)
    data=await state.get_data()
    cat2=data.get("category","Barchasi"); mode=data.get("qmode","all")
    if is_correct:
        ns=db.update_streak(uid,True); bonus=streak_bonus(ns); earned=round(coins*bonus,1)
        db.add_coins(uid,earned); text=f"✅ <b>To'g'ri!</b> +{earned} coin 🎉"
        if bonus>1: text+=f"\n🔥 Streak bonusi x{bonus}!"
        sm=streak_msg(ns)
      STICKERS_WRONG_RANDOM = ["CAACAgIAAxkBAAFK2B9qGBSy53xM_fWFSR3_QB-b-96PzwACuUIAAkSZyEj30qYDy3h_-TsE","CAACAgIAAxkBAAFK2CFqGBTQxCg8PTNAy8ELJPO1ekiKQAACcSkAAthiwUi7vlkGdgu7SjsE"]
STICKERS_TIMEOUT = ["CAACAgIAAxkBAAFK2CpqGBT9Y8JM8DQ_k5oZ_koPS4fNlgACWiYAAlDgwEhOxSLS4ALrSDsE","CAACAgIAAxkBAAFK2CVqGBTpcrLFTrOLIF6ZRjaUHU_NxwACei0AAhRdCUkIUGBOZbVgrjsE"]
STICKER_LEADERBOARD = "CAACAgQAAxkBAAFK2F5qGBZib8V7GFYDhDMw8H10BaJIfgAChBYAAkfnsFEm5zMVxs4-nDsE"
STICKER_TOP1 = "CAACAgQAAxkBAAFK2pVqGC8QLY1z08fADOc-QGogLJWn2AACFxsAAvdb0FEvAAGtAAFifD0MOwQ"
STICKER_TOP2 = "CAACAgQAAxkBAAFK2E9qGBXpsYQFe_Q2qKm4WQcn5lZeRAACGhYAAkQp2VGaVMouneMzrjsE"
STICKER_TOP3 = "CAACAgQAAxkBAAFK2FJqGBXrg1BmRPSdqE663UwwKVFsWAACnxQAAk8s6FDKghp6_6nUJDsE"
STICKER_TOP5 = "CAACAgQAAxkBAAFK2FZqGBX4e7mmRfTgeyt3WLZCD4xSdQADFwACZFbRUYAvpAABVerDrjsE"
STICKER_TOP10= "CAACAgQAAxkBAAFK2FhqGBYKX7aALmALEnidgp-wFO-3nQAC2RYAAj6CKVFONJy-EgNA5TsE"

def get_correct_sticker(c):
    if c<=1: return STICKER_CORRECT_LOW
    elif c<=5: return random.choice(STICKERS_CORRECT_RANDOM)
    else: return STICKER_CORRECT_HIGH

def get_wrong_sticker(c):
    if c<=1: return STICKER_WRONG_LOW
    elif c<=5: return STICKER_WRONG_MID
    else: return STICKER_WRONG_HIGH

def get_rank_sticker(r):
    if r==1: return STICKER_TOP1
    elif r==2: return STICKER_TOP2
    elif r==3: return STICKER_TOP3
    elif r<=5: return STICKER_TOP5
    elif r<=10: return STICKER_TOP10
    return None

def is_admin(uid): return uid in ADMIN_IDS
def is_sub_admin(uid): return db.is_sub_admin(uid)
def is_any_admin(uid): return is_admin(uid) or is_sub_admin(uid)

class AdminStates(StatesGroup):
    waiting_question_type=State(); waiting_question_text=State(); waiting_options=State()
    waiting_correct_answer=State(); waiting_coin_reward=State(); waiting_difficulty=State()
    waiting_category=State(); waiting_explanation=State(); waiting_image=State()
    waiting_time_limit=State(); waiting_new_category=State(); editing_field=State()
    editing_value=State(); broadcast_text=State(); broadcast_image=State()
    payment_amount=State(); payment_note=State(); payment_target=State()
    sub_admin_select=State(); sub_admin_salary=State(); fb_reply_text=State()

class SubAdminStates(StatesGroup):
    waiting_question_type=State(); waiting_question_text=State(); waiting_options=State()
    waiting_correct_answer=State(); waiting_coin_reward=State(); waiting_difficulty=State()
    waiting_category=State(); waiting_explanation=State()
    writing_report=State(); fb_reply=State(); broadcast_text=State(); broadcast_image=State()

class UserStates(StatesGroup):
    answering_open=State(); sending_feedback=State(); answering_premium=State()
    answering_ielts=State(); ai_chat=State(); ai_chat_confirm_debt=State()

def main_menu(uid):
    b=[[KeyboardButton(text="🎯 Savol olish"),KeyboardButton(text="🏆 Reyting")],
       [KeyboardButton(text="👤 Profilim"),KeyboardButton(text="ℹ️ Yordam")],
       [KeyboardButton(text="📝 Taklif/Shikoyat"),KeyboardButton(text="🎓 IELTS")],
       [KeyboardButton(text="🤖 AI Chat")]]
    if is_admin(uid): b.append([KeyboardButton(text="⚙️ Admin Panel")])
    if is_sub_admin(uid) and not is_admin(uid): b.append([KeyboardButton(text="🛡 Yordamchi Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=b, resize_keyboard=True)

def admin_menu():
    b=[[KeyboardButton(text="➕ Savol qo'shish"),KeyboardButton(text="📋 Savollar ro'yxati")],
       [KeyboardButton(text="✏️ Savol tahrirlash"),KeyboardButton(text="🗑 Savol o'chirish")],
       [KeyboardButton(text="📂 Kategoriyalar"),KeyboardButton(text="📊 Statistika")],
       [KeyboardButton(text="👥 Foydalanuvchilar"),KeyboardButton(text="💬 Takliflar")],
       [KeyboardButton(text="📢 Xabar yuborish"),KeyboardButton(text="⏳ Kutayotgan savollar")],
       [KeyboardButton(text="🛡 Yordamchi Adminlar"),KeyboardButton(text="🗳 Saylov boshqaruvi")],
       [KeyboardButton(text="💰 Mukofot/Jarima"),KeyboardButton(text="📜 Hisobotlar")],
       [KeyboardButton(text="🔙 Asosiy menyu")]]
    return ReplyKeyboardMarkup(keyboard=b, resize_keyboard=True)

def sub_admin_menu():
    b=[[KeyboardButton(text="➕ Savol yuborish"),KeyboardButton(text="📝 Hisobot yozish")],
       [KeyboardButton(text="💬 Takliflar o'qish"),KeyboardButton(text="💬 Javob yozish")],
       [KeyboardButton(text="📢 Xabar tarqatish"),KeyboardButton(text="💰 Moashim")],
       [KeyboardButton(text="🔙 Asosiy menyu")]]
    return ReplyKeyboardMarkup(keyboard=b, resize_keyboard=True)

def streak_bonus(s):
    b=1.0
    for t in sorted(STREAK_BONUSES.keys()):
        if s>=t: b=STREAK_BONUSES[t]
    return b

def streak_msg(s):
    if s>=10: return f"🔥🔥🔥 SUPER STREAK x{s}!"
    if s>=5: return f"🔥🔥 STREAK x{s}!"
    if s>=3: return f"🔥 STREAK x{s}!"
    return ""

def shuffle_options(opts_str, correct_letter):
    opts=opts_str.split("|")
    ci=ord(correct_letter.upper())-65
    if ci>=len(opts): return opts_str, correct_letter
    ct=opts[ci]; idx=list(range(len(opts))); random.shuffle(idx)
    shuffled=[opts[i] for i in idx]; nci=shuffled.index(ct)
    return "|".join(shuffled), chr(65+nci)

def check_answer(user_ans, correct_ans):
    uc=user_ans.strip().lower()
    return uc in [a.strip().lower() for a in correct_ans.split("\n") if a.strip()]

async def ai_req(prompt):
    try:
        url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        async with aiohttp.ClientSession() as s:
            async with s.post(url, headers={"Content-Type":"application/json"},
                json={"contents":[{"parts":[{"text":prompt}]}]},
                timeout=aiohttp.ClientTimeout(total=30)) as r:
                d=await r.json()
                if "candidates" in d and d["candidates"]:
                    return d["candidates"][0]["content"]["parts"][0]["text"]
    except: pass
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},
                json={"model":GROQ_MODEL,"messages":[{"role":"user","content":prompt}],"max_tokens":1000},
                timeout=aiohttp.ClientTimeout(total=30)) as r:
                d=await r.json()
                return d["choices"][0]["message"]["content"]
    except: pass
    return "⚠️ AI hozirda ishlamayapti."

async def ai_chat_req(history, user_text):
    sys_p="Siz BilimChallenge botining yordamchi AI sisiz. O'zbek tilida qisqa va foydali javob bering."
    try:
        prompt=sys_p+"\n\n"
        for h in history[-6:]:
            role="Foydalanuvchi" if h["role"]=="user" else "AI"
            prompt+=f"{role}: {h['content']}\n"
        prompt+=f"Foydalanuvchi: {user_text}\nAI:"
        url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        async with aiohttp.ClientSession() as s:
            async with s.post(url, headers={"Content-Type":"application/json"},
                json={"contents":[{"parts":[{"text":prompt}]}]},
                timeout=aiohttp.ClientTimeout(total=30)) as r:
                d=await r.json()
                if "candidates" in d and d["candidates"]:
                    return d["candidates"][0]["content"]["parts"][0]["text"]
    except: pass
    try:
        msgs=[{"role":"system","content":sys_p}]+history[-6:]+[{"role":"user","content":user_text}]
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},
                json={"model":GROQ_MODEL,"messages":msgs,"max_tokens":800},
                timeout=aiohttp.ClientTimeout(total=30)) as r:
                d=await r.json()
                return d["choices"][0]["message"]["content"]
    except: pass
    return "⚠️ AI hozirda ishlamayapti."

def parse_band(text):
    for p in [r'Band\s*Score[:\s]+(\d+\.?\d*)',r'(\d+\.?\d*)\s*/\s*9(?:\.0)?',r'(\d+\.?\d*)\s*ball']:
        m=re.search(p, text, re.IGNORECASE)
        if m:
            try:
                v=float(m.group(1))
                if v<=9: return v
            except: pass
    return None

# ═══════════════ START ═══════════════
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user=message.from_user
    args=message.text.split()
    referrer_id=None
    if len(args)>1 and args[1].startswith("ref"):
        try:
            referrer_id=int(args[1][3:])
            if referrer_id==user.id: referrer_id=None
        except: pass
    db.add_user(user.id, user.username or "", user.first_name or "", referrer_id)
    ref_msg=""
    if referrer_id:
        ref_msg="\n\n🎁 <b>Referal orqali qo'shildingiz!</b>\nDo'stingiz <b>+30 coin</b> oldi!"
    await message.answer(
        f"🧠 <b>BilimChallenge</b> ga xush kelibsiz, {user.first_name}!\n\n"
        "🎯 Savollarga javob bering\n💰 Coinlar to'plang\n"
        "🔥 Streak yig'ing\n🏆 Global reyting\n🎓 IELTS — AI bilan\n🤖 AI Chat\n"
        "👥 Do'stlarni taklif qiling — har biri uchun +30 coin!\n\n"
        "Boshlash uchun <b>Savol olish</b>!"+ref_msg,
        parse_mode="HTML", reply_markup=main_menu(user.id))

@dp.message(Command("cancel"))
@dp.message(Command("stop"))
async def cancel_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=main_menu(message.from_user.id))

# ═══════════════ SAVOL OLISH ═══════════════
@dp.message(F.text=="🎯 Savol olish")
async def get_question_start(message: types.Message, state: FSMContext):
    await state.clear()
    cats=db.get_categories()
    if not cats:
        await message.answer("😔 Hozircha savollar yo'q!"); return
    buttons=[]; row=[]
    for cat in cats:
        row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat_{cat}"))
        if len(row)==2: buttons.append(row); row=[]
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🌐 Aralash (barcha)", callback_data="cat_Barchasi")])
    await message.answer("📂 <b>Kategoriya tanlang:</b>", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("cat_"))
async def category_chosen(callback: types.CallbackQuery, state: FSMContext):
    category=callback.data[4:]
    await state.update_data(category=category)
    try: await callback.message.delete()
    except: pass
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Test savollar", callback_data=f"qmode_test_{category}")],
        [InlineKeyboardButton(text="✍️ Ochiq savollar", callback_data=f"qmode_open_{category}")],
        [InlineKeyboardButton(text="🌐 Aralash", callback_data=f"qmode_all_{category}")]])
    await callback.message.answer(f"📂 <b>{category}</b>\n\nSavol turini tanlang:", parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("qmode_"))
async def qmode_chosen(callback: types.CallbackQuery, state: FSMContext):
    parts=callback.data.split("_",2); mode,category=parts[1],parts[2]
    await state.update_data(category=category, qmode=mode)
    try: await callback.message.delete()
    except: pass
    await send_question(callback.message, callback.from_user.id, state, category, mode)
    await callback.answer()

async def send_question(message, user_id, state, category, mode="all"):
    if mode=="test": q=db.get_random_question(user_id, category, q_type="test")
    elif mode=="open": q=db.get_random_question(user_id, category, q_type="open")
    else: q=db.get_random_question(user_id, category, q_type=None)
    if not q:
        cats=db.get_categories(); buttons=[]; row=[]
        for cat in cats:
            row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat_{cat}"))
            if len(row)==2: buttons.append(row); row=[]
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton(text="🌐 Aralash", callback_data="cat_Barchasi")])
        await message.answer("🎉 <b>Bu bo'limdagi savollar tugadi!</b>\n\nBoshqa kategoriyani tanlang:",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)); return
    q_id,q_text,q_type,options,correct,coins,cat,difficulty,explanation,image_id,time_limit=q
    if q_type=="premium":
        await send_premium_question(message, user_id, state, category); return
    diff_icon=DIFFICULTY_ICONS.get(difficulty,"🟡"); diff_name=DIFFICULTY_NAMES.get(difficulty,"O'rta")
    q_time=DIFFICULTY_TIME.get(difficulty,30)
    header=(f"🆔 <b>#{q_id}</b>  📂 <b>{cat}</b>  {diff_icon} <b>{diff_name}</b>\n"
            f"💰 To'g'ri: <b>+{coins} coin</b>  ❌ Noto'g'ri: <b>-{round(coins*PENALTY_PERCENT,1)} coin</b>\n"
            f"⏱ Vaqt: <b>{q_time} soniya</b>\n\n❓ <b>{q_text}</b>")
    try: await bot.send_sticker(message.chat.id, sticker=STICKER_QUESTION)
    except: pass
    if q_type=="test":
        shuffled_opts,new_correct=shuffle_options(options, correct)
        opts_list=shuffled_opts.split("|")
        kb=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{chr(65+i)}. {opt[:64]}", callback_data=f"ans_{q_id}_{chr(65+i)}_{new_correct}")]
            for i,opt in enumerate(opts_list)])
        if image_id:
            try: sent=await bot.send_photo(message.chat.id, photo=image_id, caption=header, parse_mode="HTML", reply_markup=kb)
            except: sent=await message.answer(header, parse_mode="HTML", reply_markup=kb)
        else: sent=await message.answer(header, parse_mode="HTML", reply_markup=kb)
        await state.update_data(question_id=q_id, msg_id=sent.message_id, chat_id=message.chat.id)
        if user_id in active_timers: active_timers[user_id].cancel()
        active_timers[user_id]=asyncio.create_task(
            question_timeout(user_id,q_id,sent.message_id,message.chat.id,coins,state,q_time))
    else:
        await state.set_state(UserStates.answering_open)
        await state.update_data(question_id=q_id, correct=correct, coins=coins, explanation=explanation)
        text=header+"\n\n✍️ <b>Javobingizni yozing:</b>"
        if image_id:
            try: sent=await bot.send_photo(message.chat.id, photo=image_id, caption=text, parse_mode="HTML")
            except: sent=await message.answer(text, parse_mode="HTML")
        else: sent=await message.answer(text, parse_mode="HTML")
        await message.answer("👆 Javob yozing:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data=f"skip_open_{q_id}")]]))
        if user_id in active_timers: active_timers[user_id].cancel()
        active_timers[user_id]=asyncio.create_task(
            question_timeout(user_id,q_id,sent.message_id,message.chat.id,coins,state,q_time))

async def question_timeout(user_id,q_id,msg_id,chat_id,coins,state,q_time=30):
    total=q_time; wait=total-10
    if wait>0: await asyncio.sleep(wait)
    timer_msg=None
    for remaining in range(10,0,-1):
        if db.already_answered(user_id,q_id):
            if timer_msg:
                try: await timer_msg.delete()
                except: pass
            return
        filled=int((remaining/total)*10)
        block="🟥" if remaining<=3 else ("🟧" if remaining<=6 else "🟨")
        bar=block*filled+"⬜"*(10-filled)
        try:
            if timer_msg is None: timer_msg=await bot.send_message(chat_id,f"⏱ <b>{remaining}s</b>  {bar}",parse_mode="HTML")
            else: await timer_msg.edit_text(f"⏱ <b>{remaining}s</b>  {bar}",parse_mode="HTML")
        except: pass
        await asyncio.sleep(1)
    if db.already_answered(user_id,q_id):
        if timer_msg:
            try: await timer_msg.delete()
            except: pass
        return
    db.save_answer(user_id,q_id,False); penalty=round(coins*TIMEOUT_PENALTY,1)
    db.add_coins(user_id,-penalty); db.update_streak(user_id,False)
    if timer_msg:
        try: await timer_msg.delete()
        except: pass
    try: await bot.edit_message_reply_markup(chat_id=chat_id,message_id=msg_id,reply_markup=None)
    except: pass
    try: await bot.send_sticker(chat_id,sticker=random.choice(STICKERS_TIMEOUT))
    except: pass
    data=await state.get_data()
    cat=data.get("category","Barchasi"); mode=data.get("qmode","all")
    try:
        await bot.send_message(chat_id,f"⏰ <b>Vaqt tugadi!</b>\n❌ -{penalty} coin (45%)",parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="➡️ Keyingi savol",callback_data=f"next_{mode}_{cat}")]]))
    except: pass
    active_timers.pop(user_id,None)

@dp.callback_query(F.data.startswith("ans_"))
async def handle_test_answer(callback: types.CallbackQuery, state: FSMContext):
    parts=callback.data.split("_")
    q_id,ua,cl=int(parts[1]),parts[2],parts[3]
    uid=callback.from_user.id
    if db.already_answered(uid,q_id):
        await callback.answer("⚠️ Allaqachon javob bergansiz!",show_alert=True); return
    q=db.get_question_by_id(q_id)
    if not q:
        await callback.answer("Savol topilmadi!",show_alert=True); return
    q_id,q_text,q_type,options,correct,coins,cat,diff,explanation,image_id,tl=q
    is_correct=ua.upper()==cl.upper()
    db.save_answer(uid,q_id,is_correct)
    if uid in active_timers: active_timers[uid].cancel(); active_timers.pop(uid,None)
    data=await state.get_data()
    cat2=data.get("category","Barchasi"); mode=data.get("qmode","all")
    if is_correct:
        ns=db.update_streak(uid,True); bonus=streak_bonus(ns); earned=round(coins*bonus,1)
        db.add_coins(uid,earned); text=f"✅ <b>To'g'ri!</b> +{earned} coin 🎉"
        if bonus>1: text+=f"\n🔥 Streak bonusi x{bonus}!"
        sm=streak_msg(ns)
        if sm: text+=f"\n{sm}"
    else:
        db.update_streak(uid,False); penalty=round(coins*PENALTY_PERCENT,1)
        db.add_coins(uid,-penalty)
        opts_list=options.split("|"); ci=ord(correct.upper())-65
        ct=opts_list[ci] if ci<len(opts_list) else correct
        text=f"❌ <b>Noto'g'ri!</b> -{penalty} coin\n✅ To'g'ri javob: <b>{ct}</b>"
    if explanation: text+=f"\n\n💡 <i>{explanation}</i>"
    ud=db.get_user(uid); text+=f"\n\n💰 Coinlar: <b>{round(ud[3],1) if ud else 0}</b>  🔥 Streak: <b>{ud[6] if ud else 0}</b>"
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    try: await bot.send_sticker(callback.message.chat.id,sticker=get_correct_sticker(coins) if is_correct else get_wrong_sticker(coins))
    except: pass
    await callback.message.answer(text,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="➡️ Keyingi savol",callback_data=f"next_{mode}_{cat2}")]]))
    await callback.answer()

@dp.message(UserStates.answering_open)
async def handle_open_answer(message: types.Message, state: FSMContext):
    data=await state.get_data()
    q_id,correct,coins=data["question_id"],data["correct"],data["coins"]
    explanation=data.get("explanation",""); cat=data.get("category","Barchasi"); mode=data.get("qmode","all")
    uid=message.from_user.id
    if db.already_answered(uid,q_id): await state.clear(); return
    is_correct=check_answer(message.text,correct)
    db.save_answer(uid,q_id,is_correct)
    if uid in active_timers: active_timers[uid].cancel(); active_timers.pop(uid,None)
    if is_correct:
        ns=db.update_streak(uid,True); bonus=streak_bonus(ns); earned=round(coins*bonus,1)
        db.add_coins(uid,earned); text=f"✅ <b>To'g'ri!</b> +{earned} coin 🎉"
        if bonus>1: text+=f"\n🔥 Streak bonusi x{bonus}!"
        sm=streak_msg(ns)
        if sm: text+=f"\n{sm}"
    else:
        db.update_streak(uid,False); penalty=round(coins*PENALTY_PERCENT,1)
        db.add_coins(uid,-penalty); fc=correct.split("\n")[0].strip()
        text=f"❌ <b>Noto'g'ri!</b> -{penalty} coin\n✅ To'g'ri javob: <b>{fc}</b>"
    if explanation: text+=f"\n\n💡 <i>{explanation}</i>"
    ud=db.get_user(uid); text+=f"\n\n💰 Coinlar: <b>{round(ud[3],1) if ud else 0}</b>  🔥 Streak: <b>{ud[6] if ud else 0}</b>"
    try: await bot.send_sticker(message.chat.id,sticker=get_correct_sticker(coins) if is_correct else get_wrong_sticker(coins))
    except: pass
    await message.answer(text,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="➡️ Keyingi savol",callback_data=f"next_{mode}_{cat}")]]))
    await state.clear()

@dp.callback_query(F.data.startswith("skip_open_"))
async def skip_open(callback: types.CallbackQuery, state: FSMContext):
    data=await state.get_data(); cat=data.get("category","Barchasi"); mode=data.get("qmode","all")
    await state.clear()
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer("⏭ O'tkazib yuborildi.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="➡️ Keyingi savol",callback_data=f"next_{mode}_{cat}")]]))
    await callback.answer()

@dp.callback_query(F.data.startswith("next_"))
async def next_question(callback: types.CallbackQuery, state: FSMContext):
    parts=callback.data.split("_",2); mode,cat=parts[1],parts[2]
    await state.update_data(category=cat,qmode=mode)
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await send_question(callback.message,callback.from_user.id,state,cat,mode)
    await callback.answer()

@dp.callback_query(F.data.startswith("premium_start_"))
async def premium_start(callback: types.CallbackQuery, state: FSMContext):
    await send_premium_question(callback.message,callback.from_user.id,state,callback.data[14:])
    await callback.answer()

async def send_premium_question(message,user_id,state,category):
    q=db.get_random_question(user_id,category,q_type="premium")
    if not q:
        await message.answer("😔 Premium savollar tugadi!"); return
    q_id,q_text,q_type,options,correct,coins,cat,diff,explanation,image_id,tl=q
    await state.set_state(UserStates.answering_premium)
    await state.update_data(question_id=q_id,correct=correct,coins=coins,explanation=explanation,category=category,attempts=0)
    header=(f"⭐ <b>PREMIUM SAVOL</b>  🆔 #{q_id}\n📂 <b>{cat}</b>\n"
            f"💰 To'g'ri: <b>+{coins} coin</b>\n🔄 3 ta urinish  |  ⏭ O'tkazish  |  ❌ Jarima yo'q\n\n❓ <b>{q_text}</b>")
    skip_kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⏭ O'tkazib yuborish",callback_data=f"skip_premium_{q_id}_{category}")]])
    if image_id:
        try: await bot.send_photo(message.chat.id,photo=image_id,caption=header+"\n\n✍️ <b>Javob yozing:</b>",parse_mode="HTML")
        except: await message.answer(header+"\n\n✍️ <b>Javob yozing:</b>",parse_mode="HTML")
    else: await message.answer(header+"\n\n✍️ <b>Javob yozing:</b>",parse_mode="HTML")
    await message.answer("👆 Javob yozing yoki o'tkazing:",reply_markup=skip_kb)

@dp.message(UserStates.answering_premium)
async def handle_premium(message: types.Message, state: FSMContext):
    data=await state.get_data()
    q_id,correct,coins=data["question_id"],data["correct"],data["coins"]
    explanation=data.get("explanation",""); cat=data.get("category","Barchasi"); attempts=data.get("attempts",0)
    uid=message.from_user.id
    if db.already_answered(uid,q_id): await state.clear(); return
    is_correct=check_answer(message.text,correct)
    if is_correct:
        db.save_answer(uid,q_id,True); ns=db.update_streak(uid,True); bonus=streak_bonus(ns)
        earned=round(coins*bonus,1); db.add_coins(uid,earned)
        text=f"✅ <b>To'g'ri!</b> +{earned} coin 🎉"
        if bonus>1: text+=f"\n🔥 Streak bonusi x{bonus}!"
        if explanation: text+=f"\n\n💡 <i>{explanation}</i>"
        ud=db.get_user(uid); text+=f"\n\n💰 Coinlar: <b>{round(ud[3],1) if ud else 0}</b>"
        try: await bot.send_sticker(message.chat.id,sticker=get_correct_sticker(coins))
        except: pass
        await message.answer(text,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⭐ Keyingi premium savol",callback_data=f"premium_start_{cat}")]]))
        await state.clear()
    else:
        attempts+=1; remaining=3-attempts
        if remaining>0:
            await state.update_data(attempts=attempts)
            await message.answer(f"❌ Noto'g'ri! <b>{remaining} ta urinish</b> qoldi:",parse_mode="HTML")
        else:
            db.save_answer(uid,q_id,False); db.update_streak(uid,False)
            try: await bot.send_sticker(message.chat.id,sticker=random.choice(STICKERS_WRONG_RANDOM))
            except: pass
            await message.answer("😔 3 ta urinish tugadi.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⭐ Keyingi premium savol",callback_data=f"premium_start_{cat}")]]))
            await state.clear()

@dp.callback_query(F.data.startswith("skip_premium_"))
async def skip_premium(callback: types.CallbackQuery, state: FSMContext):
    parts=callback.data.split("_"); q_id,cat=int(parts[2]),parts[3]
    db.save_answer(callback.from_user.id,q_id,False); await state.clear()
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer("⏭ O'tkazib yuborildi.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⭐ Keyingi premium savol",callback_data=f"premium_start_{cat}")]]))
    await callback.answer()

# ═══════════════ IELTS ═══════════════
@dp.message(F.text=="🎓 IELTS")
async def ielts_menu(message: types.Message):
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Writing",callback_data="ielts_writing"),InlineKeyboardButton(text="✍️ Essay",callback_data="ielts_essay")],
        [InlineKeyboardButton(text="📖 Reading",callback_data="ielts_reading"),InlineKeyboardButton(text="🗣 Speaking",callback_data="ielts_speaking")],
        [InlineKeyboardButton(text="🎧 Listening",callback_data="ielts_listening")]])
    await message.answer("🎓 <b>IELTS bo'limlari</b>\n\nAI yordamida mashq qiling!",parse_mode="HTML",reply_markup=kb)

@dp.callback_query(F.data.startswith("ielts_"))
async def ielts_section(callback: types.CallbackQuery, state: FSMContext):
    section=callback.data[6:]
    q=db.get_random_question(callback.from_user.id,q_type=section)
    if not q:
        await callback.answer("🎉 Bu bo'limdagi barcha savollarga javob berdingiz!",show_alert=True); return
    q_id,q_text,q_type,options,correct,coins,cat,diff,explanation,image_id,tl=q
    await state.set_state(UserStates.answering_ielts)
    await state.update_data(question_id=q_id,q_type=q_type,coins=coins,section=section)
    tl_note=f"\n⏰ <b>Vaqt:</b> {tl}" if tl else ""
    icons={"writing":"📝","essay":"✍️","reading":"📖","speaking":"🗣","listening":"🎧"}
    header=f"{icons.get(section,'🎓')} <b>{section.upper()}</b>  🆔 #{q_id}{tl_note}\n\n❓ <b>{q_text}</b>"
    if section=="reading": header+="\n\n📌 <i>Javoblarni qatorma-qator yozing</i>"
    elif section in ["speaking","listening"]: header+="\n\n🎙 <i>Ovozli xabar yoki matn yuboring</i>"
    else: header+="\n\n✍️ <i>Javobingizni yozing</i>"
    if image_id:
        try: await bot.send_photo(callback.message.chat.id,photo=image_id,caption=header,parse_mode="HTML")
        except: await callback.message.answer(header,parse_mode="HTML")
    else: await callback.message.answer(header,parse_mode="HTML")
    await callback.message.answer("👆 Javob yuboring:",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⏭ O'tkazib yuborish",callback_data=f"skip_ielts_{section}")]]))
    await callback.answer()

@dp.message(UserStates.answering_ielts)
async def handle_ielts(message: types.Message, state: FSMContext):
    data=await state.get_data()
    q_id,coins,section=data["question_id"],data["coins"],data["section"]
    uid=message.from_user.id
    if section=="reading":
        if not message.text:
            await message.answer("✍️ Matn yuboring!"); return
        q=db.get_question_by_id(q_id); correct_ans=q[4] if q else ""
        uas=[a.strip().lower() for a in message.text.split("\n") if a.strip()]
        cls=[a.strip().lower() for a in correct_ans.split("\n") if a.strip()]
        cc=sum(1 for a in uas if a in cls); total=len(cls)
        score=round((cc/total*9),1) if total>0 else 0
        earned=round(coins*(cc/total),1) if total>0 else 0
        db.add_coins(uid,earned)
        try: db.save_answer(uid,q_id,cc==total)
        except: pass
        result=f"📖 <b>Reading natijasi</b>\n\n✅ To'g'ri: <b>{cc}/{total}</b>\nBand Score: <b>{score}/9.0</b>"
        if cc<total:
            wrong=[a for a in cls if a not in uas]
            result+="\n\n❌ To'g'ri javoblar:\n"+"\n".join([f"• {w}" for w in wrong])
        result+=f"\n\n💰 +{earned} coin"
        await message.answer(result,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=f"➡️ Keyingi {section.upper()}",callback_data=f"ielts_{section}")]]))
        await state.clear(); return
    if section in ["speaking","listening"]:
        if message.voice:
            await message.answer("⏳ Tahlil qilinmoqda...")
            prompt=f"Siz IELTS {section.capitalize()} baholovchisiz. O'zbek tilida baholang. Foydalanuvchi ovozli xabar yubordi. Umumiy tavsiyalar bering. Band Score: X.X/9.0"
        elif message.text:
            await message.answer("⏳ AI tahlil qilmoqda...")
            prompt=f"Siz IELTS {section.capitalize()} baholovchisiz. O'zbek tilida baholang:\n\n{message.text}\n\nBand Score: X.X/9.0. Tavsiyalar bering."
        else:
            await message.answer("🎙 Ovozli xabar yoki matn yuboring!"); return
    elif section in ["writing","essay"]:
        if not message.text:
            await message.answer("✍️ Matn yuboring!"); return
        await message.answer("⏳ AI tahlil qilmoqda...")
        if section=="writing":
            prompt=f"Siz IELTS Writing baholovchisiz. O'ZBEK TILIDA baholang:\n\n{message.text}\n\n1.Task Achievement 2.Coherence 3.Lexical Resource 4.Grammar\n\nBand Score: X.X/9.0\n3 ta tavsiya."
        else:
            prompt=f"Siz akademik insho mutaxassisisiz. O'ZBEK TILIDA tahlil qiling:\n\n{message.text}\n\n1.Kirish 2.Argumentlar 3.Xulosa 4.Uslub 5.Grammatika\n\nUmumiy baho: X/10. 5 ta tavsiya."
    else:
        await message.answer("❓ Noma'lum bo'lim."); return
    analysis=await ai_req(prompt)
    band_score=parse_band(analysis)
    earned=round(coins*(band_score/9.0),1) if band_score else round(coins*0.5,1)
    db.add_coins(uid,earned)
    try: db.save_answer(uid,q_id,True)
    except: pass
    st=f"\n🎯 Band Score: <b>{band_score}/9.0</b>" if band_score else ""
    await message.answer(f"🤖 <b>AI Tahlil:</b>\n\n{analysis}{st}\n\n💰 +{earned} coin (max {coins})",
        parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=f"➡️ Keyingi {section.upper()}",callback_data=f"ielts_{section}")]]))
    await state.clear()

@dp.callback_query(F.data.startswith("skip_ielts_"))
async def skip_ielts(callback: types.CallbackQuery, state: FSMContext):
    section=callback.data[11:]; await state.clear()
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer("⏭ O'tkazib yuborildi.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"➡️ Keyingi {section.upper()}",callback_data=f"ielts_{section}")]]))
    await callback.answer()

# ═══════════════ AI CHAT ═══════════════
@dp.message(F.text=="🤖 AI Chat")
async def ai_chat_start(message: types.Message, state: FSMContext):
    cs=await state.get_state()
    busy=[UserStates.answering_open.state,UserStates.answering_premium.state,UserStates.answering_ielts.state]
    if cs in busy:
        await message.answer("⚠️ Avval joriy savolingizga javob bering!"); return
    user=db.get_user(message.from_user.id); coins=round(user[3],1) if user else 0
    if coins<=0:
        await message.answer(f"❌ <b>AI Chat ishlamaydi!</b>\n\n💰 Coinlaringiz: <b>{coins}</b>\n\nAvval savollarga javob berib coin to'plang!",parse_mode="HTML"); return
    await state.set_state(UserStates.ai_chat); await state.update_data(chat_history=[])
    await message.answer(f"🤖 <b>AI Chat</b>\n\n💰 Coinlaringiz: <b>{coins}</b>\n💸 Narx: har 15 belgi = 1 coin\n\nSavolingizni yozing!\n<i>Chiqish: /stop</i>",
        parse_mode="HTML",reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🚪 AI Chatdan chiqish")]],resize_keyboard=True))

@dp.message(F.text=="🚪 AI Chatdan chiqish")
async def ai_chat_exit(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 AI Chatdan chiqdingiz!",reply_markup=main_menu(message.from_user.id))

@dp.message(UserStates.ai_chat)
async def handle_ai_chat(message: types.Message, state: FSMContext):
    if not message.text: return
    uid=message.from_user.id; ut=message.text.strip()
    for word in ILLEGAL_WORDS:
        if word in ut.lower():
            db.add_coins(uid,-10); user=db.get_user(uid)
            await message.answer(f"🚫 <b>JARIMA!</b>\n\n❌ -10 coin\n💰 Qoldi: <b>{round(user[3],1) if user else 0}</b>",parse_mode="HTML"); return
    user=db.get_user(uid); coins=round(user[3],1) if user else 0
    if coins<=0:
        await state.clear()
        await message.answer("❌ <b>Coinlaringiz tugadi!</b>",parse_mode="HTML",reply_markup=main_menu(uid)); return
    data=await state.get_data(); history=data.get("chat_history",[])
    await message.answer("⏳ AI o'ylayapti...")
    ai_reply=await ai_chat_req(history,ut)
    cost=max(1,len(ai_reply)//15)
    if coins<cost:
        await state.update_data(pending_reply=ai_reply,pending_cost=cost,chat_history=history)
        await state.set_state(UserStates.ai_chat_confirm_debt)
        kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Ha, qarz olaman",callback_data="ai_debt_yes")],[InlineKeyboardButton(text="❌ Yo'q",callback_data="ai_debt_no")]])
        await message.answer(f"⚠️ <b>Coin yetarli emas!</b>\n\n💰 Sizda: <b>{coins}</b>\n💸 Kerak: <b>{cost}</b>\n\nQarz olasizmi?",parse_mode="HTML",reply_markup=kb); return
    db.add_coins(uid,-cost); user=db.get_user(uid); coins_left=round(user[3],1) if user else 0
    history.append({"role":"user","content":ut}); history.append({"role":"assistant","content":ai_reply})
    await state.update_data(chat_history=history); await state.set_state(UserStates.ai_chat)
    await message.answer(f"🤖 {ai_reply}\n\n💰 -{cost} coin  |  Qoldi: <b>{coins_left}</b>",parse_mode="HTML")

@dp.callback_query(F.data=="ai_debt_yes")
async def ai_debt_yes(callback: types.CallbackQuery, state: FSMContext):
    data=await state.get_data()
    ai_reply,cost,history=data.get("pending_reply",""),data.get("pending_cost",0),data.get("chat_history",[])
    uid=callback.from_user.id; db.add_coins(uid,-cost); user=db.get_user(uid)
    coins_left=round(user[3],1) if user else 0
    history.append({"role":"assistant","content":ai_reply})
    await state.update_data(chat_history=history); await state.set_state(UserStates.ai_chat)
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer(f"🤖 {ai_reply}\n\n💰 -{cost} coin  |  Qoldi: <b>{coins_left}</b>",parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data=="ai_debt_no")
async def ai_debt_no(callback: types.CallbackQuery, state: FSMContext):
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer("❌ Bekor qilindi.")
    await state.set_state(UserStates.ai_chat); await callback.answer()

# ═══════════════ REYTING / PROFIL / YORDAM ═══════════════
@dp.message(F.text=="🏆 Reyting")
async def show_leaderboard(message: types.Message):
    top=db.get_leaderboard(10)
    if not top:
        await message.answer("😔 Hali hech kim reyting ro'yxatida yo'q!"); return
    try: await bot.send_sticker(message.chat.id,sticker=STICKER_LEADERBOARD)
    except: pass
    medals=["🥇","🥈","🥉"]
    text="🏆 <b>Global Reyting — Top 10</b>\n\n"
    for i,(uid,fname,uname,coins) in enumerate(top):
        medal=medals[i] if i<3 else f"{i+1}."
        name=fname or uname or f"User{uid}"
        text+=f"{medal} <b>{name}</b> — {round(coins,1)} coin\n"
    rank=db.get_user_rank(message.from_user.id)
    text+=f"\n📍 Sizning o'rningiz: <b>#{rank}</b>"
    await message.answer(text,parse_mode="HTML")
    rs=get_rank_sticker(rank)
    if rs:
        try:
            await bot.send_sticker(message.chat.id,sticker=rs)
            msgs={1:"🎉 BIRINCHI O'RIN!",2:"🎉 IKKINCHI O'RIN!",3:"🎉 UCHINCHI O'RIN!"}
            await message.answer(f"<b>{msgs.get(rank,f'🎉 Top {rank} da turibsiz!')}</b>",parse_mode="HTML")
        except: pass

@dp.message(F.text=="👤 Profilim")
async def show_profile(message: types.Message):
    user=db.get_user(message.from_user.id)
    if not user:
        await message.answer("Profil topilmadi!"); return
    uid,username,fname,coins,total_ans,correct_ans,streak,max_streak,join_date=user
    rank=db.get_user_rank(uid)
    accuracy=round((correct_ans/total_ans*100),1) if total_ans>0 else 0
    ref_count=db.get_ref_count(uid)
    me=await bot.get_me()
    ref_link=f"https://t.me/{me.username}?start=ref{uid}"
    sub_status="\n🛡 <b>Yordamchi Admin</b>" if is_sub_admin(uid) else ""
    await message.answer(
        f"👤 <b>Profil — {fname}</b>{sub_status}\n\n"
        f"💰 Coinlar: <b>{round(coins,1)}</b>\n🏆 Reyting: <b>#{rank}</b>\n"
        f"🔥 Streak: <b>{streak}</b>  ⚡ Max: <b>{max_streak}</b>\n"
        f"📝 Javob: <b>{total_ans}</b>  ✅ To'g'ri: <b>{correct_ans}</b>\n"
        f"🎯 Aniqlik: <b>{accuracy}%</b>\n📅 Qo'shilgan: <b>{join_date[:10]}</b>\n\n"
        f"👥 Taklif qilinganlar: <b>{ref_count} ta</b>\n"
        f"🔗 Referal havola:\n<code>{ref_link}</code>",
        parse_mode="HTML")

@dp.message(F.text=="ℹ️ Yordam")
async def show_help(message: types.Message):
    await message.answer(
        "ℹ️ <b>BilimChallenge — Yordam</b>\n\n"
        "🎯 Savol olish — kategoriya va tur tanlang\n"
        "🎓 IELTS — AI bilan mashq qiling\n"
        "🤖 AI Chat — coinlar evaziga AI bilan suhbat\n"
        "🏆 Reyting — Top 10\n"
        "👥 Do'stni taklif qil — har biri uchun +30 coin!\n\n"
        "💰 To'g'ri javob — coin\n"
        "❌ Noto'g'ri — 30% jarima\n"
        "⏰ Vaqt tugasa — 45% jarima\n"
        "🔥x3=1.5x  🔥🔥x5=2.0x  🔥🔥🔥x10=3.0x\n"
        "🟢Oson=30s  🟡O'rta=60s  🔴Qiyin=90s",
        parse_mode="HTML")

@dp.message(F.text=="📝 Taklif/Shikoyat")
async def feedback_start(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.sending_feedback)
    await message.answer("📝 <b>Taklif yoki shikoyatingizni yozing:</b>\n\n<i>/cancel — bekor qilish</i>",parse_mode="HTML")

@dp.message(UserStates.sending_feedback)
async def receive_feedback(message: types.Message, state: FSMContext):
    user=message.from_user
    db.save_feedback(user.id, user.first_name or "", user.username or "", message.text)
    await state.clear()
    await message.answer("✅ <b>Xabaringiz adminga yuborildi!</b>",parse_mode="HTML",reply_markup=main_menu(user.id))

# ═══════════════ ADMIN PANEL (BOSH ADMIN) ═══════════════
@dp.message(F.text=="⚙️ Admin Panel")
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("⚙️ <b>Admin Panel</b>",parse_mode="HTML",reply_markup=admin_menu())

@dp.message(F.text=="🔙 Asosiy menyu")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Asosiy menyu",reply_markup=main_menu(message.from_user.id))

@dp.message(F.text=="💬 Takliflar")
async def show_feedbacks(message: types.Message):
    if not is_admin(message.from_user.id): return
    feedbacks=db.get_feedbacks(20)
    if not feedbacks:
        await message.answer("💬 Hali taklif yo'q."); return
    for fb in feedbacks[:10]:
        fb_id,user_id,fname,username,fb_text,fb_date,is_read=fb
        read_icon="🆕" if not is_read else "✅"
        uname=f"@{username}" if username else f"ID:{user_id}"
        await message.answer(f"{read_icon} <b>#{fb_id}</b> — {fname} ({uname})\n📅 {fb_date[:10]}\n\n{fb_text}",
            parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💬 Javob",callback_data=f"reply_fb_{fb_id}"),
                InlineKeyboardButton(text="🗑 O'chirish",callback_data=f"del_fb_{fb_id}")]]))
    await message.answer(f"Jami: <b>{len(feedbacks)}</b> ta",parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Barchasini tozalash",callback_data="mark_all_read")]]))

@dp.callback_query(F.data.startswith("reply_fb_"))
async def admin_reply_fb(callback: types.CallbackQuery, state: FSMContext):
    if not is_any_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!"); return
    fb_id=int(callback.data[9:])
    await state.update_data(reply_fb_id=fb_id)
    await state.set_state(AdminStates.fb_reply_text)
    await callback.message.answer(f"💬 #{fb_id} ga javob yozing:")
    await callback.answer()

@dp.message(AdminStates.fb_reply_text)
async def save_fb_reply(message: types.Message, state: FSMContext):
    data=await state.get_data(); fb_id=data["reply_fb_id"]
    fb=db.get_feedback_by_id(fb_id)
    if fb:
        user_id=fb[1]; db.save_feedback_reply(fb_id, message.text)
        try: await bot.send_message(user_id,f"📩 <b>Taklifingizga javob:</b>\n\n{message.text}",parse_mode="HTML")
        except: pass
    await state.clear()
    await message.answer("✅ Javob yuborildi!",reply_markup=admin_menu())

@dp.callback_query(F.data.startswith("del_fb_"))
async def delete_feedback_cb(callback: types.CallbackQuery):
    db.delete_feedback(int(callback.data[7:]))
    await callback.message.edit_text("🗑 O'chirildi.")
    await callback.answer()

@dp.callback_query(F.data=="mark_all_read")
async def mark_all_read(callback: types.CallbackQuery):
    db.mark_feedbacks_read()
    await callback.message.edit_text("✅ Tozalandi!")
    await callback.answer()

@dp.message(F.text=="📂 Kategoriyalar")
async def manage_categories(message: types.Message):
    if not is_admin(message.from_user.id): return
    cats=db.get_categories_with_count()
    text="📂 <b>Kategoriyalar</b>\n\n"
    for cat,count in cats: text+=f"• <b>{cat}</b> — {count} ta\n"
    if not cats: text+="Hali kategoriya yo'q"
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ Yangi",callback_data="add_category")],[InlineKeyboardButton(text="🗑 O'chirish",callback_data="del_category_list")]])
    await message.answer(text,parse_mode="HTML",reply_markup=kb)

@dp.callback_query(F.data=="add_category")
async def add_cat_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_new_category)
    await callback.message.answer("📂 Yangi kategoriya nomini kiriting:")
    await callback.answer()

@dp.message(AdminStates.waiting_new_category)
async def save_new_category(message: types.Message, state: FSMContext):
    db.add_category(message.text.strip()); await state.clear()
    await message.answer(f"✅ <b>{message.text.strip()}</b> qo'shildi!",parse_mode="HTML",reply_markup=admin_menu())

@dp.callback_query(F.data=="del_category_list")
async def del_cat_list(callback: types.CallbackQuery):
    cats=db.get_categories()
    if not cats:
        await callback.answer("Kategoriya yo'q!",show_alert=True); return
    buttons=[[InlineKeyboardButton(text=f"🗑 {c}",callback_data=f"delcat_{c}")] for c in cats]
    await callback.message.answer("Qaysi kategoriyani o'chirish?",reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("delcat_"))
async def delete_category_cb(callback: types.CallbackQuery):
    cat=callback.data[7:]; db.delete_category(cat)
    await callback.message.edit_text(f"✅ <b>{cat}</b> o'chirildi!",parse_mode="HTML")
    await callback.answer()

@dp.message(F.text=="📊 Statistika")
async def show_stats(message: types.Message):
    if not is_admin(message.from_user.id): return
    s=db.get_stats(); subs=db.get_all_sub_admins()
    await message.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: {s['users']}\n❓ Savollar: {s['questions']}\n"
        f"📝 Javoblar: {s['answers']}\n✅ To'g'ri: {s['correct']}\n"
        f"🎯 Aniqlik: {s['accuracy']}%\n🛡 Yordamchi adminlar: {len(subs)}",
        parse_mode="HTML")

@dp.message(F.text=="👥 Foydalanuvchilar")
async def list_users(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer(f"👥 <b>Foydalanuvchilar</b>\n\nJami: <b>{db.get_total_users()}</b>\nFaol: <b>{db.get_active_users()}</b>",parse_mode="HTML")

@dp.message(F.text=="📢 Xabar yuborish")
async def broadcast_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdminStates.broadcast_text)
    await message.answer("📢 Xabar matnini kiriting:\n<i>/cancel — bekor qilish</i>",parse_mode="HTML")

@dp.message(AdminStates.broadcast_text)
async def broadcast_get_text(message: types.Message, state: FSMContext):
    await state.update_data(broadcast_text=message.text)
    await state.set_state(AdminStates.broadcast_image)
    await message.answer("🖼 Rasm (ixtiyoriy) yoki <b>'-'</b>:",parse_mode="HTML")

@dp.message(AdminStates.broadcast_image)
async def broadcast_send(message: types.Message, state: FSMContext):
    data=await state.get_data(); text=data["broadcast_text"]
    image_id=message.photo[-1].file_id if message.photo else ("" if message.text and message.text.strip()=="-" else (message.text or ""))
    await state.update_data(broadcast_image=image_id)
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📢 Yuborish",callback_data="confirm_broadcast"),InlineKeyboardButton(text="❌ Bekor",callback_data="cancel_broadcast")]])
    await message.answer(f"📢 <b>Xabar:</b>\n\n{text}\n\n🖼 {'Ha' if image_id else 'Yoq'}\n\nYuborilsinmi?",parse_mode="HTML",reply_markup=kb)

@dp.callback_query(F.data=="confirm_broadcast")
async def do_broadcast(callback: types.CallbackQuery, state: FSMContext):
    data=await state.get_data(); text,image_id=data["broadcast_text"],data.get("broadcast_image","")
    users=db.get_all_user_ids()
    await callback.message.edit_text(f"📢 Yuborilmoqda... ({len(users)} ta)")
    success=failed=0
    for uid in users:
        try:
            if image_id: await bot.send_photo(uid,photo=image_id,caption=text,parse_mode="HTML")
            else: await bot.send_message(uid,text,parse_mode="HTML")
            success+=1
        except: failed+=1
        await asyncio.sleep(0.05)
    await state.clear()
    await callback.message.answer(f"✅ {success} ta\n❌ {failed} ta",reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query(F.data=="cancel_broadcast")
async def cancel_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor.")
    await callback.message.answer("⚙️ Admin Panel",reply_markup=admin_menu())
    await callback.answer()

# ═══════════════ SAVOLLAR (ADMIN QO'SHISH/TAHRIRLASH) ═══════════════
@dp.message(F.text=="📋 Savollar ro'yxati")
async def list_questions(message: types.Message):
    if not is_admin(message.from_user.id): return
    questions=db.get_all_questions()
    if not questions:
        await message.answer("😔 Savollar yo'q."); return
    text=f"📋 <b>Jami: {len(questions)} ta</b>\n\n"
    for q in questions[:20]:
        q_id,q_text,q_type,_,_,coins,category,difficulty=q
        short=q_text[:30]+"..." if len(q_text)>30 else q_text
        text+=f"#{q_id} {DIFFICULTY_ICONS.get(difficulty,'🟡')} [{category}] {short} ({coins}💰)\n"
    if len(questions)>20: text+=f"\n...va yana {len(questions)-20} ta"
    await message.answer(text,parse_mode="HTML")

@dp.message(F.text=="🗑 Savol o'chirish")
async def delete_prompt(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("🗑 O'chiriladigan savol ID sini yuboring:")

@dp.message(F.text=="✏️ Savol tahrirlash")
async def edit_prompt(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("✏️ Tahrirlanadigan savol ID sini yuboring:")

@dp.message(F.text.regexp(r'^\d+$'))
async def handle_id_input(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    q_id=int(message.text); q=db.get_question_by_id(q_id)
    if not q:
        await message.answer(f"❌ #{q_id} topilmadi."); return
    _,q_text,q_type,options,correct,coins,cat,diff,explanation,image_id,tl=q
    short=q_text[:60]+"..." if len(q_text)>60 else q_text
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 O'chirish",callback_data=f"del_{q_id}"),InlineKeyboardButton(text="❌ Bekor",callback_data="del_cancel")],
        [InlineKeyboardButton(text="✏️ Savol matnini o'zgartir",callback_data=f"edf_{q_id}_text")],
        [InlineKeyboardButton(text="📋 Variantlarni o'zgartir",callback_data=f"edf_{q_id}_options")],
        [InlineKeyboardButton(text="✅ To'g'ri javobni o'zgartir",callback_data=f"edf_{q_id}_correct")],
        [InlineKeyboardButton(text="💰 Coinni o'zgartir",callback_data=f"edf_{q_id}_coins")],
        [InlineKeyboardButton(text="💡 Tavsifni o'zgartir",callback_data=f"edf_{q_id}_explanation")],
        [InlineKeyboardButton(text="📂 Kategoriyani o'zgartir",callback_data=f"edf_{q_id}_category")],
        [InlineKeyboardButton(text="⏰ Vaqt limitini o'zgartir",callback_data=f"edf_{q_id}_time_limit")],
        [InlineKeyboardButton(text="🖼 Rasmni o'zgartir",callback_data=f"edf_{q_id}_image_id")]])
    await message.answer(f"#{q_id} {DIFFICULTY_ICONS.get(diff,'🟡')} [{cat}]\n❓ {short}\n💰 {coins} coin\nTur: {q_type}",reply_markup=kb)

@dp.callback_query(F.data.startswith("edf_"))
async def edit_field(callback: types.CallbackQuery, state: FSMContext):
    parts=callback.data.split("_"); q_id,field=int(parts[1]),parts[2]
    await state.update_data(edit_q_id=q_id,edit_field=field)
    await state.set_state(AdminStates.editing_field)
    q=db.get_question_by_id(q_id); cv={}
    if q:
        _,q_text,q_type,options,correct,coins,cat,diff,explanation,image_id,tl=q
        cv={"text":q_text,"options":options.replace("|","\n") if options else "","correct":correct,
            "coins":str(coins),"explanation":explanation or "Yo'q","category":cat,
            "time_limit":tl or "Yo'q","image_id":"Bor ✅" if image_id else "Yo'q"}
    current=cv.get(field,"")
    prompts={"text":f"✏️ Hozirgi:\n<i>{current[:200]}</i>\n\nYangi matnni kiriting:",
             "options":f"📋 Hozirgi:\n<i>{current}</i>\n\nYangi variantlarni kiriting:",
             "correct":f"✅ Hozirgi: <i>{current}</i>\n\nYangi javobni kiriting:",
             "coins":f"💰 Hozirgi: <i>{current}</i>\n\nYangi miqdorni kiriting:",
             "explanation":f"💡 Hozirgi: <i>{current}</i>\n\nYangi tavsifni kiriting ('-' = o'chirish):",
             "category":f"📂 Hozirgi: <i>{current}</i>\n\nYangi kategoriyani kiriting:",
             "time_limit":f"⏰ Hozirgi: <i>{current}</i>\n\nYangi vaqtni kiriting ('-' = o'chirish):",
             "image_id":f"🖼 Rasm: <i>{current}</i>\n\nRasm yuboring yoki URL kiriting ('-' = o'chirish):"}
    await callback.message.answer(prompts.get(field,"Yangi qiymat:"),parse_mode="HTML")
    await callback.answer()

@dp.message(AdminStates.editing_field)
async def save_edit(message: types.Message, state: FSMContext):
    data=await state.get_data(); q_id,field=data["edit_q_id"],data["edit_field"]
    if field=="image_id":
        value=message.photo[-1].file_id if message.photo else ("" if message.text.strip()=="-" else message.text.strip())
    elif field=="coins":
        if not message.text.replace(".","").isdigit():
            await message.answer("⚠️ Faqat raqam!"); return
        value=float(message.text)
    elif field=="options":
        value="|".join([o.strip() for o in message.text.split("\n") if o.strip()])
    elif field in ("explanation","time_limit"):
        value="" if message.text.strip()=="-" else message.text.strip()
    else: value=message.text.strip()
    db.update_question_field(q_id,field,value)
    await state.clear()
    await message.answer(f"✅ #{q_id} yangilandi!",reply_markup=admin_menu())

@dp.callback_query(F.data.startswith("del_"))
async def confirm_delete(callback: types.CallbackQuery):
    if callback.data=="del_cancel":
        await callback.message.edit_text("❌ Bekor qilindi."); await callback.answer(); return
    q_id=int(callback.data.split("_")[1]); db.delete_question(q_id)
    await callback.message.edit_text(f"✅ #{q_id} o'chirildi!")
    await callback.answer()

@dp.message(F.text=="➕ Savol qo'shish")
async def add_question_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear(); await state.set_state(AdminStates.waiting_question_type)
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Test (A,B,C,D)",callback_data="qtype_test")],
        [InlineKeyboardButton(text="✍️ Ochiq savol",callback_data="qtype_open")],
        [InlineKeyboardButton(text="⭐ Premium savol",callback_data="qtype_premium")],
        [InlineKeyboardButton(text="📝 IELTS Writing",callback_data="qtype_writing")],
        [InlineKeyboardButton(text="✍️ IELTS Essay",callback_data="qtype_essay")],
        [InlineKeyboardButton(text="📖 IELTS Reading",callback_data="qtype_reading")],
        [InlineKeyboardButton(text="🗣 IELTS Speaking",callback_data="qtype_speaking")],
        [InlineKeyboardButton(text="🎧 IELTS Listening",callback_data="qtype_listening")]])
    await message.answer("📌 Savol turini tanlang:",reply_markup=kb)

@dp.callback_query(F.data.startswith("qtype_"))
async def choose_qtype(callback: types.CallbackQuery, state: FSMContext):
    qtype=callback.data[6:]
    await state.update_data(q_type=qtype); await state.set_state(AdminStates.waiting_question_text)
    await callback.message.edit_text("✏️ Savol matnini kiriting:")
    await callback.answer()

@dp.message(AdminStates.waiting_question_text)
async def get_question_text(message: types.Message, state: FSMContext):
    data=await state.get_data(); qtype=data["q_type"]
    if message.text and message.text.strip()=="/done":
        accumulated=data.get("accumulated_text","")
        if not accumulated:
            await message.answer("⚠️ Avval matn yuboring!"); return
        await state.update_data(q_text=accumulated)
        if qtype=="reading":
            await state.set_state(AdminStates.waiting_correct_answer)
            await message.answer("✅ To'g'ri javoblarni kiriting (har biri yangi qatorda):")
        elif qtype in IELTS_TYPES:
            await state.update_data(correct="",options="")
            await state.set_state(AdminStates.waiting_coin_reward)
            await message.answer("💰 Bu savol uchun necha coin?")
        else:
            await state.set_state(AdminStates.waiting_correct_answer)
            await message.answer("✅ To'g'ri javobni kiriting:")
        return
    if qtype in ["reading"]+IELTS_TYPES:
        prev=data.get("accumulated_text","")
        new_text=(prev+"\n"+message.text).strip() if prev else message.text
        await state.update_data(accumulated_text=new_text)
        await message.answer(f"✅ Qabul qilindi ({len(new_text)} belgi)\n\nDavom eting yoki <b>/done</b> yozing",parse_mode="HTML")
        return
    await state.update_data(q_text=message.text)
    if qtype=="test":
        await state.set_state(AdminStates.waiting_options)
        await message.answer("📋 Variantlarni kiriting (har biri yangi qatorda):")
    else:
        await state.set_state(AdminStates.waiting_correct_answer)
        await message.answer("✅ To'g'ri javobni kiriting:")

@dp.message(AdminStates.waiting_options)
async def get_options(message: types.Message, state: FSMContext):
    options=[o.strip() for o in message.text.split("\n") if o.strip()]
    if len(options)<2:
        await message.answer("⚠️ Kamida 2 ta variant!"); return
    await state.update_data(options="|".join(options))
    await state.set_state(AdminStates.waiting_correct_answer)
    opts_text="\n".join([f"{chr(65+i)}. {opt}" for i,opt in enumerate(options)])
    await message.answer(f"📋 Variantlar:\n{opts_text}\n\n✅ To'g'ri variant harfini kiriting (A/B/C/D):")

@dp.message(AdminStates.waiting_correct_answer)
async def get_correct_answer(message: types.Message, state: FSMContext):
    await state.update_data(correct=message.text.strip())
    await state.set_state(AdminStates.waiting_coin_reward)
    await message.answer("💰 Necha coin?")

@dp.message(AdminStates.waiting_coin_reward)
async def get_coins(message: types.Message, state: FSMContext):
    if not message.text.replace(".","").isdigit():
        await message.answer("⚠️ Faqat raqam!"); return
    await state.update_data(coins=float(message.text))
    data=await state.get_data(); qtype=data["q_type"]
    if qtype in IELTS_TYPES+["premium"]:
        await state.set_state(AdminStates.waiting_time_limit)
        await message.answer("⏰ Vaqtni kiriting (masalan: 20 daqiqa)\n<i>Kerak bo'lmasa '-' yozing</i>",parse_mode="HTML")
    else:
        await state.set_state(AdminStates.waiting_difficulty)
        kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🟢 Oson",callback_data="diff_oson")],[InlineKeyboardButton(text="🟡 O'rta",callback_data="diff_orta")],[InlineKeyboardButton(text="🔴 Qiyin",callback_data="diff_qiyin")]])
        await message.answer("📊 Qiyinlik darajasi:",reply_markup=kb)

@dp.message(AdminStates.waiting_time_limit)
async def get_time_limit(message: types.Message, state: FSMContext):
    tl="" if message.text.strip()=="-" else message.text.strip()
    await state.update_data(time_limit=tl,difficulty="orta")
    data=await state.get_data(); qtype=data["q_type"]
    if qtype in IELTS_TYPES:
        await state.update_data(category=qtype.upper())
        await state.set_state(AdminStates.waiting_explanation)
        await message.answer("💡 Tavsif (ixtiyoriy):\n<i>'-' = kerak emas</i>",parse_mode="HTML")
    else:
        await state.set_state(AdminStates.waiting_category)
        cats=db.get_categories(); buttons=[]; row=[]
        for cat in cats:
            row.append(InlineKeyboardButton(text=cat,callback_data=f"selcat_{cat}"))
            if len(row)==2: buttons.append(row); row=[]
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton(text="➕ Yangi kategoriya",callback_data="selcat_NEW")])
        await message.answer("📂 Kategoriyani tanlang:",reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("diff_"))
async def get_difficulty(callback: types.CallbackQuery, state: FSMContext):
    difficulty=callback.data.split("_")[1]
    await state.update_data(difficulty=difficulty,time_limit="")
    await state.set_state(AdminStates.waiting_category)
    cats=db.get_categories(); buttons=[]; row=[]
    for cat in cats:
        row.append(InlineKeyboardButton(text=cat,callback_data=f"selcat_{cat}"))
        if len(row)==2: buttons.append(row); row=[]
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="➕ Yangi kategoriya",callback_data="selcat_NEW")])
    await callback.message.edit_text("📂 Kategoriyani tanlang:",reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("selcat_"))
async def select_category(callback: types.CallbackQuery, state: FSMContext):
    cat=callback.data[7:]
    if cat=="NEW":
        await callback.message.edit_text("📂 Yangi kategoriya nomini kiriting:")
        await callback.answer(); return
    await state.update_data(category=cat)
    await state.set_state(AdminStates.waiting_explanation)
    await callback.message.edit_text("💡 Tavsif:\n<i>'-' = kerak emas</i>",parse_mode="HTML")
    await callback.answer()

@dp.message(AdminStates.waiting_category)
async def get_new_category(message: types.Message, state: FSMContext):
    db.add_category(message.text.strip())
    await state.update_data(category=message.text.strip())
    await state.set_state(AdminStates.waiting_explanation)
    await message.answer("💡 Tavsif:\n<i>'-' = kerak emas</i>",parse_mode="HTML")

@dp.message(AdminStates.waiting_explanation)
async def get_explanation(message: types.Message, state: FSMContext):
    explanation="" if message.text.strip()=="-" else message.text.strip()
    await state.update_data(explanation=explanation)
    await state.set_state(AdminStates.waiting_image)
    await message.answer("🖼 Rasm (ixtiyoriy):\n• Rasm yuklang  • URL yuboring  • <b>'-'</b> = kerak emas",parse_mode="HTML")

@dp.message(AdminStates.waiting_image)
async def get_image(message: types.Message, state: FSMContext):
    image_id=""
    if message.text and message.text.strip()=="-": image_id=""
    elif message.photo: image_id=message.photo[-1].file_id
    elif message.text and message.text.startswith("http"): image_id=message.text.strip()
    await state.update_data(image_id=image_id)
    data=await state.get_data()
    diff_icon=DIFFICULTY_ICONS.get(data.get("difficulty","orta"),"🟡")
    options_display=""
    if data["q_type"]=="test":
        opts=data.get("options","").split("|")
        options_display="\n"+"\n".join([f"  {chr(65+i)}. {opt}" for i,opt in enumerate(opts)])
        options_display+=f"\n✅ To'g'ri: {data['correct'].upper()}"
    elif data["q_type"] not in IELTS_TYPES:
        options_display=f"\n✅ Javob: {data['correct']}"
    tl_info=f"\n⏰ {data.get('time_limit','')}" if data.get("time_limit") else ""
    confirm=(f"📋 <b>Tekshiring:</b>\n\nTur: {data['q_type'].upper()}\n"
             f"❓ {data['q_text'][:200]}{options_display}\n"
             f"💰 {data['coins']} coin\n{diff_icon} {DIFFICULTY_NAMES.get(data.get('difficulty','orta'))}\n"
             f"📂 {data.get('category','')}{tl_info}\n🖼 {'Ha' if image_id else 'Yoq'}\n\nSaqlash?")
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Saqlash",callback_data="save_question"),InlineKeyboardButton(text="❌ Bekor",callback_data="cancel_question")]])
    await message.answer(confirm,parse_mode="HTML",reply_markup=kb)

@dp.callback_query(F.data=="save_question")
async def save_question_cb(callback: types.CallbackQuery, state: FSMContext):
    data=await state.get_data()
    db.add_question(text=data["q_text"],q_type=data["q_type"],options=data.get("options",""),
        correct=data.get("correct",""),coins=data["coins"],category=data.get("category","Umumiy"),
        difficulty=data.get("difficulty","orta"),explanation=data.get("explanation",""),
        image_id=data.get("image_id",""),time_limit=data.get("time_limit",""))
    await state.clear()
    await callback.message.edit_text("✅ <b>Savol saqlandi!</b>",parse_mode="HTML")
    await callback.message.answer("⚙️ Admin Panel",reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query(F.data=="cancel_question")
async def cancel_question(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.message.answer("⚙️ Admin Panel",reply_markup=admin_menu())
    await callback.answer()

# ═══════════════ KUTAYOTGAN SAVOLLAR (ADMIN TASDIQLASH) ═══════════════
@dp.message(F.text=="⏳ Kutayotgan savollar")
async def pending_questions_list(message: types.Message):
    if not is_admin(message.from_user.id): return
    pqs=db.get_pending_questions()
    if not pqs:
        await message.answer("✅ Kutayotgan savollar yo'q."); return
    await message.answer(f"⏳ <b>Kutayotgan savollar: {len(pqs)} ta</b>",parse_mode="HTML")
    for pq in pqs[:10]:
        pq_id,sub_id,text,q_type,options,correct,coins,cat,diff,explanation,img,tl,created,status=pq
        short=text[:80]+"..." if len(text)>80 else text
        kb=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Tasdiqlash",callback_data=f"appr_pq_{pq_id}"),
            InlineKeyboardButton(text="❌ Rad etish",callback_data=f"rej_pq_{pq_id}")]])
        await message.answer(
            f"🆔 #{pq_id} | {q_type.upper()} | {DIFFICULTY_ICONS.get(diff,'🟡')}\n📂 {cat} | 💰 {coins}\n❓ {short}\n👤 Sub-admin: {sub_id}",
            parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("appr_pq_"))
async def approve_pq(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!"); return
    pq_id=int(callback.data[8:])
    pq=db.get_pending_question_by_id(pq_id)
    if pq:
        db.approve_pending_question(pq_id); sub_id=pq[1]
        try: await bot.send_message(sub_id,"✅ <b>Savolingiz tasdiqlandi va faollashtirildi!</b>",parse_mode="HTML")
        except: pass
    await callback.message.edit_text("✅ Savol tasdiqlandi!")
    await callback.answer()

@dp.callback_query(F.data.startswith("rej_pq_"))
async def reject_pq(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!"); return
    pq_id=int(callback.data[7:])
    pq=db.get_pending_question_by_id(pq_id)
    if pq:
        db.reject_pending_question(pq_id); sub_id=pq[1]
        try: await bot.send_message(sub_id,"❌ <b>Savolingiz rad etildi.</b>\nQayta ko'rib chiqing.",parse_mode="HTML")
        except: pass
    await callback.message.edit_text("❌ Savol rad etildi.")
    await callback.answer()

# ═══════════════ YORDAMCHI ADMINLAR BOSHQARUVI ═══════════════
@dp.message(F.text=="🛡 Yordamchi Adminlar")
async def sub_admins_list(message: types.Message):
    if not is_admin(message.from_user.id): return
    subs=db.get_all_sub_admins()
    if not subs: text="🛡 <b>Yordamchi adminlar yo'q</b>"
    else:
        text="🛡 <b>Yordamchi Adminlar</b>\n\n"
        for s in subs:
            uid,uname,fname,elected,term_end,salary,last_report,rep_count,warnings,is_active=s
            text+=(f"👤 {fname} (@{uname or uid})\n"
                   f"   💰 Moash: {salary} coin\n   📝 Hisobotlar: {rep_count}\n"
                   f"   ⚠️ Ogohlantirishlar: {warnings}\n"
                   f"   ⏳ Muddat: {term_end[:10] if term_end else '?'}\n\n")
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Qo'shish",callback_data="add_sub_admin")],
        [InlineKeyboardButton(text="❌ O'chirish",callback_data="remove_sub_admin")],
        [InlineKeyboardButton(text="💰 Moash belgilash",callback_data="set_sub_salary")]])
    await message.answer(text,parse_mode="HTML",reply_markup=kb)

@dp.callback_query(F.data.startswith("add_sub_admin"))
async def cb_add_sub_admin(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.update_data(sub_action="add")
    await state.set_state(AdminStates.sub_admin_select)
    await callback.message.answer("👤 Yordamchi admin qilmoqchi bo'lgan foydalanuvchi <b>user_id</b>:")
    await callback.answer()

@dp.callback_query(F.data=="remove_sub_admin")
async def cb_remove_sub_admin(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.update_data(sub_action="remove")
    await state.set_state(AdminStates.sub_admin_select)
    await callback.message.answer("👤 O'chirmoqchi bo'lgan yordamchi admin <b>user_id</b>:")
    await callback.answer()

@dp.callback_query(F.data=="set_sub_salary")
async def cb_set_salary(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.update_data(sub_action="salary")
    await state.set_state(AdminStates.sub_admin_select)
    await callback.message.answer("👤 Moash belgilamoqchi bo'lgan yordamchi admin <b>user_id</b>:")
    await callback.answer()

@dp.message(AdminStates.sub_admin_select)
async def handle_sub_admin_select(message: types.Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("⚠️ Faqat raqam (user_id)!"); return
    target_id=int(message.text); data=await state.get_data(); action=data["sub_action"]
    if action=="add":
        user=db.get_user(target_id)
        if not user:
            await message.answer("❌ Bu foydalanuvchi topilmadi!"); return
        db.add_sub_admin(target_id, user[1], user[2])
        try:
            await bot.send_message(target_id,
                "🎉 <b>Tabriklaymiz! Siz Yordamchi Admin etib tayinlandingiz!</b>\n\n"
                "🛡 Asosiy menyudan <b>Yordamchi Admin Panel</b>ga kiring.\n"
                f"⏳ Lavozim muddati: {SUB_ADMIN_TERM_DAYS} kun\n\n"
                "📋 Vazifalar:\n• Savol tuzish (admin tasdiqlaydi)\n• Har 3 kunda hisobot\n• Takliflarga javob",
                parse_mode="HTML")
        except: pass
        await state.clear()
        await message.answer(f"✅ {user[2]} yordamchi admin etib tayinlandi!",reply_markup=admin_menu())
    elif action=="remove":
        db.remove_sub_admin(target_id)
        try: await bot.send_message(target_id,"❌ <b>Siz yordamchi admin lavozimidan olindingiz.</b>",parse_mode="HTML")
        except: pass
        await state.clear()
        await message.answer(f"✅ {target_id} lavozimdan olindi.",reply_markup=admin_menu())
    elif action=="salary":
        await state.update_data(salary_target=target_id)
        await state.set_state(AdminStates.sub_admin_salary)
        await message.answer(f"💰 {target_id} uchun oylik moash miqdori (coin):")

@dp.message(AdminStates.sub_admin_salary)
async def save_sub_salary(message: types.Message, state: FSMContext):
    if not message.text.replace(".","").isdigit():
        await message.answer("⚠️ Faqat raqam!"); return
    data=await state.get_data(); target_id=data["salary_target"]; salary=float(message.text)
    db.set_sub_admin_salary(target_id, salary)
    await state.clear()
    await message.answer(f"✅ {target_id} uchun moash {salary} coin etib belgilandi!",reply_markup=admin_menu())

# ═══════════════ MUKOFOT / JARIMA ═══════════════
@dp.message(F.text=="💰 Mukofot/Jarima")
async def payment_menu(message: types.Message):
    if not is_admin(message.from_user.id): return
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Moash to'lash",callback_data="pay_salary")],
        [InlineKeyboardButton(text="🏆 Mukofot berish",callback_data="pay_bonus")],
        [InlineKeyboardButton(text="⚠️ Jarima solish",callback_data="pay_fine")]])
    await message.answer("💰 <b>Mukofot / Jarima</b>",parse_mode="HTML",reply_markup=kb)

@dp.callback_query(F.data.startswith("pay_"))
async def pay_action(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    action=callback.data[4:]
    await state.update_data(pay_action=action)
    await state.set_state(AdminStates.payment_target)
    labels={"salary":"moash","bonus":"mukofot","fine":"jarima"}
    await callback.message.answer(f"👤 {labels.get(action,action)} beriladigan foydalanuvchi <b>user_id</b>:")
    await callback.answer()

@dp.message(AdminStates.payment_target)
async def payment_get_target(message: types.Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("⚠️ User ID raqam bo'lishi kerak!"); return
    await state.update_data(pay_target=int(message.text))
    await state.set_state(AdminStates.payment_amount)
    await message.answer("💰 Miqdorni kiriting (coin):")

@dp.message(AdminStates.payment_amount)
async def payment_get_amount(message: types.Message, state: FSMContext):
    if not message.text.replace(".","").isdigit():
        await message.answer("⚠️ Faqat raqam!"); return
    await state.update_data(pay_amount=float(message.text))
    await state.set_state(AdminStates.payment_note)
    await message.answer("📝 Izoh yozing (yoki '-'):")

@dp.message(AdminStates.payment_note)
async def payment_do(message: types.Message, state: FSMContext):
    note="" if message.text.strip()=="-" else message.text.strip()
    data=await state.get_data()
    target=data["pay_target"]; amount=data["pay_amount"]; action=data["pay_action"]
    db.add_payment(message.from_user.id, target, amount, action, note)
    if action=="fine":
        notif=f"⚠️ <b>Jarima!</b>\n\n-{amount} coin\nSabab: {note}"
    else:
        label="moash" if action=="salary" else "mukofot"
        notif=f"🎉 <b>Sizga {label} keldi!</b>\n\n+{amount} coin\n{note}"
    try: await bot.send_message(target, notif, parse_mode="HTML")
    except: pass
    await state.clear()
    action_text="jarima solindi" if action=="fine" else "to'landi"
    await message.answer(f"✅ {target} ga {amount} coin {action_text}!\nIzoh: {note}",reply_markup=admin_menu())

# ═══════════════ HISOBOTLAR (ADMIN KO'RISH) ═══════════════
@dp.message(F.text=="📜 Hisobotlar")
async def show_reports(message: types.Message):
    if not is_admin(message.from_user.id): return
    reports=db.get_reports(20)
    if not reports:
        await message.answer("📜 Hali hisobot yo'q."); return
    text="📜 <b>So'nggi hisobotlar</b>\n\n"
    for r in reports[:10]:
        r_id,sub_id,fname,r_text,created=r
        short=r_text[:100]+"..." if len(r_text)>100 else r_text
        text+=f"👤 {fname or sub_id} | 📅 {created[:10]}\n{short}\n\n"
    await message.answer(text,parse_mode="HTML")

# ═══════════════ SAYLOV BOSHQARUVI ═══════════════
@dp.message(F.text=="🗳 Saylov boshqaruvi")
async def election_admin(message: types.Message):
    if not is_admin(message.from_user.id): return
    election=db.get_active_election()
    if election:
        e_id,e_status,started,ends,winner,created=election
        text=f"🗳 <b>Faol saylov #{e_id}</b>\nHolat: {e_status}\nBoshlanish: {started[:10]}\nTugash: {ends[:10]}"
        kb=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Ovoz berishni boshlash",callback_data=f"el_start_vote_{e_id}")],
            [InlineKeyboardButton(text="🏁 Yakunlash",callback_data=f"el_finish_{e_id}")],
            [InlineKeyboardButton(text="📊 Natijalar",callback_data=f"el_results_{e_id}")]])
    else:
        text="🗳 <b>Faol saylov yo'q</b>"
        kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗳 Yangi saylov boshlash",callback_data="el_new")]])
    await message.answer(text,parse_mode="HTML",reply_markup=kb)

@dp.callback_query(F.data=="el_new")
async def start_new_election(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    top10=db.get_top10_users(); e_id=db.create_election(); notified=0
    for uid,fname,uname,coins in top10:
        db.add_candidate(e_id, uid, uname or "", fname or "")
        try:
            kb=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Ha, nomzod bo'laman",callback_data=f"cand_yes_{e_id}_{uid}")],
                [InlineKeyboardButton(text="❌ Yo'q",callback_data=f"cand_no_{e_id}_{uid}")]])
            await bot.send_message(uid,
                f"🏆 <b>Siz Top-10 da ekaniz!</b>\n\n"
                f"Ertaga <b>Yordamchi Admin</b> sayloviga nomzod qo'ya olasiz.\n"
                f"G'olib bo'lsangiz bot boshqaruvida qatnashasiz va oylik moash olasiz!\n\n"
                f"Nomzod bo'lasizmi?",parse_mode="HTML",reply_markup=kb)
            notified+=1
        except: pass
    await callback.message.edit_text(f"🗳 Saylov #{e_id} boshlandi!\n{notified} ta foydalanuvchiga xabar yuborildi.")
    await callback.answer()

@dp.callback_query(F.data.startswith("cand_yes_"))
async def candidate_yes(callback: types.CallbackQuery):
    parts=callback.data.split("_"); e_id,uid=int(parts[2]),int(parts[3])
    if callback.from_user.id!=uid:
        await callback.answer("Bu sizning havolangiz emas!"); return
    db.confirm_candidate(e_id, uid)
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer("✅ <b>Nomzodligingiz tasdiqlandi! Ertaga saylov bo'ladi, omad!</b>",parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("cand_no_"))
async def candidate_no(callback: types.CallbackQuery):
    parts=callback.data.split("_"); e_id,uid=int(parts[2]),int(parts[3])
    if callback.from_user.id!=uid:
        await callback.answer("Bu sizning havolangiz emas!"); return
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer("👍 Tushunildi, keyingi saylovda omad!")
    await callback.answer()

@dp.callback_query(F.data.startswith("el_start_vote_"))
async def start_voting_cb(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    e_id=int(callback.data[14:])
    db.start_voting(e_id)
    candidates=db.get_confirmed_candidates(e_id)
    if not candidates:
        await callback.message.edit_text("❌ Tasdiqlangan nomzodlar yo'q!"); return
    buttons=[[InlineKeyboardButton(text=f"👤 {fname or uname}",callback_data=f"vote_{e_id}_{uid}")] for uid,fname,uname in candidates]
    users=db.get_all_user_ids(); sent=failed=0
    for user_id in users:
        try:
            await bot.send_message(user_id,"🗳 <b>SAYLOV BOSHLANDI!</b>\n\nYordamchi admin uchun ovoz bering:",
                parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
            sent+=1
        except: failed+=1
        await asyncio.sleep(0.05)
    await callback.message.edit_text(f"✅ Saylov boshlandi! {sent} ta foydalanuvchiga xabar yuborildi.")
    await callback.answer()

@dp.callback_query(F.data.startswith("vote_"))
async def cast_vote_cb(callback: types.CallbackQuery):
    parts=callback.data.split("_"); e_id,cand_id=int(parts[1]),int(parts[2])
    voter=callback.from_user.id
    election=db.get_active_election()
    if not election or election[1]!="active":
        await callback.answer("Saylov hozir faol emas!",show_alert=True); return
    if db.has_voted(e_id, voter):
        await callback.answer("⚠️ Siz allaqachon ovoz bergansiz!",show_alert=True); return
    db.cast_vote(e_id, voter, cand_id)
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.answer("✅ Ovozingiz qabul qilindi!",show_alert=True)

@dp.callback_query(F.data.startswith("el_finish_"))
async def finish_election_cb(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    e_id=int(callback.data[10:])
    winner_id=db.finish_election(e_id)
    if winner_id:
        winner=db.get_user(winner_id)
        fname=winner[2] if winner else str(winner_id)
        db.add_sub_admin(winner_id, winner[1] if winner else "", fname, SUB_ADMIN_TERM_DAYS)
        try:
            await bot.send_message(winner_id,
                f"🏆 <b>Tabriklaymiz, {fname}!</b>\n\n"
                "Saylovda g'olib chiqdingiz — <b>Yordamchi Admin</b> etib tayinlandingiz!\n"
                f"Lavozim muddati: {SUB_ADMIN_TERM_DAYS} kun",parse_mode="HTML")
        except: pass
        users=db.get_all_user_ids()
        for uid in users:
            try:
                await bot.send_message(uid,f"🏆 <b>Saylov yakunlandi!</b>\n\nYordamchi admin: <b>{fname}</b>",parse_mode="HTML")
                await asyncio.sleep(0.05)
            except: pass
        await callback.message.edit_text(f"✅ G'olib: {fname} ({winner_id})")
    else:
        await callback.message.edit_text("❌ Ovozlar bo'lmadi.")
    await callback.answer()

@dp.callback_query(F.data.startswith("el_results_"))
async def show_results(callback: types.CallbackQuery):
    e_id=int(callback.data[11:])
    results=db.get_election_results(e_id)
    text=f"📊 <b>Saylov #{e_id} natijalari</b>\n\n"
    for i,(uid,fname,uname,votes) in enumerate(results):
        text+=f"{i+1}. {fname or uname} — <b>{votes}</b> ovoz\n"
    await callback.message.answer(text,parse_mode="HTML")
    await callback.answer()

# ═══════════════ YORDAMCHI ADMIN PANEL ═══════════════
@dp.message(F.text=="🛡 Yordamchi Admin Panel")
async def sub_admin_panel(message: types.Message):
    uid=message.from_user.id
    if not is_sub_admin(uid): return
    sa=db.get_sub_admin(uid)
    days_left=""
    if sa and sa[4]:
        try:
            te=datetime.strptime(sa[4][:19],"%Y-%m-%d %H:%M:%S")
            days=max(0,(te-datetime.now()).days)
            days_left=f"\n⏳ Muddat: {days} kun qoldi"
        except: pass
    text=(f"🛡 <b>Yordamchi Admin Panel</b>\n\n"
          f"👤 {sa[2] if sa else uid}\n"
          f"💰 Moash: {sa[5] if sa else 0} coin/oy\n"
          f"📝 Hisobotlar: {sa[7] if sa else 0}\n"
          f"⚠️ Ogohlantirishlar: {sa[8] if sa else 0}{days_left}")
    await message.answer(text,parse_mode="HTML",reply_markup=sub_admin_menu())

@dp.message(F.text=="➕ Savol yuborish")
async def sub_add_question_start(message: types.Message, state: FSMContext):
    if not is_sub_admin(message.from_user.id): return
    await state.clear(); await state.set_state(SubAdminStates.waiting_question_type)
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Test (A,B,C,D)",callback_data="saqtype_test")],
        [InlineKeyboardButton(text="✍️ Ochiq savol",callback_data="saqtype_open")]])
    await message.answer("📌 Savol turini tanlang:\n\n<i>⚠️ Savol bosh adminga jo'natiladi va tasdiqdan keyin faollashadi</i>",parse_mode="HTML",reply_markup=kb)

@dp.callback_query(F.data.startswith("saqtype_"))
async def sub_choose_qtype(callback: types.CallbackQuery, state: FSMContext):
    qtype=callback.data[8:]
    await state.update_data(q_type=qtype)
    await state.set_state(SubAdminStates.waiting_question_text)
    await callback.message.edit_text("✏️ Savol matnini kiriting:")
    await callback.answer()

@dp.message(SubAdminStates.waiting_question_text)
async def sub_get_question_text(message: types.Message, state: FSMContext):
    data=await state.get_data(); qtype=data["q_type"]
    await state.update_data(q_text=message.text)
    if qtype=="test":
        await state.set_state(SubAdminStates.waiting_options)
        await message.answer("📋 Variantlarni kiriting (har biri yangi qatorda):")
    else:
        await state.set_state(SubAdminStates.waiting_correct_answer)
        await message.answer("✅ To'g'ri javobni kiriting:")

@dp.message(SubAdminStates.waiting_options)
async def sub_get_options(message: types.Message, state: FSMContext):
    options=[o.strip() for o in message.text.split("\n") if o.strip()]
    if len(options)<2:
        await message.answer("⚠️ Kamida 2 ta variant!"); return
    await state.update_data(options="|".join(options))
    await state.set_state(SubAdminStates.waiting_correct_answer)
    opts_text="\n".join([f"{chr(65+i)}. {opt}" for i,opt in enumerate(options)])
    await message.answer(f"📋 Variantlar:\n{opts_text}\n\n✅ To'g'ri harfni kiriting (A/B/C/D):")

@dp.message(SubAdminStates.waiting_correct_answer)
async def sub_get_correct(message: types.Message, state: FSMContext):
    await state.update_data(correct=message.text.strip())
    await state.set_state(SubAdminStates.waiting_coin_reward)
    await message.answer("💰 Necha coin?")

@dp.message(SubAdminStates.waiting_coin_reward)
async def sub_get_coins(message: types.Message, state: FSMContext):
    if not message.text.replace(".","").isdigit():
        await message.answer("⚠️ Faqat raqam!"); return
    await state.update_data(coins=float(message.text))
    await state.set_state(SubAdminStates.waiting_difficulty)
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Oson",callback_data="sdiff_oson")],
        [InlineKeyboardButton(text="🟡 O'rta",callback_data="sdiff_orta")],
        [InlineKeyboardButton(text="🔴 Qiyin",callback_data="sdiff_qiyin")]])
    await message.answer("📊 Qiyinlik darajasi:",reply_markup=kb)

@dp.callback_query(F.data.startswith("sdiff_"))
async def sub_get_difficulty(callback: types.CallbackQuery, state: FSMContext):
    difficulty=callback.data[6:]
    await state.update_data(difficulty=difficulty)
    await state.set_state(SubAdminStates.waiting_category)
    cats=db.get_categories(); buttons=[]; row=[]
    for cat in cats:
        row.append(InlineKeyboardButton(text=cat,callback_data=f"sselcat_{cat}"))
        if len(row)==2: buttons.append(row); row=[]
    if row: buttons.append(row)
    await callback.message.edit_text("📂 Kategoriyani tanlang:",reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("sselcat_"))
async def sub_select_category(callback: types.CallbackQuery, state: FSMContext):
    cat=callback.data[8:]
    await state.update_data(category=cat)
    await state.set_state(SubAdminStates.waiting_explanation)
    await callback.message.edit_text("💡 Tavsif:\n<i>'-' = kerak emas</i>",parse_mode="HTML")
    await callback.answer()

@dp.message(SubAdminStates.waiting_explanation)
async def sub_get_explanation(message: types.Message, state: FSMContext):
    explanation="" if message.text.strip()=="-" else message.text.strip()
    await state.update_data(explanation=explanation)
    data=await state.get_data()
    diff_icon=DIFFICULTY_ICONS.get(data.get("difficulty","orta"),"🟡")
    options_display=""
    if data["q_type"]=="test":
        opts=data.get("options","").split("|")
        options_display="\n"+"\n".join([f"  {chr(65+i)}. {opt}" for i,opt in enumerate(opts)])
        options_display+=f"\n✅ To'g'ri: {data['correct'].upper()}"
    else: options_display=f"\n✅ Javob: {data['correct']}"
    confirm=(f"📋 <b>Savolingizni tekshiring:</b>\n\n"
             f"Tur: {data['q_type'].upper()}\n❓ {data['q_text'][:200]}{options_display}\n"
             f"💰 {data['coins']} coin\n{diff_icon}\n📂 {data.get('category','')}\n\n"
             f"⚠️ <i>Savol bosh adminga yuboriladi va tasdiqdan keyin faollashadi.</i>")
    kb=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📤 Yuborish",callback_data="sub_send_question"),
        InlineKeyboardButton(text="❌ Bekor",callback_data="sub_cancel_question")]])
    await message.answer(confirm,parse_mode="HTML",reply_markup=kb)

@dp.callback_query(F.data=="sub_send_question")
async def sub_send_question_cb(callback: types.CallbackQuery, state: FSMContext):
    data=await state.get_data(); uid=callback.from_user.id
    pq_id=db.add_pending_question(
        sub_admin_id=uid, text=data["q_text"], q_type=data["q_type"],
        options=data.get("options",""), correct=data.get("correct",""),
        coins=data["coins"], category=data.get("category","Umumiy"),
        difficulty=data.get("difficulty","orta"), explanation=data.get("explanation",""))
    for admin_id in ADMIN_IDS:
        try:
            sa=db.get_sub_admin(uid); fname=sa[2] if sa else str(uid)
            await bot.send_message(admin_id,
                f"📬 <b>Yangi savol kutmoqda!</b>\n\nYordamchi admin: {fname}\n"
                f"Savol #{pq_id}: {data['q_text'][:80]}\n\n"
                f"'⏳ Kutayotgan savollar' bo'limiga kiring.",parse_mode="HTML")
        except: pass
    await state.clear()
    await callback.message.edit_text("✅ <b>Savol adminga yuborildi! Tasdiqlanishini kuting.</b>",parse_mode="HTML")
    await callback.message.answer("🛡 Panel",reply_markup=sub_admin_menu())
    await callback.answer()

@dp.callback_query(F.data=="sub_cancel_question")
async def sub_cancel_question(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.message.answer("🛡 Panel",reply_markup=sub_admin_menu())
    await callback.answer()

@dp.message(F.text=="📝 Hisobot yozish")
async def sub_write_report(message: types.Message, state: FSMContext):
    uid=message.from_user.id
    if not is_sub_admin(uid): return
    sa=db.get_sub_admin(uid)
    if sa and sa[6]:
        try:
            lr=datetime.strptime(sa[6][:19],"%Y-%m-%d %H:%M:%S")
            diff=(datetime.now()-lr).days
            if diff<REPORT_DEADLINE_DAYS:
                await message.answer(f"⏳ Keyingi hisobot {REPORT_DEADLINE_DAYS-diff} kundan keyin yozilishi mumkin."); return
        except: pass
    await state.set_state(SubAdminStates.writing_report)
    await message.answer("📝 <b>Hisobotingizni yozing:</b>\n\nNima qildingiz? Muammolar? Takliflar?\n\n<i>/cancel — bekor</i>",parse_mode="HTML")

@dp.message(SubAdminStates.writing_report)
async def sub_save_report(message: types.Message, state: FSMContext):
    uid=message.from_user.id
    db.save_report(uid, message.text)
    for admin_id in ADMIN_IDS:
        try:
            sa=db.get_sub_admin(uid); fname=sa[2] if sa else str(uid)
            await bot.send_message(admin_id,
                f"📜 <b>Yangi hisobot!</b>\n\n👤 {fname}\n📅 {datetime.now().strftime('%Y-%m-%d')}\n\n{message.text[:500]}",
                parse_mode="HTML")
        except: pass
    await state.clear()
    await message.answer("✅ <b>Hisobotingiz adminga yuborildi!</b>",parse_mode="HTML",reply_markup=sub_admin_menu())

@dp.message(F.text=="💬 Takliflar o'qish")
async def sub_read_feedbacks(message: types.Message):
    if not is_sub_admin(message.from_user.id): return
    feedbacks=db.get_feedbacks(10)
    if not feedbacks:
        await message.answer("💬 Hali taklif yo'q."); return
    for fb in feedbacks[:5]:
        fb_id,user_id,fname,username,fb_text,fb_date,is_read=fb
        read_icon="🆕" if not is_read else "✅"
        uname=f"@{username}" if username else f"ID:{user_id}"
        await message.answer(f"{read_icon} <b>#{fb_id}</b> — {fname} ({uname})\n📅 {fb_date[:10]}\n\n{fb_text}",
            parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💬 Javob yozish",callback_data=f"subfb_reply_{fb_id}")]]))

@dp.message(F.text=="💬 Javob yozish")
async def sub_reply_fb_start(message: types.Message, state: FSMContext):
    if not is_sub_admin(message.from_user.id): return
    await message.answer("💬 Javob yozmoqchi bo'lgan taklif <b>#ID</b> sini kiriting:")

@dp.callback_query(F.data.startswith("subfb_reply_"))
async def sub_fb_reply_cb(callback: types.CallbackQuery, state: FSMContext):
    if not is_sub_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!"); return
    fb_id=int(callback.data[12:])
    await state.update_data(reply_fb_id=fb_id)
    await state.set_state(SubAdminStates.fb_reply)
    await callback.message.answer(f"💬 #{fb_id} ga javobingizni yozing:")
    await callback.answer()

@dp.message(SubAdminStates.fb_reply)
async def sub_save_fb_reply(message: types.Message, state: FSMContext):
    data=await state.get_data(); fb_id=data["reply_fb_id"]
    fb=db.get_feedback_by_id(fb_id)
    if fb:
        user_id=fb[1]; db.save_feedback_reply(fb_id, message.text)
        try: await bot.send_message(user_id,f"📩 <b>Taklifingizga javob:</b>\n\n{message.text}",parse_mode="HTML")
        except: pass
    await state.clear()
    await message.answer("✅ Javob yuborildi!",reply_markup=sub_admin_menu())

@dp.message(F.text=="📢 Xabar tarqatish")
async def sub_broadcast_start(message: types.Message, state: FSMContext):
    if not is_sub_admin(message.from_user.id): return
    await state.set_state(SubAdminStates.broadcast_text)
    await message.answer("📢 Xabar matnini kiriting:\n<i>/cancel — bekor</i>",parse_mode="HTML")

@dp.message(SubAdminStates.broadcast_text)
async def sub_broadcast_get_text(message: types.Message, state: FSMContext):
    await state.update_data(broadcast_text=message.text)
    await state.set_state(SubAdminStates.broadcast_image)
    await message.answer("🖼 Rasm (ixtiyoriy) yoki <b>'-'</b>:",parse_mode="HTML")

@dp.message(SubAdminStates.broadcast_image)
async def sub_broadcast_do(message: types.Message, state: FSMContext):
    data=await state.get_data(); text=data["broadcast_text"]
    image_id=message.photo[-1].file_id if message.photo else ""
    await state.update_data(broadcast_image=image_id)
    kb=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📢 Yuborish",callback_data="sub_confirm_bc"),
        InlineKeyboardButton(text="❌ Bekor",callback_data="sub_cancel_bc")]])
    await message.answer(f"📢 Yuborilsinmi?\n\n{text}",reply_markup=kb)

@dp.callback_query(F.data=="sub_confirm_bc")
async def sub_do_broadcast(callback: types.CallbackQuery, state: FSMContext):
    uid=callback.from_user.id
    if not is_sub_admin(uid): return
    data=await state.get_data(); text,image_id=data["broadcast_text"],data.get("broadcast_image","")
    sa=db.get_sub_admin(uid); fname=sa[2] if sa else "Yordamchi admin"
    full_text=f"📢 <b>{fname} dan xabar:</b>\n\n{text}"
    users=db.get_all_user_ids(); success=failed=0
    for user_id in users:
        try:
            if image_id: await bot.send_photo(user_id,photo=image_id,caption=full_text,parse_mode="HTML")
            else: await bot.send_message(user_id,full_text,parse_mode="HTML")
            success+=1
        except: failed+=1
        await asyncio.sleep(0.05)
    await state.clear()
    await callback.message.edit_text(f"✅ {success} ta yuborildi, ❌ {failed} ta xato.")
    await callback.message.answer("🛡 Panel",reply_markup=sub_admin_menu())
    await callback.answer()

@dp.callback_query(F.data=="sub_cancel_bc")
async def sub_cancel_bc(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor.")
    await callback.message.answer("🛡 Panel",reply_markup=sub_admin_menu())
    await callback.answer()

@dp.message(F.text=="💰 Moashim")
async def sub_my_salary(message: types.Message):
    uid=message.from_user.id
    if not is_sub_admin(uid): return
    sa=db.get_sub_admin(uid)
    if not sa:
        await message.answer("Ma'lumot topilmadi!"); return
    _,uname,fname,elected,term_end,salary,last_report,rep_count,warnings,is_active=sa
    payments=db.get_payments(target_id=uid, limit=5)
    user=db.get_user(uid); coins=round(user[3],1) if user else 0
    text=(f"💰 <b>Moash va To'lovlar</b>\n\n"
          f"💎 Belgilangan moash: <b>{salary} coin/oy</b>\n"
          f"💰 Hozirgi coinlar: <b>{coins}</b>\n"
          f"📝 Hisobotlar: <b>{rep_count}</b>\n"
          f"⚠️ Ogohlantirishlar: <b>{warnings}</b>\n\n"
          f"📋 <b>So'nggi to'lovlar:</b>\n")
    for p in payments:
        p_id,a_id,t_id,amount,ptype,note,created=p
        icon="🏆" if ptype=="bonus" else ("⚠️" if ptype=="fine" else "💰")
        sign="-" if ptype=="fine" else "+"
        text+=f"{icon} {sign}{amount} | {note or ptype} | {created[:10]}\n"
    await message.answer(text,parse_mode="HTML")

# ═══════════════ AVTOMATIK MUDDATNI TEKSHIRISH ═══════════════
async def check_sub_admin_terms():
    while True:
        await asyncio.sleep(86400)
        subs=db.get_all_sub_admins()
        for s in subs:
            uid,uname,fname,elected,term_end,salary,last_report,rep_count,warnings,is_active=s
            if not term_end: continue
            try:
                te=datetime.strptime(term_end[:19],"%Y-%m-%d %H:%M:%S")
                if datetime.now()>te:
                    db.remove_sub_admin(uid)
                    try: await bot.send_message(uid,"⏰ <b>Yordamchi admin lavozimingiz muddati tugadi. Rahmat xizmatingiz uchun!</b>",parse_mode="HTML")
                    except: pass
                    for admin_id in ADMIN_IDS:
                        try: await bot.send_message(admin_id,f"ℹ️ {fname} ({uid}) muddati tugadi, lavozimdan olindi.",parse_mode="HTML")
                        except: pass
                    continue
                ref_date=elected
                if last_report: ref_date=last_report
                lr=datetime.strptime(ref_date[:19],"%Y-%m-%d %H:%M:%S")
                days_since=(datetime.now()-lr).days
                if days_since>=REPORT_DEADLINE_DAYS:
                    w=db.add_sub_admin_warning(uid)
                    try:
                        await bot.send_message(uid,
                            f"⚠️ <b>Ogohlantirish #{w}!</b>\n\nHisobot yozish muddati o'tdi.\nIltimos, tezda hisobot yozing.\n3 ta ogohlantirish = lavozimdan olish!",
                            parse_mode="HTML")
                    except: pass
                    if w>=3:
                        db.remove_sub_admin(uid)
                        try: await bot.send_message(uid,"❌ <b>3 ta ogohlantirish tufayli lavozimdan olindingiz!</b>",parse_mode="HTML")
                        except: pass
                        for admin_id in ADMIN_IDS:
                            try: await bot.send_message(admin_id,f"❌ {fname} ({uid}) 3 ogohlantirish tufayli lavozimdan olindi.",parse_mode="HTML")
                            except: pass
            except: pass

async def main():
    asyncio.create_task(check_sub_admin_terms())
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__=="__main__":
    asyncio.run(main())
