import logging
import asyncio
import random
import re
import json
import aiohttp
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton,
                           ReplyKeyboardMarkup, KeyboardButton)
from database import db
from config import BOT_TOKEN, ADMIN_IDS, PENALTY_PERCENT, TIMEOUT_PENALTY, STREAK_BONUSES, GROQ_API_KEY, GROQ_MODEL

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)

# ── STIKERLAR ────────────────────────────────────────────────────────────────
STICKER_QUESTION    = "CAACAgQAAxkBAAFK2GFqGBZkvOQYIqxuYRxOg8yZ_kGpCQACLhMAAqtUsFGayERH0PRbYTsE"
STICKER_CORRECT     = "CAACAgQAAxkBAAFK2FxqGBZODMIw26R9HpabXj_GXXHY_QAC9wsAAsVA0FKiYzU0cZkIATsE"
STICKER_WRONG       = "CAACAgIAAxkBAAFK2GZqGBaGcsKcNXFNKzEjnwAB_N6SLx4AAiZjAAIexglIbW6k0yQK8f47BA"
STICKER_LEADERBOARD = "CAACAgQAAxkBAAFK2F5qGBZib8V7GFYDhDMw8H10BaJIfgAChBYAAkfnsFEm5zMVxs4-nDsE"
STICKER_TIMEOUT     = "CAACAgIAAxkBAAFK2CpqGBT9Y8JM8DQ_k5oZ_koPS4fNlgACWiYAAlDgwEhOxSLS4ALrSDsE"


dp = Dispatcher(storage=MemoryStorage())

# ── KONSTANTLAR ──────────────────────────────────────────────────────────────
DIFF_ICONS = {"oson": "🟢", "orta": "🟡", "qiyin": "🔴"}
DIFF_NAMES = {"oson": "Oson", "orta": "O'rta", "qiyin": "Qiyin"}
DIFF_TIME  = {"oson": 30, "orta": 60, "qiyin": 90}
IELTS_TYPES = ["writing","essay","reading","speaking","listening"]
LEAGUE_ICONS = {"bronza":"🥉","kumush":"🥈","oltin":"🥇","platina":"💎","olmos":"💠"}
LEAGUE_PTS   = {"bronza":0,"kumush":80,"oltin":200,"platina":500,"olmos":1000}
SUB_ADMIN_TERM = 21
REPORT_DAYS = 3

active_timers = {}
live_timers = {}

MENU_TEXTS = {
    "🎯 Savol olish","🏆 Reyting","👤 Profilim","ℹ️ Yordam",
    "📝 Taklif/Shikoyat","🎓 IELTS","⚔️ Duel","🏅 Liga",
    "🤖 AI Chat","👥 Guruhga ulash","⚙️ Admin Panel",
    "🛡 Yordamchi Admin Panel","🔙 Asosiy menyu","🚪 AI Chatdan chiqish",
    "🟢 Live Savol tashlash","➕ Savol qo'shish","📋 Savollar ro'yxati",
    "✏️ Savol tahrirlash","🗑 Savol o'chirish","📂 Kategoriyalar",
    "📊 Statistika","👥 Foydalanuvchilar","💬 Takliflar","📢 Xabar yuborish",
    "⏳ Kutayotgan savollar","🛡 Yordamchi Adminlar","🗳 Saylov boshqaruvi",
    "💰 Mukofot/Jarima","📜 Hisobotlar","👥 Guruhlar",
    "📥 Savollarni import qilish","➕ Savol yuborish","📝 Hisobot yozish",
    "💬 Takliflar o'qish","💬 Javob yozish","📢 Xabar tarqatish","💰 Moashim",
}

# ── STATES ───────────────────────────────────────────────────────────────────
class AdminSt(StatesGroup):
    q_type=State(); q_text=State(); q_opts=State(); q_correct=State()
    q_coins=State(); q_diff=State(); q_cat=State(); q_expl=State()
    q_img=State(); q_time=State(); new_cat=State()
    edit_id=State(); edit_field=State(); edit_val=State()
    bc_text=State(); bc_img=State()
    pay_target=State(); pay_amount=State(); pay_note=State(); pay_type_st=State()
    sub_sel=State(); sub_salary=State()
    fb_reply=State()
    bulk_text=State(); bulk_cat=State()
    live_type=State(); live_time=State()

class SubSt(StatesGroup):
    q_type=State(); q_text=State(); q_opts=State(); q_correct=State()
    q_coins=State(); q_diff=State(); q_cat=State(); q_expl=State()
    report=State(); fb_reply=State(); bc_text=State(); bc_img=State()

class UserSt(StatesGroup):
    open_ans=State(); feedback=State(); premium=State()
    ielts=State(); ai_chat=State(); ai_debt=State()

# ── MENYULAR ─────────────────────────────────────────────────────────────────
def is_admin(uid): return uid in ADMIN_IDS
def is_sub_admin(uid): return db.is_sub_admin(uid)

def main_menu(uid):
    b = [[KeyboardButton(text="🎯 Savol olish"), KeyboardButton(text="🏆 Reyting")],
         [KeyboardButton(text="👤 Profilim"),    KeyboardButton(text="ℹ️ Yordam")],
         [KeyboardButton(text="📝 Taklif/Shikoyat"), KeyboardButton(text="🎓 IELTS")],
         [KeyboardButton(text="⚔️ Duel"),        KeyboardButton(text="🏅 Liga")],
         [KeyboardButton(text="🤖 AI Chat"),     KeyboardButton(text="👥 Guruhga ulash")]]
    if is_admin(uid):
        b.append([KeyboardButton(text="⚙️ Admin Panel")])
    elif is_sub_admin(uid):
        b.append([KeyboardButton(text="🛡 Yordamchi Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=b, resize_keyboard=True)

def admin_menu():
    b = [[KeyboardButton(text="🟢 Live Savol tashlash"), KeyboardButton(text="➕ Savol qo'shish")],
         [KeyboardButton(text="📋 Savollar ro'yxati"),   KeyboardButton(text="✏️ Savol tahrirlash")],
         [KeyboardButton(text="🗑 Savol o'chirish"),      KeyboardButton(text="📂 Kategoriyalar")],
         [KeyboardButton(text="📊 Statistika"),           KeyboardButton(text="👥 Foydalanuvchilar")],
         [KeyboardButton(text="💬 Takliflar"),            KeyboardButton(text="📢 Xabar yuborish")],
         [KeyboardButton(text="⏳ Kutayotgan savollar"),  KeyboardButton(text="🛡 Yordamchi Adminlar")],
         [KeyboardButton(text="🗳 Saylov boshqaruvi"),    KeyboardButton(text="💰 Mukofot/Jarima")],
         [KeyboardButton(text="📜 Hisobotlar"),           KeyboardButton(text="👥 Guruhlar")],
         [KeyboardButton(text="📥 Savollarni import qilish")],
         [KeyboardButton(text="🔙 Asosiy menyu")]]
    return ReplyKeyboardMarkup(keyboard=b, resize_keyboard=True)

def sub_menu():
    b = [[KeyboardButton(text="➕ Savol yuborish"),  KeyboardButton(text="📝 Hisobot yozish")],
         [KeyboardButton(text="💬 Takliflar o'qish"), KeyboardButton(text="💬 Javob yozish")],
         [KeyboardButton(text="📢 Xabar tarqatish"),  KeyboardButton(text="💰 Moashim")],
         [KeyboardButton(text="🔙 Asosiy menyu")]]
    return ReplyKeyboardMarkup(keyboard=b, resize_keyboard=True)

# ── AI FUNKSIYALARI ───────────────────────────────────────────────────────────
GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama3-70b-8192"]

async def groq_call(messages, max_tokens=1000):
    models = [GROQ_MODEL] + [m for m in GROQ_MODELS if m != GROQ_MODEL]
    for model in models:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": 0.7
                    },
                    timeout=aiohttp.ClientTimeout(total=40)
                ) as r:
                    if r.status != 200:
                        text = await r.text()
                        logging.warning(f"Groq {model} HTTP {r.status}: {text[:200]}")
                        continue
                    d = await r.json()
                    if "error" in d:
                        logging.warning(f"Groq {model} error: {d['error']}")
                        continue
                    if "choices" in d and d["choices"]:
                        result = d["choices"][0]["message"]["content"]
                        logging.info(f"Groq {model} OK: {len(result)} chars")
                        return result
        except asyncio.TimeoutError:
            logging.warning(f"Groq {model} timeout (40s)")
        except Exception as e:
            logging.warning(f"Groq {model} exception: {e}")
    logging.error("Barcha Groq modellari ishlamadi!")
    return None

async def ai_req(prompt):
    r = await groq_call([{"role": "user", "content": prompt}])
    return r or "⚠️ AI hozirda ishlamayapti."

async def ai_chat(history, user_text):
    sys = "Siz BilimChallenge botining AI yordamchisisiz. O'zbek tilida qisqa, foydali javob bering."
    msgs = [{"role": "system", "content": sys}] + history[-6:] + [{"role": "user", "content": user_text}]
    r = await groq_call(msgs, max_tokens=800)
    return r or "⚠️ AI hozirda ishlamayapti."

# ── YORDAMCHI FUNKSIYALAR ─────────────────────────────────────────────────────
def streak_bonus(s):
    b = 1.0
    for t in sorted(STREAK_BONUSES.keys()):
        if s >= t: b = STREAK_BONUSES[t]
    return b

def shuffle_opts(opts_str, correct_letter):
    opts = opts_str.split("|")
    ci = ord(correct_letter.upper()) - 65
    if ci >= len(opts): return opts_str, correct_letter
    ct = opts[ci]
    random.shuffle(opts)
    nc = opts.index(ct)
    return "|".join(opts), chr(65 + nc)

def check_ans(user_ans, correct):
    ua = user_ans.strip().lower()
    return ua in [a.strip().lower() for a in correct.split("\n") if a.strip()]

def parse_band(text):
    for p in [r'BAND[:\s]+(\d+\.?\d*)', r'(\d+\.?\d*)\s*/\s*9', r'(\d+\.?\d*)\s*ball']:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                v = float(m.group(1))
                if v <= 9: return v
            except: pass
    return None

def is_uzbek(text):
    cyrillic = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")
    uz_words = {"va","bu","men","sen","biz","ham","emas","bor","deb","uchun","bilan","lekin"}
    if any(c in cyrillic for c in text): return True
    words = set(text.lower().split())
    return len(words & uz_words) >= 2

def is_lazy(text):
    lazy = {"bilmayman","bilmadim","idk","no idea","???","...","ha","yo'q","ok","test","salom"}
    return len(text.strip()) < 10 or text.strip().lower() in lazy

async def send_long(chat_id, text, parse_mode="HTML", reply_markup=None):
    LIMIT = 4000
    if len(text) <= LIMIT:
        return await bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    parts = []
    while len(text) > LIMIT:
        sp = text.rfind("\n", 0, LIMIT)
        if sp == -1: sp = LIMIT
        parts.append(text[:sp])
        text = text[sp:]
    parts.append(text)
    last = None
    for i, p in enumerate(parts):
        last = await bot.send_message(chat_id, p, parse_mode=parse_mode,
                                      reply_markup=reply_markup if i == len(parts)-1 else None)
    return last

def build_opts_kb(opts_list, q_id, new_correct, prefix="ans"):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=chr(65+i), callback_data=f"{prefix}_{q_id}_{chr(65+i)}_{new_correct}")
        for i in range(len(opts_list))]])

# ── IMPORT QILISH PARSERI ─────────────────────────────────────────────────────
def parse_questions(text):
    questions = []
    blocks = re.split(r'(?=\d+[-–.]\s*savol)', text, flags=re.IGNORECASE)
    for block in blocks:
        block = block.strip()
        if not block or len(block) < 15: continue
        if re.search(r'variant|test', block, re.IGNORECASE) or re.search(r'[A-E]\)\s', block):
            q_type = "test"
        else:
            q_type = "open"
        # Savol matni
        m = re.search(r'(?:\d+[-–.]\s*savol[^:]*:\s*)?(.+?)(?=\s*A\)\s|To[\'ʻ]g[\'ʻ]ri\s*javob|Tavsif\s*:|$)',
                      block, re.IGNORECASE | re.DOTALL)
        q_text = re.sub(r'\s+', ' ', m.group(1)).strip() if m else ""
        if not q_text or len(q_text) < 10: continue
        # Variantlar
        options = []
        for _, opt in re.findall(r'([A-E])\)\s*(.+?)(?=[A-E]\)|To[\'ʻ]g[\'ʻ]ri|Tavsif|$)', block, re.DOTALL):
            options.append(re.sub(r'\s+', ' ', opt).strip())
        # To'g'ri javob
        cm = re.search(r"To[\'ʻ]g[\'ʻ]ri\s*javob[:\s]+([^\n\s]+)", block, re.IGNORECASE)
        correct = cm.group(1).strip() if cm else ""
        # Tavsif
        tm = re.search(r'Tavsif[:\s]+(.+?)$', block, re.IGNORECASE | re.DOTALL)
        explanation = re.sub(r'\s+', ' ', tm.group(1)).strip() if tm else ""
        if q_text and correct:
            questions.append({"text": q_text, "type": q_type,
                              "options": "|".join(options), "correct": correct,
                              "explanation": explanation, "coins": 5})
    return questions

# ── route_menu ────────────────────────────────────────────────────────────────
async def route_menu(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    t = message.text
    if t == "🎯 Savol olish": await question_start(message, state)
    elif t == "🏆 Reyting": await show_leaderboard(message)
    elif t == "👤 Profilim": await show_profile(message)
    elif t == "ℹ️ Yordam": await show_help(message)
    elif t == "📝 Taklif/Shikoyat": await feedback_start(message, state)
    elif t == "🎓 IELTS": await ielts_menu(message)
    elif t == "⚔️ Duel": await duel_menu(message, state)
    elif t == "🏅 Liga": await liga_menu(message, state)
    elif t == "🤖 AI Chat": await ai_chat_start(message, state)
    elif t == "👥 Guruhga ulash": await guruhga_ulash(message)
    elif t == "⚙️ Admin Panel": await admin_panel(message)
    elif t == "🛡 Yordamchi Admin Panel": await sub_panel(message)
    elif t == "🔙 Asosiy menyu":
        await state.clear()
        await message.answer("🏠 Asosiy menyu", reply_markup=main_menu(uid))
    else:
        await message.answer("🏠 Asosiy menyu", reply_markup=main_menu(uid))

# ══════════════════════════════════════════════════════════════════════════════
# START
# ══════════════════════════════════════════════════════════════════════════════
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    u = message.from_user
    args = message.text.split()
    ref_id = None
    if len(args) > 1 and args[1].startswith("ref"):
        try:
            ref_id = int(args[1][3:])
            if ref_id == u.id: ref_id = None
        except: pass
    db.add_user(u.id, u.username or "", u.first_name or "", ref_id)
    ref_msg = "\n\n🎁 <b>Referal orqali qo'shildingiz!</b> Do'stingiz +30 coin oldi!" if ref_id else ""
    me = await bot.get_me()
    add_url = f"https://t.me/{me.username}?startgroup=start"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👥 Botni guruhga qo'shish", url=add_url)]])
    await message.answer(
        f"🧠 <b>BilimChallenge</b> ga xush kelibsiz, {u.first_name}!\n\n"
        "🎯 Savollarga javob bering  💰 Coin to'plang\n"
        "🔥 Streak  🏆 Reyting  🎓 IELTS  🤖 AI Chat\n"
        "⚔️ Duel  🏅 Liga  👥 Do'st taklif qil (+30 coin)" + ref_msg,
        parse_mode="HTML", reply_markup=main_menu(u.id))
    await message.answer("👇 Guruhingizga ham qo'shing:", reply_markup=kb)

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor.", reply_markup=main_menu(message.from_user.id))

# ══════════════════════════════════════════════════════════════════════════════
# SAVOL OLISH (shaxsiy)
# ══════════════════════════════════════════════════════════════════════════════
@dp.message(F.text == "🎯 Savol olish")
async def question_start(message: types.Message, state: FSMContext):
    await state.clear()
    cats = db.get_categories()
    if not cats:
        await message.answer("😔 Hozircha savollar yo'q!"); return
    buttons = []
    row = []
    for cat in cats:
        row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat_{cat}"))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🌐 Barchasi", callback_data="cat_Barchasi")])
    await message.answer("📂 <b>Kategoriya tanlang:</b>", parse_mode="HTML",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("cat_"))
async def cat_chosen(callback: types.CallbackQuery, state: FSMContext):
    cat = callback.data[4:]
    await state.update_data(category=cat)
    try: await callback.message.delete()
    except: pass
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Test", callback_data=f"qmode_test_{cat}")],
        [InlineKeyboardButton(text="✍️ Ochiq", callback_data=f"qmode_open_{cat}")],
        [InlineKeyboardButton(text="🌐 Aralash", callback_data=f"qmode_all_{cat}")]])
    await callback.message.answer(f"📂 <b>{cat}</b>\n\nSavol turini tanlang:", parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("qmode_"))
async def qmode_chosen(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_", 2)
    mode, cat = parts[1], parts[2]
    await state.update_data(category=cat, qmode=mode)
    try: await callback.message.delete()
    except: pass
    await send_question(callback.message, callback.from_user.id, state, cat, mode)
    await callback.answer()

async def send_question(message, user_id, state, category, mode="all"):
    uid = user_id
    if mode == "test": q = db.get_random_question(uid, category, q_type="test")
    elif mode == "open": q = db.get_random_question(uid, category, q_type="open")
    else: q = db.get_random_question(uid, category)
    if not q:
        cats = db.get_categories()
        buttons = []
        row = []
        for cat in cats:
            row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat_{cat}"))
            if len(row) == 2: buttons.append(row); row = []
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton(text="🌐 Barchasi", callback_data="cat_Barchasi")])
        await message.answer(
            "🎉 <b>Barcha savollar tugadi!</b>\nBoshqa kategoriyani tanlang:",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return
    q_id, q_text, q_type, options, correct, coins, cat, diff, expl, img, tl = q
    if q_type == "premium":
        await send_premium(message, uid, state, category); return
    d_icon = DIFF_ICONS.get(diff, "🟡")
    d_name = DIFF_NAMES.get(diff, "O'rta")
    q_time = DIFF_TIME.get(diff, 30)
    header = (f"🆔 <b>#{q_id}</b>  📂 <b>{cat}</b>  {d_icon} <b>{d_name}</b>\n"
              f"💰 +{coins}  ❌ -{round(coins*PENALTY_PERCENT,1)}  ⏱ {q_time}s\n\n"
              f"❓ <b>{q_text}</b>")
    try: await bot.send_sticker(message.chat.id, sticker=STICKER_QUESTION)
    except: pass
    if q_type == "test":
        sh_opts, new_cor = shuffle_opts(options, correct)
        opts_list = sh_opts.split("|")
        opts_text = "\n".join
        full_text = header + "\n\n" + opts_text
        kb = build_opts_kb(opts_list, q_id, new_cor, "ans")
        if img:
            try:
                if len(full_text) <= 1024:
                    sent = await bot.send_photo(message.chat.id, photo=img, caption=full_text, parse_mode="HTML", reply_markup=kb)
                else:
                    await bot.send_photo(message.chat.id, photo=img)
                    sent = await message.answer(full_text, parse_mode="HTML", reply_markup=kb)
            except:
                sent = await message.answer(full_text, parse_mode="HTML", reply_markup=kb)
        else:
            if len(full_text) <= 4000:
                sent = await message.answer(full_text, parse_mode="HTML", reply_markup=kb)
            else:
                await send_long(message.chat.id, full_text, parse_mode="HTML")
                sent = await message.answer("👆 Javobni tanlang:", reply_markup=kb)
        await state.update_data(question_id=q_id, chat_id=message.chat.id)
        if uid in active_timers: active_timers[uid].cancel()
        active_timers[uid] = asyncio.create_task(q_timeout(uid, q_id, sent.message_id, message.chat.id, coins, state, q_time))
    else:
        await state.set_state(UserSt.open_ans)
        await state.update_data(question_id=q_id, correct=correct, coins=coins, explanation=expl, category=category, qmode=mode)
        full_text = header + "\n\n✍️ <b>Javobingizni yozing:</b>"
        skip_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⏭ O'tkazish", callback_data=f"skip_open_{q_id}")]])
        if img:
            try:
                if len(full_text) <= 1024:
                    sent = await bot.send_photo(message.chat.id, photo=img, caption=full_text, parse_mode="HTML")
                else:
                    await bot.send_photo(message.chat.id, photo=img)
                    sent = await message.answer(full_text, parse_mode="HTML")
            except:
                sent = await message.answer(full_text, parse_mode="HTML")
        else:
            sent = await send_long(message.chat.id, full_text, parse_mode="HTML")
        await message.answer("👆 Javob yozing:", reply_markup=skip_kb)
        if uid in active_timers: active_timers[uid].cancel()
        active_timers[uid] = asyncio.create_task(q_timeout(uid, q_id, sent.message_id, message.chat.id, coins, state, q_time))

async def q_timeout(uid, q_id, msg_id, chat_id, coins, state, total):
    wait = total - 10
    if wait > 0: await asyncio.sleep(wait)
    timer_msg = None
    for rem in range(10, 0, -1):
        if db.already_answered(uid, q_id):
            if timer_msg:
                try: await timer_msg.delete()
                except: pass
            return
        block = "🟥" if rem <= 3 else ("🟧" if rem <= 6 else "🟨")
        bar = block * int(rem/total*10) + "⬜" * (10 - int(rem/total*10))
        try:
            if timer_msg is None:
                timer_msg = await bot.send_message(chat_id, f"⏱ <b>{rem}s</b> {bar}", parse_mode="HTML")
            else:
                await timer_msg.edit_text(f"⏱ <b>{rem}s</b> {bar}", parse_mode="HTML")
        except: pass
        await asyncio.sleep(1)
    if db.already_answered(uid, q_id):
        if timer_msg:
            try: await timer_msg.delete()
            except: pass
        return
    db.save_answer(uid, q_id, False)
    penalty = round(coins * TIMEOUT_PENALTY, 1)
    db.add_coins(uid, -penalty)
    db.update_streak(uid, False)
    if timer_msg:
        try: await timer_msg.delete()
        except: pass
    try: await bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=None)
    except: pass
    try: await bot.send_sticker(chat_id, sticker=STICKER_TIMEOUT)
    except: pass
    data = await state.get_data()
    cat = data.get("category", "Barchasi")
    mode = data.get("qmode", "all")
    await bot.send_message(chat_id,
        f"⏰ <b>Vaqt tugadi!</b> -{penalty} coin",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="➡️ Keyingi", callback_data=f"next_{mode}_{cat}")]]))
    active_timers.pop(uid, None)

@dp.callback_query(F.data.startswith("ans_"))
async def handle_test_ans(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    q_id, ua, cl = int(parts[1]), parts[2], parts[3]
    uid = callback.from_user.id
    if db.already_answered(uid, q_id):
        await callback.answer("⚠️ Allaqachon javob bergansiz!", show_alert=True); return
    q = db.get_question_by_id(q_id)
    if not q: await callback.answer(); return
    _, q_text, q_type, options, correct, coins, cat, diff, expl, img, tl = q
    is_correct = ua.upper() == cl.upper()
    db.save_answer(uid, q_id, is_correct)
    if uid in active_timers: active_timers[uid].cancel(); active_timers.pop(uid, None)
    data = await state.get_data()
    cat2 = data.get("category", "Barchasi")
    mode = data.get("qmode", "all")
    if is_correct:
        ns = db.update_streak(uid, True)
        bonus = streak_bonus(ns)
        earned = round(coins * bonus, 1)
        db.add_coins(uid, earned)
        db.add_league_points(uid, 2)
        text = f"✅ <b>To'g'ri!</b> +{earned} coin"
        if bonus > 1: text += f" 🔥x{bonus}"
        try: await bot.send_sticker(callback.message.chat.id, sticker=STICKER_CORRECT)
        except: pass
    else:
        db.update_streak(uid, False)
        penalty = round(coins * PENALTY_PERCENT, 1)
        db.add_coins(uid, -penalty)
        opts_list = options.split("|")
        ci = ord(correct.upper()) - 65
        ct = opts_list[ci] if ci < len(opts_list) else correct
        text = f"❌ <b>Noto'g'ri!</b> -{penalty} coin\n✅ To'g'ri: <b>{ct}</b>"
        try: await bot.send_sticker(callback.message.chat.id, sticker=STICKER_WRONG)
        except: pass
    if expl: text += f"\n\n💡 <i>{expl}</i>"
    ud = db.get_user(uid)
    if ud: text += f"\n\n💰 {round(ud[3],1)}  🔥 {ud[6]}"
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer(text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="➡️ Keyingi", callback_data=f"next_{mode}_{cat2}")]]))
    await callback.answer()

@dp.message(UserSt.open_ans)
async def handle_open_ans(message: types.Message, state: FSMContext):
    if message.text in MENU_TEXTS:
        await state.clear()
        await route_menu(message, state); return
    data = await state.get_data()
    q_id = data["question_id"]
    correct = data["correct"]
    coins = data["coins"]
    expl = data.get("explanation", "")
    cat = data.get("category", "Barchasi")
    mode = data.get("qmode", "all")
    uid = message.from_user.id
    if db.already_answered(uid, q_id): await state.clear(); return
    is_correct = check_ans(message.text, correct)
    db.save_answer(uid, q_id, is_correct)
    if uid in active_timers: active_timers[uid].cancel(); active_timers.pop(uid, None)
    if is_correct:
        ns = db.update_streak(uid, True)
        bonus = streak_bonus(ns)
        earned = round(coins * bonus, 1)
        db.add_coins(uid, earned)
        db.add_league_points(uid, 2)
        text = f"✅ <b>To'g'ri!</b> +{earned} coin"
        if bonus > 1: text += f" 🔥x{bonus}"
    else:
        db.update_streak(uid, False)
        penalty = round(coins * PENALTY_PERCENT, 1)
        db.add_coins(uid, -penalty)
        fc = correct.split("\n")[0].strip()
        text = f"❌ <b>Noto'g'ri!</b> -{penalty} coin\n✅ To'g'ri: <b>{fc}</b>"
    if expl: text += f"\n\n💡 <i>{expl}</i>"
    ud = db.get_user(uid)
    if ud: text += f"\n\n💰 {round(ud[3],1)}  🔥 {ud[6]}"
    await message.answer(text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="➡️ Keyingi", callback_data=f"next_{mode}_{cat}")]]))
    await state.clear()

@dp.callback_query(F.data.startswith("skip_open_"))
async def skip_open(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cat = data.get("category", "Barchasi")
    mode = data.get("qmode", "all")
    await state.clear()
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer("⏭ O'tkazildi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="➡️ Keyingi", callback_data=f"next_{mode}_{cat}")]]))
    await callback.answer()

@dp.callback_query(F.data.startswith("next_"))
async def next_q(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_", 2)
    mode, cat = parts[1], parts[2]
    await state.update_data(category=cat, qmode=mode)
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await send_question(callback.message, callback.from_user.id, state, cat, mode)
    await callback.answer()

@dp.callback_query(F.data.startswith("go_cats"))
async def go_cats(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    cats = db.get_categories()
    buttons = []
    row = []
    for cat in cats:
        row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat_{cat}"))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🌐 Barchasi", callback_data="cat_Barchasi")])
    await callback.message.answer("📂 Kategoriya tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

# Premium
async def send_premium(message, uid, state, category):
    q = db.get_random_question(uid, category, q_type="premium")
    if not q:
        await message.answer("😔 Premium savollar tugadi!"); return
    q_id, q_text, q_type, options, correct, coins, cat, diff, expl, img, tl = q
    await state.set_state(UserSt.premium)
    await state.update_data(question_id=q_id, correct=correct, coins=coins, explanation=expl, category=category, attempts=0)
    header = (f"⭐ <b>PREMIUM</b>  📂 <b>{cat}</b>\n"
              f"💰 +{coins}  🔄 3 urinish\n\n❓ <b>{q_text}</b>")
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⏭ O'tkazish", callback_data=f"skip_prem_{q_id}_{category}")]])
    if img:
        try: await bot.send_photo(message.chat.id, photo=img, caption=header+"\n\n✍️ Javob:", parse_mode="HTML")
        except: await message.answer(header+"\n\n✍️ Javob:", parse_mode="HTML")
    else:
        await message.answer(header+"\n\n✍️ Javob:", parse_mode="HTML")
    await message.answer("👆", reply_markup=skip_kb)

@dp.message(UserSt.premium)
async def handle_premium(message: types.Message, state: FSMContext):
    if message.text in MENU_TEXTS:
        await state.clear(); await route_menu(message, state); return
    data = await state.get_data()
    q_id, correct, coins = data["question_id"], data["correct"], data["coins"]
    expl = data.get("explanation", "")
    cat = data.get("category", "Barchasi")
    attempts = data.get("attempts", 0)
    uid = message.from_user.id
    if db.already_answered(uid, q_id): await state.clear(); return
    if check_ans(message.text, correct):
        db.save_answer(uid, q_id, True)
        ns = db.update_streak(uid, True)
        earned = round(coins * streak_bonus(ns), 1)
        db.add_coins(uid, earned)
        text = f"✅ +{earned} coin"
        if expl: text += f"\n\n💡 <i>{expl}</i>"
        await message.answer(text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⭐ Keyingi premium", callback_data=f"prem_{cat}")]]))
        await state.clear()
    else:
        attempts += 1
        rem = 3 - attempts
        if rem > 0:
            await state.update_data(attempts=attempts)
            await message.answer(f"❌ Noto'g'ri! <b>{rem}</b> urinish qoldi.", parse_mode="HTML")
        else:
            db.save_answer(uid, q_id, False)
            db.update_streak(uid, False)
            await message.answer("😔 3 urinish tugadi.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="⭐ Keyingi premium", callback_data=f"prem_{cat}")]]))
            await state.clear()

@dp.callback_query(F.data.startswith("prem_"))
async def prem_next(callback: types.CallbackQuery, state: FSMContext):
    await send_premium(callback.message, callback.from_user.id, state, callback.data[5:])
    await callback.answer()

@dp.callback_query(F.data.startswith("skip_prem_"))
async def skip_prem(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    q_id, cat = int(parts[2]), parts[3]
    db.save_answer(callback.from_user.id, q_id, False)
    await state.clear()
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer("⏭",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⭐ Keyingi premium", callback_data=f"prem_{cat}")]]))
    await callback.answer()

# ══════════════════════════════════════════════════════════════════════════════
# REYTING / PROFIL / YORDAM
# ══════════════════════════════════════════════════════════════════════════════
@dp.message(F.text == "🏆 Reyting")
async def show_leaderboard(message: types.Message):
    top = db.get_leaderboard(10)
    if not top: await message.answer("😔 Hali hech kim yo'q!"); return
    try: await bot.send_sticker(message.chat.id, sticker=STICKER_LEADERBOARD)
    except: pass
    medals = ["🥇","🥈","🥉"]
    text = "🏆 <b>Global Reyting — Top 10</b>\n\n"
    for i, (uid, fname, uname, coins) in enumerate(top):
        m = medals[i] if i < 3 else f"{i+1}."
        name = fname or uname or str(uid)
        text += f"{m} <b>{name}</b> — {round(coins,1)} coin\n"
    rank = db.get_user_rank(message.from_user.id)
    text += f"\n📍 Sizning o'rningiz: <b>#{rank}</b>"
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "👤 Profilim")
async def show_profile(message: types.Message):
    uid = message.from_user.id
    user = db.get_user(uid)
    if not user: await message.answer("Profil topilmadi! /start bosing."); return
    _, username, fname, coins, total, correct, streak, max_streak, join = user
    rank = db.get_user_rank(uid)
    acc = round(correct/total*100, 1) if total else 0
    ref = db.get_ref_count(uid)
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref{uid}"
    sub_status = "\n🛡 <b>Yordamchi Admin</b>" if is_sub_admin(uid) else ""
    await message.answer(
        f"👤 <b>{fname}</b>{sub_status}\n\n"
        f"💰 {round(coins,1)} coin  🏆 #{rank}\n"
        f"🔥 Streak: {streak}  ⚡ Max: {max_streak}\n"
        f"📝 Javoblar: {total}  ✅ To'g'ri: {correct}\n"
        f"🎯 Aniqlik: {acc}%\n"
        f"📅 Qo'shilgan: {join[:10]}\n\n"
        f"👥 Taklif qilinganlar: {ref} ta\n"
        f"🔗 <code>{ref_link}</code>",
        parse_mode="HTML")

@dp.message(F.text == "👥 Guruhga ulash")
async def guruhga_ulash(message: types.Message):
    me = await bot.get_me()
    url = f"https://t.me/{me.username}?startgroup=start"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👥 Guruhni tanlang", url=url)]])
    await message.answer(
        "👥 <b>Botni guruhga qo'shish</b>\n\n"
        "Tugmani bosib guruhingizni tanlang.\n\n"
        "Guruhda:\n• /savol — yangi savol\n• /reyting — guruh reytingi\n• /stat — statistika",
        parse_mode="HTML", reply_markup=kb)

@dp.message(F.text == "ℹ️ Yordam")
async def show_help(message: types.Message):
    me = await bot.get_me()
    url = f"https://t.me/{me.username}?startgroup=start"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👥 Guruhga qo'shish", url=url)]])
    await message.answer(
        "ℹ️ <b>BilimChallenge</b>\n\n"
        "🎯 Savol olish | 🎓 IELTS | 🤖 AI Chat\n"
        "⚔️ Duel | 🏅 Liga | 👥 Do'st taklif (+30)\n\n"
        "💰 To'g'ri → coin\n❌ Noto'g'ri → -30%\n⏰ Vaqt → -45%\n"
        "🔥x3=1.5x x5=2.0x x10=3.0x\n"
        "🟢Oson=30s 🟡O'rta=60s 🔴Qiyin=90s",
        parse_mode="HTML", reply_markup=kb)

# ══════════════════════════════════════════════════════════════════════════════
# FEEDBACK
# ══════════════════════════════════════════════════════════════════════════════
@dp.message(F.text == "📝 Taklif/Shikoyat")
async def feedback_start(message: types.Message, state: FSMContext):
    await state.set_state(UserSt.feedback)
    await message.answer("📝 Taklif yoki shikoyatingizni yozing:\n<i>/cancel — bekor</i>", parse_mode="HTML")

@dp.message(UserSt.feedback)
async def recv_feedback(message: types.Message, state: FSMContext):
    if message.text in MENU_TEXTS: await state.clear(); await route_menu(message, state); return
    u = message.from_user
    db.save_feedback(u.id, u.first_name or "", u.username or "", message.text)
    await state.clear()
    await message.answer("✅ Yuborildi!", reply_markup=main_menu(u.id))

# ══════════════════════════════════════════════════════════════════════════════
# IELTS
# ══════════════════════════════════════════════════════════════════════════════
@dp.message(F.text == "🎓 IELTS")
async def ielts_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Writing", callback_data="ielts_writing"),
         InlineKeyboardButton(text="✍️ Essay",   callback_data="ielts_essay")],
        [InlineKeyboardButton(text="📖 Reading", callback_data="ielts_reading"),
         InlineKeyboardButton(text="🗣 Speaking", callback_data="ielts_speaking")],
        [InlineKeyboardButton(text="🎧 Listening", callback_data="ielts_listening")]])
    await message.answer("🎓 <b>IELTS bo'limlari</b>", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("ielts_"))
async def ielts_section(callback: types.CallbackQuery, state: FSMContext):
    section = callback.data[6:]
    q = db.get_random_question(callback.from_user.id, q_type=section)
    if not q:
        await callback.answer("🎉 Barcha savollarga javob berdingiz!", show_alert=True); return
    q_id, q_text, q_type, options, correct, coins, cat, diff, expl, img, tl = q
    await state.set_state(UserSt.ielts)
    await state.update_data(question_id=q_id, coins=coins, section=section)
    tl_note = f"\n⏰ {tl}" if tl else ""
    icons = {"writing":"📝","essay":"✍️","reading":"📖","speaking":"🗣","listening":"🎧"}
    header = f"{icons.get(section,'🎓')} <b>{section.upper()}</b>  #{q_id}{tl_note}\n\n"
    if section == "reading":
        parts = q_text.split("---")
        if len(parts) >= 2:
            header += f"📄 <b>Matn:</b>\n{parts[0].strip()}\n\n❓ <b>Savollar:</b>\n{'---'.join(parts[1:]).strip()}"
        else:
            header += f"❓ <b>{q_text}</b>"
        header += "\n\n📌 <i>Javoblarni qatorma-qator yozing</i>"
    elif section == "essay":
        header += f"✍️ <b>Mavzu:</b>\n{q_text}\n\n📝 <i>O'ZBEK TILIDA insho yozing (min 150 so'z)</i>"
    elif section == "writing":
        header += f"📝 <b>Vazifa:</b>\n{q_text}\n\n✍️ <i>Ingliz tilida yozing (min 150 so'z)</i>"
    elif section == "speaking":
        header += f"🗣 <b>Savol:</b>\n{q_text}\n\n🎙 <i>Ovozli xabar yuboring yoki matn yozing</i>"
    elif section == "listening":
        header += f"🎧 <b>Topshiriq:</b>\n{q_text}\n\n🎙 <i>Javobingizni yozing</i>"
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⏭ O'tkazish", callback_data=f"skip_ielts_{section}")]])
    if img and section == "listening":
        try: await bot.send_audio(callback.message.chat.id, audio=img, caption=header[:1024], parse_mode="HTML")
        except:
            try: await bot.send_voice(callback.message.chat.id, voice=img)
            except: pass
            await send_long(callback.message.chat.id, header, parse_mode="HTML")
    elif img:
        try:
            if len(header) <= 1024:
                await bot.send_photo(callback.message.chat.id, photo=img, caption=header, parse_mode="HTML")
            else:
                await bot.send_photo(callback.message.chat.id, photo=img)
                await send_long(callback.message.chat.id, header, parse_mode="HTML")
        except:
            await send_long(callback.message.chat.id, header, parse_mode="HTML")
    else:
        await send_long(callback.message.chat.id, header, parse_mode="HTML")
    await callback.message.answer("👆 Javob yuboring:", reply_markup=skip_kb)
    await callback.answer()

@dp.message(UserSt.ielts)
async def handle_ielts(message: types.Message, state: FSMContext):
    if message.text in MENU_TEXTS: await state.clear(); await route_menu(message, state); return
    data = await state.get_data()
    q_id, coins, section = data["question_id"], data["coins"], data["section"]
    uid = message.from_user.id
    if section == "reading":
        if not message.text: await message.answer("✍️ Matn yuboring!"); return
        q = db.get_question_by_id(q_id)
        correct_ans = q[4] if q else ""
        uas = [a.strip().lower() for a in message.text.split("\n") if a.strip()]
        cls = [a.strip().lower() for a in correct_ans.split("\n") if a.strip()]
        cc = sum(1 for a in uas if a in cls)
        total = len(cls)
        earned = round(coins * (cc/total), 1) if total else 0
        db.add_coins(uid, earned)
        try: db.save_answer(uid, q_id, cc == total)
        except: pass
        result = f"📖 <b>Reading natijasi</b>\n\n✅ {cc}/{total}  💰 +{earned}"
        if cc < total:
            wrong = [a for a in cls if a not in uas]
            result += "\n❌ To'g'ri javoblar:\n" + "\n".join(f"• {w}" for w in wrong)
        await message.answer(result, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=f"➡️ Keyingi", callback_data=f"ielts_{section}")]]))
        await state.clear(); return
    if message.text and is_lazy(message.text):
        await state.clear()
        try: db.save_answer(uid, q_id, False)
        except: pass
        await message.answer("❌ 0 coin — sifatsiz javob!\nTo'liq javob yozing.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Qayta", callback_data=f"ielts_{section}")]]))
        return
    if section == "essay":
        if not message.text: await message.answer("✍️ Matn yuboring!"); return
        if not is_uzbek(message.text):
            await state.clear()
            await message.answer("❌ 0 coin — O'ZBEK TILIDA yozing!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="🔄 Qayta", callback_data=f"ielts_{section}")]]))
            return
        await message.answer("⏳ AI tahlil qilmoqda...")
        prompt = (f"O'zbek tili insho baholovchisisiz. O'ZBEK TILIDA baholang:\n\n{message.text}\n\n"
                  f"Baholash: Mavzuga mosligi, Tuzilma, Argumentlar, Uslub, Grammatika.\n"
                  f"Umumiy baho: X/10. Tavsiyalar. Faqat raqam: BAHO:X")
    elif section == "writing":
        if not message.text: await message.answer("✍️ Matn yuboring!"); return
        await message.answer("⏳ AI tahlil qilmoqda...")
        prompt = (f"IELTS Writing baholovchisisiz. O'ZBEK TILIDA baholang:\n\n{message.text}\n\n"
                  f"Task Achievement, Coherence, Lexical Resource, Grammar.\n"
                  f"Band Score: X.X/9.0. Tavsiyalar. Faqat: BAND:X.X")
    elif section in ("speaking","listening"):
        if message.voice:
            await message.answer("⏳ Tahlil...")
            prompt = (f"IELTS {section} baholovchisisiz. O'ZBEK TILIDA baholang. "
                      f"Foydalanuvchi ovozli xabar yubordi. Umumiy tavsiyalar. BAND:X.X")
        elif message.text:
            await message.answer("⏳ AI tahlil...")
            prompt = (f"IELTS {section} baholovchisisiz. O'ZBEK TILIDA baholang:\n\n{message.text}\n\n"
                      f"BAND:X.X. Tavsiyalar.")
        else:
            await message.answer("🎙 Ovozli xabar yoki matn yuboring!"); return
    else:
        await message.answer("❓ Noma'lum bo'lim."); return
    analysis = await ai_req(prompt)
    earned = 0
    band = None
    if section == "essay":
        m = re.search(r'BAHO[:\s]+(\d+\.?\d*)', analysis, re.IGNORECASE)
        if m:
            try:
                v = float(m.group(1))
                v = min(v, 10)
                earned = round(coins * (v/10), 1) if v >= 3 else 0
            except: pass
        if not earned: earned = round(coins * 0.3, 1)
    else:
        m = re.search(r'BAND[:\s]+(\d+\.?\d*)', analysis, re.IGNORECASE)
        if m:
            try:
                band = float(m.group(1))
                band = min(band, 9)
                earned = round(coins * (band/9), 1) if band >= 3 else 0
            except: pass
        if not earned: earned = round(coins * 0.3, 1)
    db.add_coins(uid, earned)
    try: db.save_answer(uid, q_id, earned > 0)
    except: pass
    score_text = f"\n🎯 Band: <b>{band}/9.0</b>" if band else ""
    await send_long(message.chat.id,
        f"🤖 <b>AI Tahlil:</b>\n\n{analysis}{score_text}\n\n💰 +{earned} coin (max {coins})",
        parse_mode="HTML")
    await message.answer("➡️",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=f"➡️ Keyingi {section.upper()}", callback_data=f"ielts_{section}")]]))
    await state.clear()

@dp.callback_query(F.data.startswith("skip_ielts_"))
async def skip_ielts(callback: types.CallbackQuery, state: FSMContext):
    section = callback.data[11:]
    await state.clear()
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer("⏭",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=f"➡️ Keyingi", callback_data=f"ielts_{section}")]]))
    await callback.answer()

# ══════════════════════════════════════════════════════════════════════════════
# AI CHAT
# ══════════════════════════════════════════════════════════════════════════════
ILLEGAL = {"bomb","portlat","terror","narkotik","hack","qotil"}

@dp.message(F.text == "🤖 AI Chat")
async def ai_chat_start(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    user = db.get_user(uid)
    coins = round(user[3], 1) if user else 0
    if coins <= 0:
        await message.answer(f"❌ AI Chat uchun coin kerak!\nHozir: <b>{coins}</b>\nAvval savollarga javob bering.",
            parse_mode="HTML"); return
    await state.set_state(UserSt.ai_chat)
    await state.update_data(history=[])
    await message.answer(
        f"🤖 <b>AI Chat</b>\n\n💰 {coins} coin\n💸 Har 15 belgi = 1 coin\n\n"
        f"Savolingizni yozing!\n<i>/cancel yoki '🚪 Chiqish' tugmasi</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🚪 AI Chatdan chiqish")]],
                                         resize_keyboard=True))

@dp.message(F.text == "🚪 AI Chatdan chiqish")
async def ai_exit(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 Chiqildi!", reply_markup=main_menu(message.from_user.id))

@dp.message(UserSt.ai_chat)
async def handle_ai(message: types.Message, state: FSMContext):
    if not message.text: return
    uid = message.from_user.id
    text = message.text.strip()
    if text in MENU_TEXTS: await state.clear(); await route_menu(message, state); return
    for w in ILLEGAL:
        if w in text.lower():
            db.add_coins(uid, -10)
            await message.answer("🚫 <b>Taqiqlangan so'z!</b> -10 coin", parse_mode="HTML"); return
    user = db.get_user(uid)
    coins = round(user[3], 1) if user else 0
    if coins <= 0:
        await state.clear()
        await message.answer("❌ Coinlar tugadi!", reply_markup=main_menu(uid)); return
    data = await state.get_data()
    history = data.get("history", [])
    thinking = await message.answer("⏳ AI o'ylayapti...")
    try:
        reply = await ai_chat(history, text)
    except Exception as e:
        logging.error(f"AI chat error: {e}")
        reply = None
    try: await thinking.delete()
    except: pass
    if not reply or reply.startswith("⚠️"):
        await message.answer(
            "⚠️ <b>AI hozirda ishlamayapti.</b>\n\n"
            "Groq API bilan bog'lanishda xato. Keyinroq urinib ko'ring.",
            parse_mode="HTML")
        return
    cost = max(1, len(reply) // 15)
    if coins < cost:
        await state.update_data(pending_reply=reply, pending_cost=cost, history=history)
        await state.set_state(UserSt.ai_debt)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Qarz olaman", callback_data="ai_debt_yes"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="ai_debt_no")]])
        await message.answer(
            f"⚠️ Coin yetmaydi!\nKerak: <b>{cost}</b>  Sizda: <b>{coins}</b>\nQarz olasizmi?",
            parse_mode="HTML", reply_markup=kb)
        return
    db.add_coins(uid, -cost)
    history.append({"role":"user","content":text})
    history.append({"role":"assistant","content":reply})
    await state.update_data(history=history)
    await state.set_state(UserSt.ai_chat)
    ud = db.get_user(uid)
    coins_left = round(ud[3], 1) if ud else 0
    await message.answer(f"🤖 {reply}\n\n💰 -{cost} coin  |  Qoldi: <b>{coins_left}</b>", parse_mode="HTML")

@dp.callback_query(F.data == "ai_debt_yes")
async def ai_debt_yes(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    reply, cost, history = data["pending_reply"], data["pending_cost"], data.get("history",[])
    uid = callback.from_user.id
    db.add_coins(uid, -cost)
    history.append({"role":"assistant","content":reply})
    await state.update_data(history=history)
    await state.set_state(UserSt.ai_chat)
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    ud = db.get_user(uid)
    await callback.message.answer(f"🤖 {reply}\n\n💰 -{cost}  Qoldi: {round(ud[3],1)}", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "ai_debt_no")
async def ai_debt_no(callback: types.CallbackQuery, state: FSMContext):
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await state.set_state(UserSt.ai_chat)
    await callback.message.answer("❌ Bekor.")
    await callback.answer()

# ══════════════════════════════════════════════════════════════════════════════
# DUEL TIZIMI
# ══════════════════════════════════════════════════════════════════════════════
@dp.message(F.text == "⚔️ Duel")
async def duel_menu(message: types.Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    user = db.get_user(uid)
    if not user: await message.answer("Avval /start bosing!"); return

    pending = db.get_pending_duel(uid)
    if pending:
        d_id, ch_id, op_id, bet, status, winner, ch_sc, op_sc, total, created = pending
        ch = db.get_user(ch_id)
        ch_name = ch[2] if ch else str(ch_id)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Qabul", callback_data=f"duel_accept_{d_id}"),
            InlineKeyboardButton(text="❌ Rad", callback_data=f"duel_decline_{d_id}")]])
        await message.answer(
            f"⚔️ <b>{ch_name}</b> sizni duelga chaqirdi!\n💰 Tikish: <b>{bet} coin</b>\n❓ 5 ta savol",
            parse_mode="HTML", reply_markup=kb)
        return

    active = db.get_active_duel(uid)
    if active:
        d_id = active[0]
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Duerni bekor qilish", callback_data=f"duel_cancel_{d_id}")]])
        await message.answer(
            "\u23f3 <b>Aktiv duelingiz bor!</b>\n\nDuerni bekor qilmoqchimisiz?",
            parse_mode="HTML", reply_markup=kb)
        return

    stats = db.get_duel_stats(uid)
    total_d = stats[0] or 0
    wins = stats[1] or 0
    losses = stats[2] or 0
    coins = round(user[3], 1)

    top = db.get_leaderboard(10)
    buttons = []
    for t_uid, fname, uname, t_coins in top:
        if t_uid == uid: continue
        name = fname or uname or str(t_uid)
        buttons.append([InlineKeyboardButton(
            text=f"⚔️ {name} ({round(t_coins,1)} coin)",
            callback_data=f"duel_ch_{t_uid}_10")])
    buttons.append([InlineKeyboardButton(text="❌ Yopish", callback_data="duel_close")])

    await message.answer(
        f"⚔️ <b>DUEL</b>\n\n💰 Coinlaringiz: <b>{coins}</b>\n"
        f"🏆 G'alaba: {wins}  ❌ Yutqazish: {losses}  🤝 Durrang: {total_d-wins-losses}\n\n"
        f"Raqib tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("duel_ch_"))
async def duel_challenge(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    op_id = int(parts[2])
    bet = float(parts[3])
    ch_id = callback.from_user.id
    if ch_id == op_id:
        await callback.answer("O'zingizga duel bo'lmaydi!", show_alert=True); return
    ch = db.get_user(ch_id)
    op = db.get_user(op_id)
    if not ch or ch[3] < bet:
        await callback.answer(f"Coin yetmaydi! Kerak: {bet}", show_alert=True); return
    if not op or op[3] < bet:
        await callback.answer("Raqibda coin yetmaydi!", show_alert=True); return
    if db.get_active_duel(ch_id) or db.get_active_duel(op_id):
        await callback.answer("Biri aktiv duelda!", show_alert=True); return

    d_id = db.create_duel(ch_id, op_id, bet)
    ch_name = ch[2] or str(ch_id)
    op_name = op[2] or str(op_id)
    try:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Qabul", callback_data=f"duel_accept_{d_id}"),
            InlineKeyboardButton(text="❌ Rad", callback_data=f"duel_decline_{d_id}")]])
        await bot.send_message(op_id,
            f"⚔️ <b>{ch_name}</b> sizni duelga chaqirdi!\n💰 Tikish: <b>{bet} coin</b>\n❓ 5 ta savol",
            parse_mode="HTML", reply_markup=kb)
    except:
        await callback.answer("Raqibga xabar yuborib bo'lmadi!", show_alert=True)
        db.decline_duel(d_id); return

    await callback.message.edit_text(f"✅ <b>{op_name}</b> ga duel so'rovi yuborildi!", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("duel_accept_"))
async def duel_accept(callback: types.CallbackQuery):
    d_id = int(callback.data[12:])
    duel = db.get_duel(d_id)
    if not duel or duel[4] != 'pending':
        await callback.answer("Duel topilmadi!", show_alert=True); return
    _, ch_id, op_id, bet, *_ = duel
    if callback.from_user.id != op_id:
        await callback.answer("Bu sizning duelingiz emas!", show_alert=True); return

    ch = db.get_user(ch_id)
    op = db.get_user(op_id)
    if not ch or ch[3] < bet or not op or op[3] < bet:
        await callback.answer("Coin yetmaydi!", show_alert=True)
        db.decline_duel(d_id); return

    db.add_coins(ch_id, -bet)
    db.add_coins(op_id, -bet)
    db.accept_duel(d_id)

    q_ids = db.get_random_test_questions(5)
    if len(q_ids) < 3:
        await callback.answer("Savollar yetmaydi!", show_alert=True)
        db.add_coins(ch_id, bet); db.add_coins(op_id, bet); return

    db.set_duel_questions(d_id, q_ids)
    ch_name = ch[2] or str(ch_id)
    op_name = op[2] or str(op_id)
    start_text = (f"⚔️ <b>DUEL BOSHLANDI!</b>\n\n"
                  f"👤 {ch_name} vs {op_name}\n"
                  f"💰 Tikish: {bet} coin  ❓ {len(q_ids)} savol\n"
                  f"🏆 G'olib 2x coin oladi!")
    try: await bot.send_message(ch_id, start_text, parse_mode="HTML")
    except Exception as e: logging.error(f"duel start ch: {e}")
    try: await callback.message.edit_text(start_text, parse_mode="HTML")
    except: pass
    # Birinchi savolni yuborish - asyncio.sleep bilan ishonchli qilish
    await asyncio.sleep(0.5)
    await send_duel_q(ch_id, d_id)
    await asyncio.sleep(0.3)
    await send_duel_q(op_id, d_id)
    await callback.answer("✅ Duel boshlandi!")

@dp.callback_query(F.data.startswith("duel_decline_"))
async def duel_decline(callback: types.CallbackQuery):
    d_id = int(callback.data[13:])
    duel = db.get_duel(d_id)
    if not duel: await callback.answer(); return
    _, ch_id, op_id, *_ = duel
    db.decline_duel(d_id)
    op = db.get_user(op_id)
    op_name = op[2] if op else str(op_id)
    try: await bot.send_message(ch_id, f"❌ <b>{op_name}</b> duelni rad etdi.", parse_mode="HTML")
    except: pass
    await callback.message.edit_text("❌ Duel rad etildi.")
    await callback.answer()

@dp.callback_query(F.data == "duel_close")
async def duel_close_cb(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Yopildi.")
    await callback.answer()

@dp.callback_query(F.data.startswith("duel_cancel_"))
async def duel_cancel_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    d_id = int(callback.data[12:])
    duel = db.get_duel(d_id)
    if not duel:
        await callback.answer("Duel topilmadi!", show_alert=True); return
    _, ch_id, op_id, bet, status, *_ = duel
    # Faqat ikki tomondagidan biri bekor qila oladi
    if uid not in (ch_id, op_id):
        await callback.answer("Bu sizning duelingiz emas!", show_alert=True); return
    if status == "finished":
        await callback.answer("Duel allaqachon tugagan!", show_alert=True); return
    # Coinlarni qaytarish agar active bo'lsa
    if status == "active":
        db.add_coins(ch_id, bet)
        db.add_coins(op_id, bet)
    db.decline_duel(d_id)
    other_id = op_id if uid == ch_id else ch_id
    other = db.get_user(other_id)
    me = db.get_user(uid)
    my_name = me[2] if me else str(uid)
    try:
        coin_msg = f"\n\U0001f4b0 {bet} coin qaytarildi." if status == "active" else ""
        await bot.send_message(other_id,
            f"\u274c <b>{my_name}</b> duelni bekor qildi." + coin_msg,
            parse_mode="HTML")
    except: pass
    coin_msg2 = f"\n\U0001f4b0 {bet} coin qaytarildi." if status == "active" else ""
    await callback.message.edit_text("\u274c Duel bekor qilindi." + coin_msg2)
    await callback.answer("\u2705 Duel bekor qilindi!")

async def send_duel_q(uid, d_id):
    duel = db.get_duel(d_id)
    if not duel: return
    _, ch_id, op_id, bet, status, winner, ch_sc, op_sc, total, created = duel
    q_ids = db.get_duel_questions(d_id)
    answered = db.get_duel_answer_count(d_id, uid)
    if answered >= len(q_ids):
        await check_duel_end(d_id); return
    q_id = q_ids[answered]
    q = db.get_question_by_id(q_id)
    if not q: return
    _, q_text, q_type, options, correct, coins, cat, diff, expl, img, tl = q
    d_icon = DIFF_ICONS.get(diff, "🟡")
    sh_opts, new_cor = shuffle_opts(options, correct)
    opts_list = sh_opts.split("|")
    opts_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(opts_list)])
    header = (f"⚔️ <b>DUEL</b>  {d_icon}  {answered+1}/{len(q_ids)}\n\n"
              f"❓ <b>{q_text}</b>\n\n{opts_text}")
    kb = build_opts_kb(opts_list, q_id, new_cor, f"duelans_{d_id}")
    try:
        await bot.send_message(uid, header, parse_mode="HTML", reply_markup=kb)
        logging.info(f"Duel savol {answered+1} yuborildi: uid={uid} d_id={d_id}")
    except Exception as e:
        logging.error(f"send_duel_q uid={uid}: {e}")

@dp.callback_query(F.data.startswith("duelans_"))
async def duel_answer(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    d_id = int(parts[1])
    q_id = int(parts[2])
    ua = parts[3]
    new_cor = parts[4]
    uid = callback.from_user.id
    duel = db.get_duel(d_id)
    if not duel or duel[4] != 'active':
        await callback.answer("Duel aktiv emas!", show_alert=True); return
    cur = db.get_conn().cursor()
    cur.execute("SELECT 1 FROM duel_answers WHERE duel_id=%s AND user_id=%s AND question_id=%s", (d_id, uid, q_id))
    if cur.fetchone():
        await callback.answer("Allaqachon javob bergansiz!", show_alert=True); return
    is_correct = ua.upper() == new_cor.upper()
    db.save_duel_answer(d_id, uid, q_id, is_correct)
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer("✅ To'g'ri!" if is_correct else "❌ Noto'g'ri!")
    await send_duel_q(uid, d_id)
    await callback.answer()

async def check_duel_end(d_id):
    duel = db.get_duel(d_id)
    if not duel or duel[4] != 'active': return
    _, ch_id, op_id, bet, status, winner, ch_sc, op_sc, total, created = duel
    q_ids = db.get_duel_questions(d_id)
    total_q = len(q_ids)
    ch_ans = db.get_duel_answer_count(d_id, ch_id)
    op_ans = db.get_duel_answer_count(d_id, op_id)
    if ch_ans < total_q or op_ans < total_q: return
    result = db.finish_duel(d_id)
    if not result: return
    winner_id, final_ch, final_op = result
    ch = db.get_user(ch_id)
    op = db.get_user(op_id)
    ch_name = ch[2] if ch else str(ch_id)
    op_name = op[2] if op else str(op_id)
    prize = bet * 2
    if winner_id:
        loser_id = op_id if winner_id == ch_id else ch_id
        db.add_coins(winner_id, prize)
        db.add_league_points(winner_id, 20)
        db.add_league_points(loser_id, 5)
        w_name = ch_name if winner_id == ch_id else op_name
        result_text = (f"🏆 <b>DUEL YAKUNLANDI!</b>\n\n"
                       f"👤 {ch_name}: <b>{final_ch}</b> ✅\n"
                       f"👤 {op_name}: <b>{final_op}</b> ✅\n\n"
                       f"🥇 G'olib: <b>{w_name}</b>\n"
                       f"💰 +{prize} coin  📈 +20 liga ball")
    else:
        db.add_coins(ch_id, bet)
        db.add_coins(op_id, bet)
        db.add_league_points(ch_id, 10)
        db.add_league_points(op_id, 10)
        result_text = (f"🤝 <b>DURRANG!</b>\n\n"
                       f"👤 {ch_name}: <b>{final_ch}</b>\n"
                       f"👤 {op_name}: <b>{final_op}</b>\n\n"
                       f"Coinlar qaytarildi. +10 liga ball")
    try: await bot.send_message(ch_id, result_text, parse_mode="HTML")
    except: pass
    try: await bot.send_message(op_id, result_text, parse_mode="HTML")
    except: pass

# ══════════════════════════════════════════════════════════════════════════════
# LIGA TIZIMI
# ══════════════════════════════════════════════════════════════════════════════
@dp.message(F.text == "🏅 Liga")
async def liga_menu(message: types.Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    ld = db.get_or_create_league(uid)
    if not ld: await message.answer("Xato!"); return
    u_id, league, points, week_pts, season, updated = ld
    icon = LEAGUE_ICONS.get(league, "🥉")
    next_leagues = {"bronza":"kumush","kumush":"oltin","oltin":"platina","platina":"olmos"}
    nl = next_leagues.get(league)
    progress = ""
    if nl:
        need = LEAGUE_PTS[nl] - points
        nl_icon = LEAGUE_ICONS.get(nl, "")
        progress = f"\n⬆️ Keyingi: {nl_icon} {nl.capitalize()} — {need} ball"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{icon} Liga reytingi", callback_data=f"liga_top_{league}")],
        [InlineKeyboardButton(text="🌍 Umumiy reyting",   callback_data="liga_top_all")],
        [InlineKeyboardButton(text="📅 Haftalik reyting", callback_data="liga_weekly")]])
    await message.answer(
        f"{icon} <b>{league.upper()} LIGA</b>\n\n"
        f"📊 Ball: <b>{points}</b>\n"
        f"📅 Bu hafta: <b>{week_pts}</b>{progress}\n\n"
        f"Ball qanday yig'iladi:\n"
        f"⚔️ Duel g'alaba +20  🤝 Durrang +10  ❌ +5\n"
        f"✅ To'g'ri javob +2",
        parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("liga_top_"))
async def liga_top(callback: types.CallbackQuery):
    lf = callback.data[9:]
    if lf == "all":
        top = db.get_league_leaderboard(limit=10)
        title = "🌍 Umumiy Liga Reytingi"
    else:
        top = db.get_league_leaderboard(league=lf, limit=10)
        icon = LEAGUE_ICONS.get(lf, "🏅")
        title = f"{icon} {lf.capitalize()} Liga"
    if not top:
        await callback.answer("Hali hech kim yo'q!", show_alert=True); return
    medals = ["🥇","🥈","🥉"]
    text = f"<b>{title}</b>\n\n"
    for i, (uid, fname, uname, pts, lg) in enumerate(top):
        m = medals[i] if i < 3 else f"{i+1}."
        name = fname or uname or str(uid)
        icon = LEAGUE_ICONS.get(lg, "🥉")
        text += f"{m} {icon} <b>{name}</b> — {pts}\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="liga_back")]])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "liga_weekly")
async def liga_weekly(callback: types.CallbackQuery):
    top = db.get_weekly_leaderboard(10)
    if not top:
        await callback.answer("Hali hech kim yo'q!", show_alert=True); return
    medals = ["🥇","🥈","🥉"]
    text = "📅 <b>Haftalik Reyting</b>\n\n"
    for i, (uid, fname, uname, pts, lg) in enumerate(top):
        m = medals[i] if i < 3 else f"{i+1}."
        name = fname or uname or str(uid)
        text += f"{m} <b>{name}</b> — {pts}\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="liga_back")]])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "liga_back")
async def liga_back_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    ld = db.get_or_create_league(uid)
    if not ld: await callback.answer(); return
    u_id, league, points, week_pts, season, updated = ld
    icon = LEAGUE_ICONS.get(league, "🥉")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{icon} Liga reytingi", callback_data=f"liga_top_{league}")],
        [InlineKeyboardButton(text="🌍 Umumiy", callback_data="liga_top_all")],
        [InlineKeyboardButton(text="📅 Haftalik", callback_data="liga_weekly")]])
    await callback.message.edit_text(
        f"{icon} <b>{league.upper()}</b>\n📊 {points} ball  📅 Bu hafta: {week_pts}",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN PANEL
# ══════════════════════════════════════════════════════════════════════════════
@dp.message(F.text == "⚙️ Admin Panel")
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("⚙️ <b>Admin Panel</b>", parse_mode="HTML", reply_markup=admin_menu())

@dp.message(F.text == "🔙 Asosiy menyu")
async def back_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠", reply_markup=main_menu(message.from_user.id))

@dp.message(F.text == "📊 Statistika")
async def admin_stats(message: types.Message):
    if not is_admin(message.from_user.id): return
    s = db.get_stats()
    subs = db.get_all_sub_admins()
    await message.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: {s['users']}\n"
        f"❓ Savollar: {s['questions']}\n"
        f"📝 Javoblar: {s['answers']}\n"
        f"✅ To'g'ri: {s['correct']}\n"
        f"🎯 Aniqlik: {s['accuracy']}%\n"
        f"🛡 Sub-adminlar: {len(subs)}",
        parse_mode="HTML")

@dp.message(F.text == "👥 Foydalanuvchilar")
async def admin_users(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer(
        f"👥 <b>Foydalanuvchilar</b>\n\nJami: <b>{db.get_total_users()}</b>\nFaol: <b>{db.get_active_users()}</b>",
        parse_mode="HTML")

# ── SAVOL QO'SHISH ────────────────────────────────────────────────────────────
@dp.message(F.text == "➕ Savol qo'shish")
async def add_q_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    await state.set_state(AdminSt.q_type)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Test", callback_data="aqt_test"),
         InlineKeyboardButton(text="✍️ Ochiq", callback_data="aqt_open")],
        [InlineKeyboardButton(text="⭐ Premium", callback_data="aqt_premium")],
        [InlineKeyboardButton(text="📝 Writing", callback_data="aqt_writing"),
         InlineKeyboardButton(text="✍️ Essay", callback_data="aqt_essay")],
        [InlineKeyboardButton(text="📖 Reading", callback_data="aqt_reading"),
         InlineKeyboardButton(text="🗣 Speaking", callback_data="aqt_speaking")],
        [InlineKeyboardButton(text="🎧 Listening", callback_data="aqt_listening")]])
    await message.answer("📌 Savol turi:", reply_markup=kb)

@dp.callback_query(F.data.startswith("aqt_"))
async def aq_type(callback: types.CallbackQuery, state: FSMContext):
    qt = callback.data[4:]
    await state.update_data(q_type=qt, accumulated="")
    await state.set_state(AdminSt.q_text)
    await callback.message.edit_text("✏️ Savol matnini kiriting:\n<i>(Uzun matn uchun bir necha xabar yuboring, /done — tugash)</i>", parse_mode="HTML")
    await callback.answer()

@dp.message(AdminSt.q_text)
async def aq_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    qt = data["q_type"]
    if message.text == "/done":
        acc = data.get("accumulated", "")
        if not acc: await message.answer("⚠️ Avval matn yuboring!"); return
        await state.update_data(q_text=acc)
        await _aq_next_after_text(message, state, qt)
        return
    prev = data.get("accumulated", "")
    new_text = (prev + "\n" + message.text).strip() if prev else message.text
    await state.update_data(accumulated=new_text)
    if qt in ["reading"] + IELTS_TYPES:
        await message.answer(f"✅ Qabul ({len(new_text)} belgi). Davom yoki /done")
    else:
        await state.update_data(q_text=new_text)
        await _aq_next_after_text(message, state, qt)

async def _aq_next_after_text(message, state, qt):
    if qt == "test":
        await state.set_state(AdminSt.q_opts)
        await message.answer("📋 Variantlarni kiriting (har biri yangi qatorda):")
    elif qt in IELTS_TYPES:
        await state.update_data(correct="", options="")
        await state.set_state(AdminSt.q_coins)
        await message.answer("💰 Necha coin?")
    else:
        await state.set_state(AdminSt.q_correct)
        await message.answer("✅ To'g'ri javob:")

@dp.message(AdminSt.q_opts)
async def aq_opts(message: types.Message, state: FSMContext):
    opts = [o.strip() for o in message.text.split("\n") if o.strip()]
    if len(opts) < 2: await message.answer("⚠️ Kamida 2 ta variant!"); return
    await state.update_data(options="|".join(opts))
    await state.set_state(AdminSt.q_correct)
    opts_text = "\n".join([f"{chr(65+i)}. {o}" for i, o in enumerate(opts)])
    await message.answer(f"📋 Variantlar:\n{opts_text}\n\n✅ To'g'ri harf (A/B/C/D):")

@dp.message(AdminSt.q_correct)
async def aq_correct(message: types.Message, state: FSMContext):
    await state.update_data(correct=message.text.strip())
    await state.set_state(AdminSt.q_coins)
    await message.answer("💰 Necha coin?")

@dp.message(AdminSt.q_coins)
async def aq_coins(message: types.Message, state: FSMContext):
    if not message.text.replace(".", "").isdigit():
        await message.answer("⚠️ Faqat raqam!"); return
    await state.update_data(coins=float(message.text))
    data = await state.get_data()
    qt = data["q_type"]
    if qt in IELTS_TYPES + ["premium"]:
        await state.set_state(AdminSt.q_time)
        await message.answer("⏰ Vaqt (masalan: 20 daqiqa) yoki '-':")
    else:
        await state.set_state(AdminSt.q_diff)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Oson", callback_data="adiff_oson"),
             InlineKeyboardButton(text="🟡 O'rta", callback_data="adiff_orta"),
             InlineKeyboardButton(text="🔴 Qiyin", callback_data="adiff_qiyin")]])
        await message.answer("📊 Qiyinlik:", reply_markup=kb)

@dp.message(AdminSt.q_time)
async def aq_time(message: types.Message, state: FSMContext):
    tl = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(time_limit=tl, difficulty="orta")
    data = await state.get_data()
    qt = data["q_type"]
    if qt in IELTS_TYPES:
        await state.update_data(category=qt.upper())
        await state.set_state(AdminSt.q_expl)
        await message.answer("💡 Tavsif yoki '-':")
    else:
        await _show_cat_kb(message, state)

@dp.callback_query(F.data.startswith("adiff_"))
async def aq_diff(callback: types.CallbackQuery, state: FSMContext):
    diff = callback.data[6:]
    await state.update_data(difficulty=diff, time_limit="")
    await _show_cat_kb(callback.message, state)
    await callback.answer()

async def _show_cat_kb(message, state):
    await state.set_state(AdminSt.q_cat)
    cats = db.get_categories()
    buttons = []
    row = []
    for cat in cats:
        row.append(InlineKeyboardButton(text=cat, callback_data=f"acat_{cat}"))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="➕ Yangi", callback_data="acat_NEW")])
    await message.answer("📂 Kategoriya:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("acat_"))
async def aq_cat(callback: types.CallbackQuery, state: FSMContext):
    cat = callback.data[5:]
    if cat == "NEW":
        await callback.message.answer("📂 Yangi kategoriya nomini kiriting:")
        await callback.answer(); return
    await state.update_data(category=cat)
    await state.set_state(AdminSt.q_expl)
    await callback.message.edit_text("💡 Tavsif yoki '-':")
    await callback.answer()

@dp.message(AdminSt.q_cat)
async def aq_new_cat(message: types.Message, state: FSMContext):
    db.add_category(message.text.strip())
    await state.update_data(category=message.text.strip())
    await state.set_state(AdminSt.q_expl)
    await message.answer("💡 Tavsif yoki '-':")

@dp.message(AdminSt.q_expl)
async def aq_expl(message: types.Message, state: FSMContext):
    expl = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(explanation=expl)
    await state.set_state(AdminSt.q_img)
    await message.answer("🖼 Rasm/audio yoki '-':")

@dp.message(AdminSt.q_img)
async def aq_img(message: types.Message, state: FSMContext):
    img = ""
    if message.text and message.text.strip() == "-": img = ""
    elif message.photo: img = message.photo[-1].file_id
    elif message.audio: img = message.audio.file_id
    elif message.voice: img = message.voice.file_id
    elif message.document: img = message.document.file_id
    elif message.text and message.text.startswith("http"): img = message.text.strip()
    await state.update_data(image_id=img)
    data = await state.get_data()
    qt = data.get("q_type","test")
    q_text = data.get("q_text", data.get("accumulated",""))
    short = q_text[:100] + "..." if len(q_text) > 100 else q_text
    opts_d = ""
    if qt == "test":
        opts = data.get("options","").split("|")
        opts_d = "\n" + "\n".join([f"  {chr(65+i)}. {o}" for i,o in enumerate(opts)])
        opts_d += f"\n✅ {data.get('correct','').upper()}"
    elif qt not in IELTS_TYPES:
        opts_d = f"\n✅ {data.get('correct','')}"
    confirm = (f"📋 <b>Tekshiring:</b>\n\nTur: {qt.upper()}\n❓ {short}{opts_d}\n"
               f"💰 {data.get('coins',5)} coin  {DIFF_ICONS.get(data.get('difficulty','orta'),'🟡')}\n"
               f"📂 {data.get('category','')}\n🖼 {'Ha' if img else 'Yoq'}\n\nSaqlash?")
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Saqlash", callback_data="aq_save"),
        InlineKeyboardButton(text="❌ Bekor", callback_data="aq_cancel")]])
    await message.answer(confirm, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "aq_save")
async def aq_save(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    q_text = data.get("q_text", data.get("accumulated",""))
    db.add_question(
        text=q_text, q_type=data["q_type"],
        options=data.get("options",""), correct=data.get("correct",""),
        coins=data["coins"], category=data.get("category","Umumiy"),
        difficulty=data.get("difficulty","orta"), explanation=data.get("explanation",""),
        image_id=data.get("image_id",""), time_limit=data.get("time_limit",""))
    await state.clear()
    await callback.message.edit_text("✅ <b>Savol saqlandi!</b>", parse_mode="HTML")
    await callback.message.answer("⚙️", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query(F.data == "aq_cancel")
async def aq_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor.")
    await callback.message.answer("⚙️", reply_markup=admin_menu())
    await callback.answer()

# ── SAVOLLAR RO'YXATI ─────────────────────────────────────────────────────────
@dp.message(F.text == "📋 Savollar ro'yxati")
async def list_questions(message: types.Message):
    if not is_admin(message.from_user.id): return
    qs = db.get_all_questions()
    if not qs: await message.answer("😔 Savollar yo'q."); return
    text = f"📋 <b>Jami: {len(qs)} ta</b>\n\n"
    for q in qs[:20]:
        q_id, q_text, qt, *_ = q
        short = q_text[:35] + "..." if len(q_text) > 35 else q_text
        text += f"#{q_id} [{qt}] {short}\n"
    if len(qs) > 20: text += f"\n...va yana {len(qs)-20} ta"
    await message.answer(text, parse_mode="HTML")

# ── SAVOL TAHRIRLASH / O'CHIRISH ──────────────────────────────────────────────
@dp.message(F.text == "✏️ Savol tahrirlash")
async def edit_q_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdminSt.edit_id)
    await state.update_data(edit_action="edit")
    await message.answer("✏️ Savol ID sini yuboring:\n<i>/cancel — bekor</i>", parse_mode="HTML")

@dp.message(F.text == "🗑 Savol o'chirish")
async def del_q_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdminSt.edit_id)
    await state.update_data(edit_action="delete")
    await message.answer("🗑 O'chiriladigan savol ID:\n<i>/cancel — bekor</i>", parse_mode="HTML")

@dp.message(AdminSt.edit_id)
async def handle_edit_id(message: types.Message, state: FSMContext):
    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ Faqat raqam!"); return
    q_id = int(message.text.strip())
    q = db.get_question_by_id(q_id)
    data = await state.get_data()
    action = data.get("edit_action","edit")
    await state.clear()
    if not q: await message.answer(f"❌ #{q_id} topilmadi."); return
    _, q_text, qt, options, correct, coins, cat, diff, expl, img, tl = q
    short = q_text[:60] + "..." if len(q_text) > 60 else q_text
    if action == "delete":
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🗑 Ha, o'chirish", callback_data=f"del_{q_id}"),
            InlineKeyboardButton(text="❌ Bekor", callback_data="del_cancel")]])
        await message.answer(f"#{q_id} [{cat}]\n❓ {short}\n\nO'chirilsinmi?", reply_markup=kb)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Matn", callback_data=f"edf_{q_id}_text"),
             InlineKeyboardButton(text="📋 Variantlar", callback_data=f"edf_{q_id}_options")],
            [InlineKeyboardButton(text="✅ Javob", callback_data=f"edf_{q_id}_correct"),
             InlineKeyboardButton(text="💰 Coin", callback_data=f"edf_{q_id}_coins")],
            [InlineKeyboardButton(text="📂 Kategoriya", callback_data=f"edf_{q_id}_category"),
             InlineKeyboardButton(text="💡 Tavsif", callback_data=f"edf_{q_id}_explanation")],
            [InlineKeyboardButton(text="❌ Bekor", callback_data="del_cancel")]])
        await message.answer(f"#{q_id} {DIFF_ICONS.get(diff,'🟡')} [{cat}]\n❓ {short}\n💰 {coins} — {qt}", reply_markup=kb)

@dp.callback_query(F.data.startswith("edf_"))
async def edit_field_cb(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    q_id, field = int(parts[1]), parts[2]
    await state.update_data(edit_q_id=q_id, edit_field=field)
    await state.set_state(AdminSt.edit_val)
    labels = {"text":"Yangi matn:","options":"Yangi variantlar (har biri yangi qatorda):","correct":"Yangi to'g'ri javob:","coins":"Yangi coin miqdori:","category":"Yangi kategoriya:","explanation":"Yangi tavsif ('-' = o'chirish):"}
    await callback.message.answer(labels.get(field, "Yangi qiymat:"))
    await callback.answer()

@dp.message(AdminSt.edit_val)
async def save_edit_val(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_id, field = data["edit_q_id"], data["edit_field"]
    if field == "coins":
        if not message.text.replace(".", "").isdigit():
            await message.answer("⚠️ Faqat raqam!"); return
        value = float(message.text)
    elif field == "options":
        value = "|".join([o.strip() for o in message.text.split("\n") if o.strip()])
    elif field == "explanation":
        value = "" if message.text.strip() == "-" else message.text.strip()
    else:
        value = message.text.strip()
    db.update_question_field(q_id, field, value)
    await state.clear()
    await message.answer(f"✅ #{q_id} yangilandi!", reply_markup=admin_menu())

@dp.callback_query(F.data.startswith("del_"))
async def confirm_del(callback: types.CallbackQuery):
    if callback.data == "del_cancel":
        await callback.message.edit_text("❌ Bekor."); await callback.answer(); return
    q_id = int(callback.data[4:])
    db.delete_question(q_id)
    await callback.message.edit_text(f"✅ #{q_id} o'chirildi!")
    await callback.answer()

# ── KATEGORIYALAR ─────────────────────────────────────────────────────────────
@dp.message(F.text == "📂 Kategoriyalar")
async def manage_cats(message: types.Message):
    if not is_admin(message.from_user.id): return
    cats = db.get_categories_with_count()
    text = "📂 <b>Kategoriyalar</b>\n\n"
    for cat, count in cats: text += f"• <b>{cat}</b> — {count} ta\n"
    if not cats: text += "Hali yo'q"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi", callback_data="cat_new")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data="cat_del_list")]])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "cat_new")
async def cat_new_cb(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminSt.new_cat)
    await callback.message.answer("📂 Yangi kategoriya nomini kiriting:")
    await callback.answer()

@dp.message(AdminSt.new_cat)
async def save_new_cat(message: types.Message, state: FSMContext):
    db.add_category(message.text.strip()); await state.clear()
    await message.answer(f"✅ <b>{message.text.strip()}</b> qo'shildi!", parse_mode="HTML", reply_markup=admin_menu())

@dp.callback_query(F.data == "cat_del_list")
async def cat_del_list(callback: types.CallbackQuery):
    cats = db.get_categories()
    if not cats: await callback.answer("Yo'q!", show_alert=True); return
    buttons = [[InlineKeyboardButton(text=f"🗑 {c}", callback_data=f"delcat_{c}")] for c in cats]
    await callback.message.answer("Qaysi kategoriyani o'chirish?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("delcat_"))
async def del_cat_cb(callback: types.CallbackQuery):
    cat = callback.data[7:]
    db.delete_category(cat)
    await callback.message.edit_text(f"✅ <b>{cat}</b> o'chirildi!", parse_mode="HTML")
    await callback.answer()

# ── TAKLIFLAR ─────────────────────────────────────────────────────────────────
@dp.message(F.text == "💬 Takliflar")
async def show_feedbacks(message: types.Message):
    if not is_admin(message.from_user.id): return
    fbs = db.get_feedbacks(20)
    if not fbs: await message.answer("💬 Hali taklif yo'q."); return
    for fb in fbs[:10]:
        fb_id, user_id, fname, uname, fb_text, created, is_read = fb
        icon = "🆕" if not is_read else "✅"
        u_str = f"@{uname}" if uname else f"ID:{user_id}"
        await message.answer(
            f"{icon} <b>#{fb_id}</b> — {fname} ({u_str})\n📅 {created[:10]}\n\n{fb_text}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💬 Javob", callback_data=f"fb_reply_{fb_id}"),
                InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"fb_del_{fb_id}")]]))
    await message.answer(f"Jami: {len(fbs)} ta",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Barchasini tozalash", callback_data="fb_clear")]]))

@dp.callback_query(F.data.startswith("fb_reply_"))
async def fb_reply_cb(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id) and not is_sub_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!"); return
    fb_id = int(callback.data[9:])
    await state.update_data(reply_fb_id=fb_id)
    await state.set_state(AdminSt.fb_reply)
    await callback.message.answer(f"💬 #{fb_id} ga javob yozing:")
    await callback.answer()

@dp.message(AdminSt.fb_reply)
async def save_fb_reply(message: types.Message, state: FSMContext):
    data = await state.get_data()
    fb_id = data["reply_fb_id"]
    fb = db.get_feedback_by_id(fb_id)
    if fb:
        db.save_feedback_reply(fb_id, message.text)
        try: await bot.send_message(fb[1], f"📩 <b>Taklifingizga javob:</b>\n\n{message.text}", parse_mode="HTML")
        except: pass
    await state.clear()
    await message.answer("✅ Javob yuborildi!", reply_markup=admin_menu())

@dp.callback_query(F.data.startswith("fb_del_"))
async def fb_del_cb(callback: types.CallbackQuery):
    db.delete_feedback(int(callback.data[7:]))
    await callback.message.edit_text("🗑 O'chirildi.")
    await callback.answer()

@dp.callback_query(F.data == "fb_clear")
async def fb_clear(callback: types.CallbackQuery):
    db.mark_feedbacks_read()
    await callback.message.edit_text("✅ Tozalandi!")
    await callback.answer()

# ── XABAR YUBORISH ────────────────────────────────────────────────────────────
@dp.message(F.text == "📢 Xabar yuborish")
async def bc_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdminSt.bc_text)
    await message.answer("📢 Xabar matnini kiriting:\n<i>/cancel — bekor</i>", parse_mode="HTML")

@dp.message(AdminSt.bc_text)
async def bc_text(message: types.Message, state: FSMContext):
    await state.update_data(bc_text=message.text)
    await state.set_state(AdminSt.bc_img)
    await message.answer("🖼 Rasm (ixtiyoriy) yoki '-':")

@dp.message(AdminSt.bc_img)
async def bc_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data["bc_text"]
    img = message.photo[-1].file_id if message.photo else ""
    await state.update_data(bc_img=img)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📢 Yuborish", callback_data="bc_confirm"),
        InlineKeyboardButton(text="❌ Bekor", callback_data="bc_cancel")]])
    await message.answer(f"📢 Xabar:\n{text}\n🖼 {'Ha' if img else 'Yoq'}\n\nYuborilsinmi?", reply_markup=kb)

@dp.callback_query(F.data == "bc_confirm")
async def bc_confirm(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text, img = data["bc_text"], data.get("bc_img","")
    users = db.get_all_user_ids()
    await callback.message.edit_text(f"📢 Yuborilmoqda... ({len(users)} ta)")
    ok = fail = 0
    for uid in users:
        try:
            if img: await bot.send_photo(uid, photo=img, caption=text, parse_mode="HTML")
            else: await bot.send_message(uid, text, parse_mode="HTML")
            ok += 1
        except: fail += 1
        await asyncio.sleep(0.03)
    await state.clear()
    await callback.message.answer(f"✅ {ok} ta yuborildi  ❌ {fail} ta xato", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query(F.data == "bc_cancel")
async def bc_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor.")
    await callback.message.answer("⚙️", reply_markup=admin_menu())
    await callback.answer()

# ── KUTAYOTGAN SAVOLLAR ───────────────────────────────────────────────────────
@dp.message(F.text == "⏳ Kutayotgan savollar")
async def pending_qs(message: types.Message):
    if not is_admin(message.from_user.id): return
    pqs = db.get_pending_questions()
    if not pqs:
        await message.answer("✅ Kutayotgan savollar yo'q."); return
    await message.answer(f"⏳ <b>Kutayotgan: {len(pqs)} ta</b>", parse_mode="HTML")
    for pq in pqs[:10]:
        pq_id, sub_id, text, qt, opts, correct, coins, cat, diff, expl, img, tl, created, status = pq
        short = text[:80] + "..." if len(text) > 80 else text
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pq_ok_{pq_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pq_no_{pq_id}")]])
        await message.answer(
            f"🆔 #{pq_id} | {qt.upper()} | 📂 {cat} | 💰 {coins}\n❓ {short}",
            parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("pq_ok_"))
async def pq_approve(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    pq_id = int(callback.data[6:])
    pq = db.get_pending_question_by_id(pq_id)
    if pq:
        db.approve_pending_question(pq_id)
        sub_id = pq[1]
        if sub_id and sub_id != 0:
            try: await bot.send_message(sub_id, "✅ <b>Savolingiz tasdiqlandi!</b>", parse_mode="HTML")
            except: pass
    await callback.message.edit_text("✅ Tasdiqlandi va qo'shildi!")
    await callback.answer()

@dp.callback_query(F.data.startswith("pq_no_"))
async def pq_reject(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    pq_id = int(callback.data[6:])
    pq = db.get_pending_question_by_id(pq_id)
    if pq:
        db.reject_pending_question(pq_id)
        sub_id = pq[1]
        if sub_id and sub_id != 0:
            try: await bot.send_message(sub_id, "❌ <b>Savolingiz rad etildi.</b>", parse_mode="HTML")
            except: pass
    await callback.message.edit_text("❌ Rad etildi.")
    await callback.answer()

# ── SAVOLLARNI IMPORT QILISH ──────────────────────────────────────────────────
@dp.message(F.text == "📥 Savollarni import qilish")
async def import_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdminSt.bulk_text)
    await message.answer(
        "📥 <b>Savollarni import qilish</b>\n\n"
        "Savollarni quyidagi formatda yozing:\n\n"
        "<code>1-savol (Ochiq): Savol matni?\n"
        "To'g'ri javob: Javob\n"
        "Tavsif: Tushuntirish\n\n"
        "2-savol (4 talik variant): Savol matni?\n"
        "A) Variant1 B) Variant2 C) Variant3 D) Variant4\n"
        "To'g'ri javob: B\n"
        "Tavsif: Tushuntirish</code>\n\n"
        "Matnni yuboring:",
        parse_mode="HTML")

@dp.message(AdminSt.bulk_text)
async def import_get_text(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("⚠️ Matn yuboring!"); return
    await state.update_data(bulk_text=message.text)
    await state.set_state(AdminSt.bulk_cat)
    cats = db.get_categories()
    buttons = []
    row = []
    for cat in cats:
        row.append(InlineKeyboardButton(text=cat, callback_data=f"bcat_{cat}"))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="📂 Yangi kategoriya", callback_data="bcat_NEW")])
    await message.answer("📂 Bu savollar qaysi kategoriyaga?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("bcat_"))
async def import_cat_chosen(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    cat = callback.data[5:]
    if cat == "NEW":
        await callback.message.answer("📂 Yangi kategoriya nomini kiriting:")
        await callback.answer(); return
    data = await state.get_data()
    bulk_text = data.get("bulk_text","")
    await state.clear()
    await do_import(callback.message, bulk_text, cat, callback.from_user.id)
    await callback.answer()

@dp.message(AdminSt.bulk_cat)
async def import_new_cat(message: types.Message, state: FSMContext):
    data = await state.get_data()
    bulk_text = data.get("bulk_text","")
    cat = message.text.strip()
    db.add_category(cat)
    await state.clear()
    await do_import(message, bulk_text, cat, message.from_user.id)

async def do_import(message_obj, text, category, admin_id):
    questions = parse_questions(text)
    if not questions:
        await message_obj.answer("❌ Hech qanday savol aniqlanmadi. Formatni tekshiring!")
        return
    added = 0
    for q in questions:
        try:
            db.add_pending_question(
                sub_admin_id=admin_id, text=q["text"], q_type=q["type"],
                options=q["options"], correct=q["correct"],
                coins=q["coins"], category=category,
                difficulty="orta", explanation=q["explanation"])
            added += 1
        except Exception as e:
            logging.error(f"import err: {e}")
    preview = f"✅ <b>{added} ta savol import qilindi!</b>\n\n📋 <b>Misollar:</b>\n\n"
    for i, q in enumerate(questions[:3]):
        icon = "📝" if q["type"] == "test" else "✍️"
        short = q["text"][:60] + "..." if len(q["text"]) > 60 else q["text"]
        preview += f"{icon} {i+1}. {short}\n✅ {q['correct']}\n\n"
    if len(questions) > 3:
        preview += f"...va yana {len(questions)-3} ta\n\n"
    preview += "⏳ <b>Kutayotgan savollar</b> dan tasdiqlang!"
    await send_long(message_obj.chat.id, preview, parse_mode="HTML")
    await message_obj.answer("⚙️", reply_markup=admin_menu())

# ── YORDAMCHI ADMINLAR ────────────────────────────────────────────────────────
@dp.message(F.text == "🛡 Yordamchi Adminlar")
async def sub_admins_list(message: types.Message):
    if not is_admin(message.from_user.id): return
    subs = db.get_all_sub_admins()
    text = "🛡 <b>Yordamchi Adminlar</b>\n\n"
    if not subs: text += "Hali yo'q"
    else:
        for s in subs:
            uid, uname, fname, elected, term_end, salary, last_report, rep_count, warnings, is_active = s
            text += (f"👤 {fname} (@{uname or uid})\n"
                     f"   💰 {salary} coin/oy  📝 {rep_count}  ⚠️ {warnings}\n"
                     f"   ⏳ {term_end[:10] if term_end else '?'}\n\n")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Qo'shish", callback_data="sub_add")],
        [InlineKeyboardButton(text="❌ O'chirish", callback_data="sub_remove")],
        [InlineKeyboardButton(text="💰 Moash belgilash", callback_data="sub_salary")]])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("sub_add"))
async def sub_add_cb(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    top = db.get_leaderboard(20)
    subs = db.get_all_sub_admins()
    sub_ids = [s[0] for s in subs]
    buttons = []
    for uid, fname, uname, coins in top:
        if uid in sub_ids or is_admin(uid): continue
        name = fname or uname or str(uid)
        buttons.append([InlineKeyboardButton(text=f"👤 {name} ({round(coins,1)})", callback_data=f"do_sub_add_{uid}")])
    if not buttons:
        await callback.answer("Tayinlash uchun foydalanuvchi yo'q!", show_alert=True); return
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="sub_cancel")])
    await callback.message.answer("👤 Kim yordamchi admin bo'lsin?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("do_sub_add_"))
async def do_sub_add(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data[11:])
    user = db.get_user(uid)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True); return
    db.add_sub_admin(uid, user[1], user[2])
    try:
        await bot.send_message(uid,
            "🎉 <b>Tabriklaymiz! Siz Yordamchi Admin etib tayinlandingiz!</b>\n\n"
            f"⏳ Lavozim muddati: {SUB_ADMIN_TERM} kun\n"
            "📋 Vazifalar: savol tuzish, hisobot (3 kunda bir), takliflarga javob",
            parse_mode="HTML")
    except: pass
    await callback.message.edit_text(f"✅ <b>{user[2]}</b> tayinlandi!", parse_mode="HTML")
    await callback.message.answer("⚙️", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query(F.data == "sub_remove")
async def sub_remove_cb(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    subs = db.get_all_sub_admins()
    if not subs:
        await callback.answer("Yo'q!", show_alert=True); return
    buttons = [[InlineKeyboardButton(text=f"❌ {s[2]}", callback_data=f"do_sub_rm_{s[0]}")] for s in subs]
    buttons.append([InlineKeyboardButton(text="🔙 Bekor", callback_data="sub_cancel")])
    await callback.message.answer("Kim lavozimdan olinsin?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("do_sub_rm_"))
async def do_sub_rm(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data[10:])
    sa = db.get_sub_admin(uid)
    fname = sa[2] if sa else str(uid)
    db.remove_sub_admin(uid)
    try: await bot.send_message(uid, "❌ <b>Siz yordamchi admin lavozimidan olindingiz.</b>", parse_mode="HTML")
    except: pass
    await callback.message.edit_text(f"✅ <b>{fname}</b> lavozimdan olindi.", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "sub_salary")
async def sub_salary_cb(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    subs = db.get_all_sub_admins()
    if not subs:
        await callback.answer("Yo'q!", show_alert=True); return
    buttons = [[InlineKeyboardButton(text=f"💰 {s[2]} (hozir: {s[5]})", callback_data=f"do_salary_{s[0]}")] for s in subs]
    buttons.append([InlineKeyboardButton(text="🔙 Bekor", callback_data="sub_cancel")])
    await callback.message.answer("Kimga moash belgilash?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("do_salary_"))
async def do_salary_cb(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data[10:])
    await state.update_data(salary_target=uid)
    await state.set_state(AdminSt.sub_salary)
    sa = db.get_sub_admin(uid)
    fname = sa[2] if sa else str(uid)
    await callback.message.edit_text(f"💰 <b>{fname}</b> uchun oylik moash (coin):", parse_mode="HTML")
    await callback.answer()

@dp.message(AdminSt.sub_salary)
async def save_salary(message: types.Message, state: FSMContext):
    if not message.text.replace(".", "").isdigit():
        await message.answer("⚠️ Faqat raqam!"); return
    data = await state.get_data()
    uid = data["salary_target"]
    salary = float(message.text)
    db.set_sub_admin_salary(uid, salary)
    await state.clear()
    await message.answer(f"✅ Moash {salary} coin etib belgilandi!", reply_markup=admin_menu())

@dp.callback_query(F.data == "sub_cancel")
async def sub_cancel_cb(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Bekor.")
    await callback.answer()

# ── MUKOFOT / JARIMA ─────────────────────────────────────────────────────────
@dp.message(F.text == "💰 Mukofot/Jarima")
async def pay_menu(message: types.Message):
    if not is_admin(message.from_user.id): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Moash to'lash", callback_data="payact_salary")],
        [InlineKeyboardButton(text="🏆 Mukofot berish", callback_data="payact_bonus")],
        [InlineKeyboardButton(text="⚠️ Jarima solish",  callback_data="payact_fine")]])
    await message.answer("💰 <b>Mukofot / Jarima</b>", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("payact_"))
async def payact_cb(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    action = callback.data[7:]
    await state.update_data(pay_action=action)
    if action in ("salary","fine"):
        users_list = db.get_all_sub_admins()
        buttons = [[InlineKeyboardButton(text=f"👤 {s[2]}", callback_data=f"paytgt_{s[0]}")] for s in users_list]
        if not users_list:
            await callback.answer("Yordamchi adminlar yo'q!", show_alert=True); return
    else:
        users_list = db.get_leaderboard(10)
        buttons = [[InlineKeyboardButton(text=f"👤 {fname or uname} ({round(coins,1)})", callback_data=f"paytgt_{uid}")] for uid, fname, uname, coins in users_list]
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="pay_cancel")])
    labels = {"salary":"💰 Moash","bonus":"🏆 Mukofot","fine":"⚠️ Jarima"}
    await callback.message.answer(f"{labels[action]} — <b>Kimga?</b>",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("paytgt_"))
async def pay_target_chosen(callback: types.CallbackQuery, state: FSMContext):
    uid = int(callback.data[7:])
    user = db.get_user(uid)
    fname = user[2] if user else str(uid)
    await state.update_data(pay_target=uid)
    await state.set_state(AdminSt.pay_amount)
    await callback.message.edit_text(f"💰 <b>{fname}</b> ga necha coin?", parse_mode="HTML")
    await callback.answer()

@dp.message(AdminSt.pay_amount)
async def pay_amount(message: types.Message, state: FSMContext):
    if not message.text.replace(".", "").isdigit():
        await message.answer("⚠️ Faqat raqam!"); return
    await state.update_data(pay_amount=float(message.text))
    await state.set_state(AdminSt.pay_note)
    await message.answer("📝 Izoh (yoki '-'):")

@dp.message(AdminSt.pay_note)
async def pay_do(message: types.Message, state: FSMContext):
    note = "" if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    target = data["pay_target"]
    amount = data["pay_amount"]
    action = data["pay_action"]
    db.add_payment(message.from_user.id, target, amount, action, note)
    notif = (f"⚠️ <b>Jarima!</b>\n\n-{amount} coin\nSabab: {note}"
             if action == "fine"
             else f"🎉 <b>{'Moash' if action=='salary' else 'Mukofot'}!</b>\n\n+{amount} coin\n{note}")
    try: await bot.send_message(target, notif, parse_mode="HTML")
    except: pass
    await state.clear()
    act_text = "jarima solindi" if action == "fine" else "to'landi"
    await message.answer(f"✅ {amount} coin {act_text}!", reply_markup=admin_menu())

@dp.callback_query(F.data == "pay_cancel")
async def pay_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor.")
    await callback.answer()

# ── HISOBOTLAR ────────────────────────────────────────────────────────────────
@dp.message(F.text == "📜 Hisobotlar")
async def show_reports(message: types.Message):
    if not is_admin(message.from_user.id): return
    rpts = db.get_reports(10)
    if not rpts:
        await message.answer("📜 Hali hisobot yo'q."); return
    text = "📜 <b>So'nggi hisobotlar</b>\n\n"
    for r in rpts:
        r_id, sub_id, fname, r_text, created = r
        short = r_text[:100] + "..." if len(r_text) > 100 else r_text
        text += f"👤 {fname or sub_id}  📅 {created[:10]}\n{short}\n\n"
    await send_long(message.chat.id, text, parse_mode="HTML")

# ── SAYLOV ────────────────────────────────────────────────────────────────────
@dp.message(F.text == "🗳 Saylov boshqaruvi")
async def election_admin(message: types.Message):
    if not is_admin(message.from_user.id): return
    el = db.get_active_election()
    if el:
        e_id, status, started, ends, winner, created = el
        text = f"🗳 <b>Faol saylov #{e_id}</b>\nHolat: {status}\n{started[:10]} — {ends[:10]}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Ovozni boshlash", callback_data=f"el_vote_{e_id}")],
            [InlineKeyboardButton(text="🏁 Yakunlash", callback_data=f"el_finish_{e_id}")],
            [InlineKeyboardButton(text="📊 Natijalar", callback_data=f"el_res_{e_id}")]])
    else:
        text = "🗳 <b>Faol saylov yo'q</b>"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🗳 Yangi saylov", callback_data="el_new")]])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "el_new")
async def el_new(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    top = db.get_top10_users()
    e_id = db.create_election()
    notified = 0
    for uid, fname, uname, coins in top:
        db.add_candidate(e_id, uid, uname or "", fname or "")
        try:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Ha, nomzod bo'laman", callback_data=f"cand_yes_{e_id}_{uid}"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data=f"cand_no_{e_id}_{uid}")]])
            await bot.send_message(uid,
                f"🏆 <b>Siz Top-10 da ekaniz!</b>\n\nYordamchi Admin sayloviga nomzod bo'lasizmi?",
                parse_mode="HTML", reply_markup=kb)
            notified += 1
        except: pass
    await callback.message.edit_text(f"🗳 Saylov #{e_id} boshlandi!\n{notified} ta xabar yuborildi.")
    await callback.answer()

@dp.callback_query(F.data.startswith("cand_yes_"))
async def cand_yes(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    e_id, uid = int(parts[2]), int(parts[3])
    if callback.from_user.id != uid:
        await callback.answer("Bu sizning havolangiz emas!"); return
    db.confirm_candidate(e_id, uid)
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer("✅ <b>Nomzodligingiz tasdiqlandi!</b>", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("cand_no_"))
async def cand_no(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    e_id, uid = int(parts[2]), int(parts[3])
    if callback.from_user.id != uid:
        await callback.answer(); return
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.message.answer("👍 Keyingi safar!")
    await callback.answer()

@dp.callback_query(F.data.startswith("el_vote_"))
async def el_vote(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    e_id = int(callback.data[8:])
    db.start_voting(e_id)
    cands = db.get_confirmed_candidates(e_id)
    if not cands:
        await callback.message.edit_text("❌ Nomzodlar yo'q!"); return
    buttons = [[InlineKeyboardButton(text=f"👤 {fname or uname}", callback_data=f"vote_{e_id}_{uid}")] for uid, fname, uname in cands]
    users = db.get_all_user_ids()
    ok = 0
    for user_id in users:
        try:
            await bot.send_message(user_id,
                "🗳 <b>SAYLOV BOSHLANDI!</b>\nYordamchi admin uchun ovoz bering:",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
            ok += 1
        except: pass
        await asyncio.sleep(0.03)
    await callback.message.edit_text(f"✅ Saylov boshlandi! {ok} ta xabar yuborildi.")
    await callback.answer()

@dp.callback_query(F.data.startswith("vote_"))
async def cast_vote(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    e_id, cand_id = int(parts[1]), int(parts[2])
    voter = callback.from_user.id
    el = db.get_active_election()
    if not el or el[1] != "active":
        await callback.answer("Saylov faol emas!", show_alert=True); return
    if db.has_voted(e_id, voter):
        await callback.answer("⚠️ Allaqachon ovoz bergansiz!", show_alert=True); return
    db.cast_vote(e_id, voter, cand_id)
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.answer("✅ Ovozingiz qabul qilindi!", show_alert=True)

@dp.callback_query(F.data.startswith("el_finish_"))
async def el_finish(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    e_id = int(callback.data[10:])
    winner_id = db.finish_election(e_id)
    if winner_id:
        winner = db.get_user(winner_id)
        fname = winner[2] if winner else str(winner_id)
        db.add_sub_admin(winner_id, winner[1] if winner else "", fname, SUB_ADMIN_TERM)
        try:
            await bot.send_message(winner_id,
                f"🏆 <b>Tabriklaymiz, {fname}!</b>\nSiz saylovda g'olib chiqdingiz!\nYordamchi Admin panelingizdan foydalaning.",
                parse_mode="HTML")
        except: pass
        users = db.get_all_user_ids()
        for uid in users:
            try:
                await bot.send_message(uid, f"🏆 <b>Saylov yakunlandi!</b>\nYordamchi admin: <b>{fname}</b>", parse_mode="HTML")
                await asyncio.sleep(0.02)
            except: pass
        await callback.message.edit_text(f"✅ G'olib: {fname}")
    else:
        await callback.message.edit_text("❌ Ovozlar bo'lmadi.")
    await callback.answer()

@dp.callback_query(F.data.startswith("el_res_"))
async def el_results(callback: types.CallbackQuery):
    e_id = int(callback.data[7:])
    results = db.get_election_results(e_id)
    text = f"📊 <b>Saylov #{e_id} natijalari</b>\n\n"
    for i, (uid, fname, uname, votes) in enumerate(results):
        text += f"{i+1}. {fname or uname} — <b>{votes}</b> ovoz\n"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

# ── GURUHLAR ──────────────────────────────────────────────────────────────────
@dp.message(F.text == "👥 Guruhlar")
async def admin_groups(message: types.Message):
    if not is_admin(message.from_user.id): return
    groups = db.get_all_groups()
    text = f"👥 <b>Guruhlar ({len(groups)} ta)</b>\n\n"
    for g in groups:
        chat_id, title, is_main, is_active, added_at, category = g
        star = "⭐" if is_main else "•"
        text += f"{star} <b>{title}</b>  📂 {category}\n  🆔 <code>{chat_id}</code>\n\n"
    if not groups: text += "Hali yo'q\nBotni guruhga qo'shing."
    buttons = [[InlineKeyboardButton(text=f"{'⭐' if g[2] else ''}📌 {g[1][:25]}", callback_data=f"grp_{g[0]}")] for g in groups]
    buttons.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data="grp_refresh")])
    await message.answer(text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None)

@dp.callback_query(F.data.startswith("grp_"))
async def grp_manage(callback: types.CallbackQuery):
    if callback.data == "grp_refresh":
        await admin_groups(callback.message)
        await callback.answer(); return
    try: chat_id = int(callback.data[4:])
    except: await callback.answer(); return
    g = db.get_group(chat_id)
    if not g: await callback.answer("Topilmadi!"); return
    _, title, is_main, is_active, added_at, category = g
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Asosiy qilish", callback_data=f"grp_main_{chat_id}")],
        [InlineKeyboardButton(text="📂 Kategoriya", callback_data=f"grp_cat_{chat_id}")],
        [InlineKeyboardButton(text="📢 Savol yuborish", callback_data=f"grp_sendq_{chat_id}")],
        [InlineKeyboardButton(text="❌ Guruhdan chiqish", callback_data=f"grp_leave_{chat_id}")]])
    await callback.message.answer(
        f"📌 <b>{title}</b>\n🆔 <code>{chat_id}</code>\n📂 {category}\n⭐ {'Ha' if is_main else 'Yoq'}",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("grp_main_"))
async def grp_set_main(callback: types.CallbackQuery):
    chat_id = int(callback.data[9:])
    db.set_main_group(chat_id)
    await callback.answer("⭐ Asosiy guruh belgilandi!", show_alert=True)

@dp.callback_query(F.data.startswith("grp_cat_"))
async def grp_set_cat(callback: types.CallbackQuery):
    chat_id = int(callback.data[8:])
    cats = db.get_categories()
    buttons = [[InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"grp_setcat_{chat_id}_{cat}")] for cat in cats]
    buttons.append([InlineKeyboardButton(text="🌐 Barchasi", callback_data=f"grp_setcat_{chat_id}_Barchasi")])
    await callback.message.answer("📂 Kategoriya:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("grp_setcat_"))
async def grp_setcat(callback: types.CallbackQuery):
    parts = callback.data[11:].split("_", 1)
    chat_id, cat = int(parts[0]), parts[1]
    db.set_group_category(chat_id, cat)
    await callback.answer(f"✅ {cat}", show_alert=True)

@dp.callback_query(F.data.startswith("grp_sendq_"))
async def grp_sendq(callback: types.CallbackQuery):
    chat_id = int(callback.data[10:])
    aq = db.get_group_question(chat_id)
    if aq:
        await callback.answer("Aktiv savol bor!", show_alert=True); return
    category = db.get_group_category(chat_id)
    q = db.get_group_random_question(chat_id, category)
    if not q:
        await callback.answer("Savollar tugadi!", show_alert=True); return
    await _send_group_question(chat_id, q)
    await callback.answer("✅ Savol yuborildi!", show_alert=True)

@dp.callback_query(F.data.startswith("grp_leave_"))
async def grp_leave(callback: types.CallbackQuery):
    chat_id = int(callback.data[10:])
    try: await bot.leave_chat(chat_id)
    except: pass
    db.remove_group(chat_id)
    await callback.message.edit_text("✅ Guruhdan chiqildi.")
    await callback.answer()

# ══════════════════════════════════════════════════════════════════════════════
# YORDAMCHI ADMIN PANEL
# ══════════════════════════════════════════════════════════════════════════════
@dp.message(F.text == "🛡 Yordamchi Admin Panel")
async def sub_panel(message: types.Message):
    uid = message.from_user.id
    if not is_sub_admin(uid): return
    sa = db.get_sub_admin(uid)
    days_left = ""
    if sa and sa[4]:
        try:
            te = datetime.strptime(sa[4][:19], "%Y-%m-%d %H:%M:%S")
            days = max(0, (te - datetime.now()).days)
            days_left = f"\n⏳ {days} kun qoldi"
        except: pass
    text = (f"🛡 <b>Yordamchi Admin Panel</b>\n\n"
            f"👤 {sa[2] if sa else uid}\n"
            f"💰 Moash: {sa[5] if sa else 0} coin/oy\n"
            f"📝 Hisobotlar: {sa[7] if sa else 0}\n"
            f"⚠️ Ogohlantirishlar: {sa[8] if sa else 0}{days_left}")
    await message.answer(text, parse_mode="HTML", reply_markup=sub_menu())

@dp.message(F.text == "➕ Savol yuborish")
async def sub_add_q_start(message: types.Message, state: FSMContext):
    if not is_sub_admin(message.from_user.id): return
    await state.clear()
    await state.set_state(SubSt.q_type)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Test", callback_data="saqt_test"),
         InlineKeyboardButton(text="✍️ Ochiq", callback_data="saqt_open")]])
    await message.answer(
        "📌 Savol turi:\n\n"
        "<i>⚠️ Savol bosh adminga yuboriladi, tasdiqdan keyin faollashadi</i>",
        parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("saqt_"))
async def sub_q_type(callback: types.CallbackQuery, state: FSMContext):
    qt = callback.data[5:]
    await state.update_data(q_type=qt)
    await state.set_state(SubSt.q_text)
    await callback.message.edit_text("✏️ Savol matnini kiriting:")
    await callback.answer()

@dp.message(SubSt.q_text)
async def sub_q_text(message: types.Message, state: FSMContext):
    if message.text in MENU_TEXTS: await state.clear(); await route_menu(message, state); return
    data = await state.get_data()
    await state.update_data(q_text=message.text)
    if data["q_type"] == "test":
        await state.set_state(SubSt.q_opts)
        await message.answer("📋 Variantlarni kiriting (har biri yangi qatorda):")
    else:
        await state.set_state(SubSt.q_correct)
        await message.answer("✅ To'g'ri javob:")

@dp.message(SubSt.q_opts)
async def sub_q_opts(message: types.Message, state: FSMContext):
    if message.text in MENU_TEXTS: await state.clear(); await route_menu(message, state); return
    opts = [o.strip() for o in message.text.split("\n") if o.strip()]
    if len(opts) < 2: await message.answer("⚠️ Kamida 2 ta variant!"); return
    await state.update_data(options="|".join(opts))
    await state.set_state(SubSt.q_correct)
    opts_text = "\n".join([f"{chr(65+i)}. {o}" for i, o in enumerate(opts)])
    await message.answer(f"📋 Variantlar:\n{opts_text}\n\n✅ To'g'ri harf (A/B/C/D):")

@dp.message(SubSt.q_correct)
async def sub_q_correct(message: types.Message, state: FSMContext):
    if message.text in MENU_TEXTS: await state.clear(); await route_menu(message, state); return
    await state.update_data(correct=message.text.strip())
    await state.set_state(SubSt.q_coins)
    await message.answer("💰 Necha coin?")

@dp.message(SubSt.q_coins)
async def sub_q_coins(message: types.Message, state: FSMContext):
    if message.text in MENU_TEXTS: await state.clear(); await route_menu(message, state); return
    if not message.text.replace(".", "").isdigit():
        await message.answer("⚠️ Faqat raqam!"); return
    await state.update_data(coins=float(message.text))
    await state.set_state(SubSt.q_diff)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Oson", callback_data="sdiff_oson"),
         InlineKeyboardButton(text="🟡 O'rta", callback_data="sdiff_orta"),
         InlineKeyboardButton(text="🔴 Qiyin", callback_data="sdiff_qiyin")]])
    await message.answer("📊 Qiyinlik:", reply_markup=kb)

@dp.callback_query(F.data.startswith("sdiff_"))
async def sub_q_diff(callback: types.CallbackQuery, state: FSMContext):
    diff = callback.data[6:]
    await state.update_data(difficulty=diff)
    await state.set_state(SubSt.q_cat)
    cats = db.get_categories()
    buttons = []
    row = []
    for cat in cats:
        row.append(InlineKeyboardButton(text=cat, callback_data=f"scat_{cat}"))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    await callback.message.edit_text("📂 Kategoriya:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("scat_"))
async def sub_q_cat(callback: types.CallbackQuery, state: FSMContext):
    cat = callback.data[5:]
    await state.update_data(category=cat)
    await state.set_state(SubSt.q_expl)
    await callback.message.edit_text("💡 Tavsif yoki '-':")
    await callback.answer()

@dp.message(SubSt.q_expl)
async def sub_q_expl(message: types.Message, state: FSMContext):
    if message.text in MENU_TEXTS: await state.clear(); await route_menu(message, state); return
    expl = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(explanation=expl)
    data = await state.get_data()
    qt = data["q_type"]
    q_text = data.get("q_text","")
    short = q_text[:100] + "..." if len(q_text) > 100 else q_text
    opts_d = ""
    if qt == "test":
        opts = data.get("options","").split("|")
        opts_d = "\n" + "\n".join([f"  {chr(65+i)}. {o}" for i,o in enumerate(opts)])
        opts_d += f"\n✅ {data.get('correct','').upper()}"
    else:
        opts_d = f"\n✅ {data.get('correct','')}"
    confirm = (f"📋 <b>Savolingizni tekshiring:</b>\n\n"
               f"Tur: {qt.upper()}\n❓ {short}{opts_d}\n"
               f"💰 {data.get('coins',5)} coin  {DIFF_ICONS.get(data.get('difficulty','orta'),'🟡')}\n"
               f"📂 {data.get('category','')}\n\n"
               f"⚠️ <i>Savol bosh adminga yuboriladi va tasdiqdan keyin faollashadi.</i>")
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📤 Yuborish", callback_data="sub_send_q"),
        InlineKeyboardButton(text="❌ Bekor", callback_data="sub_cancel_q")]])
    await message.answer(confirm, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "sub_send_q")
async def sub_send_q(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    uid = callback.from_user.id
    pq_id = db.add_pending_question(
        sub_admin_id=uid, text=data["q_text"], q_type=data["q_type"],
        options=data.get("options",""), correct=data.get("correct",""),
        coins=data["coins"], category=data.get("category","Umumiy"),
        difficulty=data.get("difficulty","orta"), explanation=data.get("explanation",""))
    for admin_id in ADMIN_IDS:
        try:
            sa = db.get_sub_admin(uid)
            fname = sa[2] if sa else str(uid)
            await bot.send_message(admin_id,
                f"📬 <b>Yangi savol kutmoqda!</b>\n\nYordamchi admin: {fname}\n"
                f"Savol #{pq_id}: {data['q_text'][:80]}\n\n"
                f"'⏳ Kutayotgan savollar' dan tasdiqlang.",
                parse_mode="HTML")
        except: pass
    await state.clear()
    await callback.message.edit_text("✅ <b>Savol adminga yuborildi!</b>", parse_mode="HTML")
    await callback.message.answer("🛡 Panel", reply_markup=sub_menu())
    await callback.answer()

@dp.callback_query(F.data == "sub_cancel_q")
async def sub_cancel_q(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor.")
    await callback.message.answer("🛡 Panel", reply_markup=sub_menu())
    await callback.answer()

@dp.message(F.text == "📝 Hisobot yozish")
async def sub_report_start(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    if not is_sub_admin(uid): return
    sa = db.get_sub_admin(uid)
    if sa and sa[6]:
        try:
            lr = datetime.strptime(sa[6][:19], "%Y-%m-%d %H:%M:%S")
            diff = (datetime.now() - lr).days
            if diff < REPORT_DAYS:
                await message.answer(f"⏳ Keyingi hisobot {REPORT_DAYS-diff} kundan keyin."); return
        except: pass
    await state.set_state(SubSt.report)
    await message.answer("📝 Hisobotingizni yozing:\n<i>/cancel — bekor</i>", parse_mode="HTML")

@dp.message(SubSt.report)
async def sub_save_report(message: types.Message, state: FSMContext):
    if message.text in MENU_TEXTS: await state.clear(); await route_menu(message, state); return
    uid = message.from_user.id
    db.save_report(uid, message.text)
    for admin_id in ADMIN_IDS:
        try:
            sa = db.get_sub_admin(uid)
            fname = sa[2] if sa else str(uid)
            await bot.send_message(admin_id,
                f"📜 <b>Yangi hisobot!</b>\n👤 {fname}\n📅 {datetime.now().strftime('%Y-%m-%d')}\n\n{message.text[:500]}",
                parse_mode="HTML")
        except: pass
    await state.clear()
    await message.answer("✅ Hisobot yuborildi!", reply_markup=sub_menu())

@dp.message(F.text == "💬 Takliflar o'qish")
async def sub_read_fbs(message: types.Message):
    if not is_sub_admin(message.from_user.id): return
    fbs = db.get_feedbacks(10)
    if not fbs: await message.answer("💬 Hali taklif yo'q."); return
    for fb in fbs[:5]:
        fb_id, user_id, fname, uname, fb_text, created, is_read = fb
        icon = "🆕" if not is_read else "✅"
        u_str = f"@{uname}" if uname else f"ID:{user_id}"
        await message.answer(
            f"{icon} <b>#{fb_id}</b> — {fname} ({u_str})\n{created[:10]}\n\n{fb_text}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💬 Javob", callback_data=f"subfb_{fb_id}")]]))

@dp.message(F.text == "💬 Javob yozish")
async def sub_fb_reply_start(message: types.Message, state: FSMContext):
    if not is_sub_admin(message.from_user.id): return
    await message.answer("💬 Javob yozmoqchi bo'lgan taklif <b>#ID</b> sini kiriting:", parse_mode="HTML")

@dp.callback_query(F.data.startswith("subfb_"))
async def sub_fb_reply_cb(callback: types.CallbackQuery, state: FSMContext):
    if not is_sub_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!"); return
    fb_id = int(callback.data[6:])
    await state.update_data(reply_fb_id=fb_id)
    await state.set_state(SubSt.fb_reply)
    await callback.message.answer(f"💬 #{fb_id} ga javob yozing:")
    await callback.answer()

@dp.message(SubSt.fb_reply)
async def sub_save_fb_reply(message: types.Message, state: FSMContext):
    if message.text in MENU_TEXTS: await state.clear(); await route_menu(message, state); return
    data = await state.get_data()
    fb_id = data["reply_fb_id"]
    fb = db.get_feedback_by_id(fb_id)
    if fb:
        db.save_feedback_reply(fb_id, message.text)
        try: await bot.send_message(fb[1], f"📩 <b>Taklifingizga javob:</b>\n\n{message.text}", parse_mode="HTML")
        except: pass
    await state.clear()
    await message.answer("✅ Javob yuborildi!", reply_markup=sub_menu())

@dp.message(F.text == "📢 Xabar tarqatish")
async def sub_bc_start(message: types.Message, state: FSMContext):
    if not is_sub_admin(message.from_user.id): return
    await state.set_state(SubSt.bc_text)
    await message.answer("📢 Xabar matnini kiriting:\n<i>/cancel — bekor</i>", parse_mode="HTML")

@dp.message(SubSt.bc_text)
async def sub_bc_text(message: types.Message, state: FSMContext):
    if message.text in MENU_TEXTS: await state.clear(); await route_menu(message, state); return
    await state.update_data(bc_text=message.text)
    await state.set_state(SubSt.bc_img)
    await message.answer("🖼 Rasm yoki '-':")

@dp.message(SubSt.bc_img)
async def sub_bc_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data["bc_text"]
    img = message.photo[-1].file_id if message.photo else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📢 Yuborish", callback_data="sub_bc_go"),
        InlineKeyboardButton(text="❌ Bekor", callback_data="sub_bc_no")]])
    await state.update_data(bc_img=img)
    await message.answer(f"📢 Yuborilsinmi?\n{text}", reply_markup=kb)

@dp.callback_query(F.data == "sub_bc_go")
async def sub_bc_go(callback: types.CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    if not is_sub_admin(uid): return
    data = await state.get_data()
    text, img = data["bc_text"], data.get("bc_img","")
    sa = db.get_sub_admin(uid)
    fname = sa[2] if sa else "Yordamchi admin"
    full = f"📢 <b>{fname} dan xabar:</b>\n\n{text}"
    users = db.get_all_user_ids()
    ok = fail = 0
    for user_id in users:
        try:
            if img: await bot.send_photo(user_id, photo=img, caption=full, parse_mode="HTML")
            else: await bot.send_message(user_id, full, parse_mode="HTML")
            ok += 1
        except: fail += 1
        await asyncio.sleep(0.03)
    await state.clear()
    await callback.message.edit_text(f"✅ {ok} ta  ❌ {fail} ta")
    await callback.message.answer("🛡 Panel", reply_markup=sub_menu())
    await callback.answer()

@dp.callback_query(F.data == "sub_bc_no")
async def sub_bc_no(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor.")
    await callback.message.answer("🛡 Panel", reply_markup=sub_menu())
    await callback.answer()

@dp.message(F.text == "💰 Moashim")
async def sub_salary_view(message: types.Message):
    uid = message.from_user.id
    if not is_sub_admin(uid): return
    sa = db.get_sub_admin(uid)
    if not sa: await message.answer("Ma'lumot topilmadi!"); return
    _, uname, fname, elected, term_end, salary, last_report, rep_count, warnings, is_active = sa
    pays = db.get_payments(target_id=uid, limit=5)
    user = db.get_user(uid)
    coins = round(user[3], 1) if user else 0
    text = (f"💰 <b>Moash va To'lovlar</b>\n\n"
            f"💎 Moash: <b>{salary} coin/oy</b>\n"
            f"💰 Hozirgi: <b>{coins}</b>\n"
            f"📝 Hisobotlar: <b>{rep_count}</b>\n"
            f"⚠️ Ogohlantirishlar: <b>{warnings}</b>\n\n"
            f"📋 <b>So'nggi to'lovlar:</b>\n")
    for p in pays:
        p_id, a_id, t_id, amount, ptype, note, created = p
        icon = "🏆" if ptype == "bonus" else ("⚠️" if ptype == "fine" else "💰")
        sign = "-" if ptype == "fine" else "+"
        text += f"{icon} {sign}{amount} | {note or ptype} | {created[:10]}\n"
    await message.answer(text, parse_mode="HTML")

# ══════════════════════════════════════════════════════════════════════════════
# GURUH HANDLERLARI
# ══════════════════════════════════════════════════════════════════════════════
@dp.my_chat_member()
async def on_bot_added(event: types.ChatMemberUpdated):
    if event.chat.type not in ("group","supergroup"): return
    status = event.new_chat_member.status
    if status in ("member","administrator"):
        db.add_group(event.chat.id, event.chat.title or "")
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id,
                    f"✅ Bot guruhga qo'shildi!\n📌 <b>{event.chat.title}</b>\n🆔 <code>{event.chat.id}</code>",
                    parse_mode="HTML")
            except: pass
    elif status in ("left","kicked"):
        db.remove_group(event.chat.id)

async def _send_group_question(chat_id, q):
    q_id, q_text, q_type, options, correct, coins, cat, diff, expl, img = q
    d_icon = DIFF_ICONS.get(diff,"🟡")
    me = await bot.get_me()
    join_link = f"https://t.me/{me.username}?start=ref0"
    if q_type == "test":
        sh_opts, new_cor = shuffle_opts(options, correct)
        db.set_group_question(chat_id, q_id, new_cor, coins)
        opts_list = sh_opts.split("|")
        opts_text = "\n".join([f"{chr(65+i)}. {opt}" for i,opt in enumerate(opts_list)])
        header = (f"🧠 <b>GURUH SAVOLI</b>  {d_icon}  📂 {cat}\n"
                  f"💰 To'g'ri: +{coins} coin\n\n❓ <b>{q_text}</b>\n\n{opts_text}\n\n"
                  f"✍️ <b>A / B / C / D</b> deb yozing!\n"
                  f"👉 Coin olish: <a href='{join_link}'>Botga qo'shiling</a>")
    else:
        db.set_group_question(chat_id, q_id, correct, coins)
        header = (f"🧠 <b>GURUH SAVOLI</b>  {d_icon}  📂 {cat}\n"
                  f"💰 To'g'ri: +{coins} coin\n\n❓ <b>{q_text}</b>\n\n"
                  f"✍️ Javob yozing!\n"
                  f"👉 <a href='{join_link}'>Botga qo'shiling</a>")
    try:
        if img and len(header) <= 1024:
            await bot.send_photo(chat_id, photo=img, caption=header, parse_mode="HTML")
        else:
            if img:
                try: await bot.send_photo(chat_id, photo=img)
                except: pass
            await send_long(chat_id, header, parse_mode="HTML")
    except Exception as e:
        logging.error(f"send_group_q: {e}")

@dp.message(Command("savol"))
async def group_savol(message: types.Message):
    if message.chat.type not in ("group","supergroup"): return
    chat_id = message.chat.id
    uid = message.from_user.id
    try:
        member = await bot.get_chat_member(chat_id, uid)
        if member.status not in ("administrator","creator") and not is_admin(uid):
            await message.reply("❌ Faqat guruh admini savol yuborishi mumkin."); return
    except: pass
    aq = db.get_group_question(chat_id)
    if aq:
        await message.reply("⏳ Aktiv savol bor! /skip — o'tkazish"); return
    category = db.get_group_category(chat_id)
    q = db.get_group_random_question(chat_id, category)
    if not q:
        await message.reply("😔 Bu guruhda barcha savollar tugadi! Admin yangi savollar qo'shing."); return
    await _send_group_question(chat_id, q)

@dp.message(Command("skip"))
async def group_skip(message: types.Message):
    if message.chat.type not in ("group","supergroup"): return
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ("administrator","creator") and not is_admin(message.from_user.id):
            await message.reply("❌ Faqat admin o'tkaza oladi."); return
    except: pass
    aq = db.get_group_question(message.chat.id)
    if not aq:
        await message.reply("Aktiv savol yo'q."); return
    _, q_id, correct, coins, _, _ = aq
    db.close_group_question(message.chat.id)
    await message.reply(f"⏭ O'tkazildi.\n✅ To'g'ri javob: <b>{correct}</b>", parse_mode="HTML")

@dp.message(Command("reyting"))
async def group_reyting(message: types.Message):
    if message.chat.type not in ("group","supergroup"): return
    top = db.get_group_leaderboard(message.chat.id, 10)
    if not top:
        await message.reply("🏆 Hali hech kim javob bermagan!"); return
    medals = ["🥇","🥈","🥉"]
    text = f"🏆 <b>{message.chat.title} — Reyting</b>\n\n"
    for i,(uid,fname,uname,count) in enumerate(top):
        m = medals[i] if i < 3 else f"{i+1}."
        name = fname or uname or str(uid)
        text += f"{m} <b>{name}</b> — {count} ta to'g'ri\n"
    await message.reply(text, parse_mode="HTML")

@dp.message(Command("stat"))
async def group_stat(message: types.Message):
    if message.chat.type not in ("group","supergroup"): return
    s = db.get_group_stats(message.chat.id)
    await message.reply(
        f"📊 <b>{message.chat.title}</b>\n\n"
        f"👥 Ishtirokchilar: <b>{s['players']}</b>\n"
        f"📝 Jami javoblar: <b>{s['total']}</b>\n"
        f"✅ To'g'ri: <b>{s['correct']}</b>",
        parse_mode="HTML")

@dp.message(F.chat.type.in_({"group","supergroup"}))
async def handle_group_msg(message: types.Message):
    if not message.text or message.text.startswith("/"): return
    if message.text in MENU_TEXTS: return
    chat_id = message.chat.id
    uid = message.from_user.id
    fname = message.from_user.first_name or str(uid)
    uname = message.from_user.username or ""

    # ── SO'Z O'YINI TEKSHIRUVI ──
    if chat_id in word_games:
        game = word_games[chat_id]
        if uid != game.get("explainer_id") and game.get("word"):
            word = game["word"]
            if message.text.strip().lower() == word.strip().lower():
                explainer_id = game.get("explainer_id")
                explainer_name = game.get("explainer_name","?")
                game_id = game["game_id"]
                db.add_word_score(game_id, chat_id, uid, fname, uname, guessed=1)
                if explainer_id:
                    exp_user = db.get_user(explainer_id)
                    exp_fname = exp_user[2] if exp_user else explainer_name
                    exp_uname = exp_user[1] if exp_user else ""
                    db.add_word_score(game_id, chat_id, explainer_id, exp_fname, exp_uname, explained=1)
                db.add_coins(uid, 5)
                if explainer_id: db.add_coins(explainer_id, 3)
                if chat_id in word_explainer_tasks:
                    word_explainer_tasks[chat_id].cancel()
                    word_explainer_tasks.pop(chat_id, None)
                if game.get("msg_id"):
                    try: await bot.edit_message_reply_markup(
                        chat_id=chat_id, message_id=game["msg_id"], reply_markup=None)
                    except: pass
                await message.reply(
                    f"\U0001f389 <b>{fname}</b> topdi! So'z: <b>{word}</b>\n\n"
                    f"\u2705 {fname}: +2 ball (+5 coin)\n"
                    f"\U0001f4a1 {explainer_name}: +1 ball (+3 coin)\n\n"
                    f"\u23f3 Keyingi so'z yuklanmoqda...",
                    parse_mode="HTML")
                await asyncio.sleep(2)
                await _next_round(chat_id, game_id)
                return
        return  # So'z o'yinida boshqa xabarlar e'tiborga olinmaydi

    # ── SAVOL-JAVOB TIZIMI ──
    aq = db.get_group_question(chat_id)
    if not aq: return
    _, q_id, correct, coins, asked_at, is_open = aq
    if not is_open: return
    if db.already_answered_group(chat_id, uid, q_id): return
    user = db.get_user(uid)
    me = await bot.get_me()
    join_link = f"https://t.me/{me.username}?start=ref{uid}"
    if not user:
        try:
            await message.reply(
                f"\U0001f44b <b>{fname}</b>, coin olish uchun botga qo'shiling!\n"
                f"\U0001f449 <a href='{join_link}'>Botga o'tish</a>", parse_mode="HTML")
        except: pass
        return
    is_correct = check_ans(message.text, correct)
    if is_correct:
        db.save_group_answer(chat_id, uid, q_id, True)
        ns = db.update_streak(uid, True)
        bonus = streak_bonus(ns)
        earned = round(coins * bonus, 1)
        db.add_coins(uid, earned)
        try: db.save_answer(uid, q_id, True)
        except: pass
        db.close_group_question(chat_id)
        text = (f"\u2705 <b>{fname}</b> to'g'ri topdi!\n"
                f"\U0001f4b0 +{earned} coin" + (f" (\U0001f525x{bonus})" if bonus > 1 else "") +
                "\n\n\u23ed Keyingi savol uchun admin /savol yuboring")
        ud = db.get_user(uid)
        if ud: text += f"\n\U0001f3c6 Reyting: #{db.get_user_rank(uid)}"
        await message.reply(text, parse_mode="HTML")
    else:
        db.save_group_answer(chat_id, uid, q_id, False)
        try: await message.reply("\u274c Noto'g'ri! Boshqalar davom etishi mumkin.")
        except: pass

# ══════════════════════════════════════════════════════════════════════════════
# LIVE SAVOL TIZIMI (faqat admin)
# ══════════════════════════════════════════════════════════════════════════════
@dp.message(F.text == "🟢 Live Savol tashlash")
async def live_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    open_live = db.get_open_live_question()
    if open_live:
        await message.answer(
            "⏳ Hozir aktiv Live savol bor!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🛑 To'xtatish", callback_data=f"live_stop_{open_live[0]}")]]))
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Test savol", callback_data="live_type_test"),
         InlineKeyboardButton(text="✍️ Ochiq savol", callback_data="live_type_open")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="live_cancel")]])
    await message.answer("🟢 <b>Live Savol</b>\nBarcha foydalanuvchilarga bir vaqtda boradi.\nSavol turini tanlang:",
        parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "live_cancel")
async def live_cancel_cb(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor.")
    await callback.answer()

@dp.callback_query(F.data.startswith("live_type_"))
async def live_type_cb(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    qt = callback.data[10:]
    cats = db.get_categories()
    buttons = []
    row = []
    for cat in cats:
        row.append(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"live_cat_{qt}_{cat}"))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🌐 Barchasi", callback_data=f"live_cat_{qt}_Barchasi")])
    await callback.message.edit_text("📂 Kategoriya tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("live_cat_"))
async def live_cat_cb(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    rest = callback.data[9:]
    qt, category = rest.split("_", 1)
    q = db.get_random_question(0, category if category != "Barchasi" else None, q_type=qt)
    if not q:
        await callback.answer("Bu kategoriyada savol yo'q!", show_alert=True); return
    q_id, q_text, q_t, options, correct, coins, cat, diff, expl, img, tl = q
    await state.update_data(live_q_id=q_id, live_q_type=q_t, live_correct=correct, live_coins=coins)
    await state.set_state(AdminSt.live_time)
    short = q_text[:120] + "..." if len(q_text) > 120 else q_text
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏱ 30s", callback_data="live_time_30"),
         InlineKeyboardButton(text="⏱ 60s", callback_data="live_time_60"),
         InlineKeyboardButton(text="⏱ 120s", callback_data="live_time_120")],
        [InlineKeyboardButton(text="✍️ Boshqa vaqt", callback_data="live_time_custom")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="live_cancel")]])
    await callback.message.edit_text(
        f"❓ <b>Savol:</b>\n{short}\n💰 {coins} coin\n\n⏰ Vaqtni tanlang:",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("live_time_"))
async def live_time_cb(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    val = callback.data[10:]
    if val == "custom":
        await callback.message.edit_text("⏰ Vaqtni soniyada kiriting (5-600):")
        await callback.answer(); return
    await _do_live_start(callback.message, state, int(val), callback.from_user.id)
    await callback.answer()

@dp.message(AdminSt.live_time)
async def live_time_msg(message: types.Message, state: FSMContext):
    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ Faqat raqam!"); return
    tl = int(message.text.strip())
    if tl < 5 or tl > 600:
        await message.answer("⚠️ 5 dan 600 soniyagacha!"); return
    await _do_live_start(message, state, tl, message.from_user.id)

async def _do_live_start(msg_obj, state, time_limit, admin_id):
    data = await state.get_data()
    q_id = data.get("live_q_id")
    await state.clear()
    q = db.get_question_by_id(q_id)
    if not q: await msg_obj.answer("❌ Savol topilmadi!"); return
    _, q_text, q_type, options, correct, coins, cat, diff, expl, img, tl = q
    d_icon = DIFF_ICONS.get(diff,"🟡")
    if q_type == "test":
        sh_opts, new_cor = shuffle_opts(options, correct)
        live_id = db.create_live_question(q_id, "test", new_cor, coins, time_limit, admin_id)
        opts_list = sh_opts.split("|")
        opts_text = "\n".join([f"{chr(65+i)}. {opt}" for i,opt in enumerate(opts_list)])
        header = (f"🟢 <b>LIVE SAVOL!</b>  {d_icon}  📂 {cat}\n"
                  f"💰 +{coins} coin  ⏰ {time_limit}s\n\n❓ <b>{q_text}</b>\n\n{opts_text}\n\n"
                  f"✍️ A / B / C / D deb yozing!\n⚠️ Faqat 1 marta javob!")
    else:
        live_id = db.create_live_question(q_id, "open", correct, coins, time_limit, admin_id)
        header = (f"🟢 <b>LIVE SAVOL!</b>  {d_icon}  📂 {cat}\n"
                  f"💰 +{coins} coin  ⏰ {time_limit}s\n\n❓ <b>{q_text}</b>\n\n"
                  f"✍️ Javob yozing — kim birinchi topsa g'olib!\n"
                  f"🎯 1-urinishda topgan 2x coin oladi (Sniper Bonus)!")
    stop_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🛑 To'xtatish (admin)", callback_data=f"live_stop_{live_id}")]])
    all_users = db.get_all_user_ids()
    sent = 0
    for uid in all_users:
        try:
            kb_to_send = stop_kb if is_admin(uid) else None
            await bot.send_message(uid, header, parse_mode="HTML", reply_markup=kb_to_send)
            sent += 1
        except: pass
        await asyncio.sleep(0.03)
    await msg_obj.answer(f"✅ {sent} ta foydalanuvchiga yuborildi!\n⏰ {time_limit}s", reply_markup=admin_menu())
    if live_id in live_timers: live_timers[live_id].cancel()
    live_timers[live_id] = asyncio.create_task(_live_timeout(live_id, time_limit))

async def _live_timeout(live_id, time_limit):
    await asyncio.sleep(time_limit)
    live = db.get_live_question(live_id)
    if live and live[6] == "open":
        await _finish_live(live_id, "timeout")

@dp.callback_query(F.data.startswith("live_stop_"))
async def live_stop_cb(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True); return
    live_id = int(callback.data[10:])
    if live_id in live_timers: live_timers[live_id].cancel()
    await _finish_live(live_id, "stopped")
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except: pass
    await callback.answer("🛑 To'xtatildi!", show_alert=True)

async def _finish_live(live_id, reason):
    live = db.get_live_question(live_id)
    if not live or live[6] != "open": return
    _, q_id, q_type, correct, coins, time_limit, status, winner_id, created_by, created_at, closed_at = live
    q = db.get_question_by_id(q_id)
    diff = q[7] if q else "orta"
    if q_type == "test":
        cur = db.get_conn().cursor()
        cur.execute("SELECT user_id, is_correct FROM live_attempts WHERE live_id=%s", (live_id,))
        rows = cur.fetchall()
        correct_users = [uid for uid, ic in rows if ic]
        wrong_users   = [uid for uid, ic in rows if not ic]
        for uid in correct_users:
            earned = round(coins * {"oson":1.0,"orta":1.2,"qiyin":1.5}.get(diff,1.0), 1)
            db.add_coins(uid, earned)
            db.add_league_points(uid, 3)
        for uid in wrong_users:
            db.add_coins(uid, -round(coins * 0.1, 1))
        db.close_live_question(live_id, winner_id=correct_users[0] if correct_users else None)
        why = "vaqt tugadi" if reason == "timeout" else "admin to'xtatdi"
        result = (f"🏁 <b>LIVE SAVOL YAKUNLANDI!</b> ({why})\n\n"
                  f"✅ To'g'ri: {len(correct_users)} kishi\n"
                  f"❌ Noto'g'ri: {len(wrong_users)} kishi")
        all_users = db.get_all_user_ids()
        for uid in all_users:
            try:
                personal = ""
                if uid in correct_users:
                    earned = round(coins * {"oson":1.0,"orta":1.2,"qiyin":1.5}.get(diff,1.0), 1)
                    personal = f"\n\n🎉 Siz to'g'ri! +{earned} coin"
                elif uid in wrong_users:
                    personal = f"\n\n❌ Siz noto'g'ri. -{round(coins*0.1,1)} coin"
                await bot.send_message(uid, result + personal, parse_mode="HTML")
            except: pass
            await asyncio.sleep(0.02)
    else:
        participants = db.get_live_participants(live_id)
        winner = None
        winner_attempt = None
        for uid, fname, uname, attempts, got_correct, correct_at in participants:
            if got_correct:
                winner = uid
                winner_attempt = correct_at
                break
        if winner:
            mult = 2.0 if winner_attempt == 1 else (1.5 if winner_attempt == 2 else 1.0)
            earned = round(coins * mult, 1)
            db.add_coins(winner, earned)
            db.add_league_points(winner, 5)
            bonus_text = " 🎯 Sniper Bonus!" if winner_attempt == 1 else ""
        for uid, fname, uname, attempts, got_correct, correct_at in participants:
            if uid != winner and attempts > 0:
                penalty = round(coins * min(0.5, 0.1 * attempts), 1)
                db.add_coins(uid, -penalty)
        db.close_live_question(live_id, winner_id=winner)
        stats_lines = []
        for uid, fname, uname, attempts, got_correct, correct_at in participants:
            name = fname or uname or str(uid)
            if uid == winner:
                stats_lines.append(f"🏆 <b>{name}</b> — {correct_at}-urinishda topdi{bonus_text if winner_attempt==1 else ''}")
            else:
                stats_lines.append(f"❌ {name} — {attempts} urinish, topa olmadi")
        why = "vaqt tugadi" if reason == "timeout" else "admin to'xtatdi"
        result = (f"🏁 <b>LIVE SAVOL YAKUNLANDI!</b> ({why})\n\n"
                  f"📊 Statistika:\n" + "\n".join(stats_lines) if stats_lines else "Hech kim qatnashmadi.")
        if winner:
            result += f"\n\n💰 G'olib: +{earned} coin"
        all_users = db.get_all_user_ids()
        for uid in all_users:
            try: await send_long(uid, result, parse_mode="HTML")
            except: pass
            await asyncio.sleep(0.02)
    live_timers.pop(live_id, None)

@dp.message(F.chat.type == "private")
async def handle_live_answer(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None: return
    if not message.text or message.text.startswith("/"): return
    if message.text in MENU_TEXTS: return
    live = db.get_open_live_question()
    if not live: return
    live_id, q_id, q_type, correct, coins, time_limit, status, winner_id, created_by, created_at, closed_at = live
    uid = message.from_user.id
    user = db.get_user(uid)
    if not user: return
    if q_type == "test":
        if db.has_live_attempted(live_id, uid):
            await message.reply("⚠️ Faqat 1 marta javob!"); return
        ans = message.text.strip().upper()
        if ans not in ("A","B","C","D"): return
        is_correct = (ans == correct.upper())
        db.add_live_attempt(live_id, uid, ans, is_correct)
        if is_correct:
            await message.reply("✅ Javobingiz qabul qilindi! Natija elon qilinganda bilosiz.")
        else:
            await message.reply("📝 Javobingiz qabul qilindi.")
    else:
        if db.has_live_correct(live_id, uid):
            await message.reply("✅ Siz allaqachon to'g'ri topgansiz!"); return
        is_correct = check_ans(message.text, correct)
        attempt_num = db.add_live_attempt(live_id, uid, message.text, is_correct)
        if is_correct:
            mult = 2.0 if attempt_num == 1 else (1.5 if attempt_num == 2 else 1.0)
            bonus = " 🎯 Sniper Bonus!" if attempt_num == 1 else ""
            await message.reply(
                f"🎯 <b>TO'G'RI!</b> {attempt_num}-urinishda topdingiz!{bonus}\n"
                f"Natija e'lon qilinganda coin beriladi.",
                parse_mode="HTML")
            if live_id in live_timers: live_timers[live_id].cancel()
            await _finish_live(live_id, "answered")
        else:
            await message.reply(f"❌ Noto'g'ri. Yana urining! (#{attempt_num})")

# ══════════════════════════════════════════════════════════════════════════════
# AVTOMATIK MUDDATNI TEKSHIRISH
# ══════════════════════════════════════════════════════════════════════════════
async def check_sub_terms():
    while True:
        await asyncio.sleep(86400)
        subs = db.get_all_sub_admins()
        for s in subs:
            uid, uname, fname, elected, term_end, salary, last_report, rep_count, warnings, is_active = s
            if not term_end: continue
            try:
                te = datetime.strptime(term_end[:19], "%Y-%m-%d %H:%M:%S")
                if datetime.now() > te:
                    db.remove_sub_admin(uid)
                    try: await bot.send_message(uid, "⏰ <b>Lavozim muddatingiz tugadi.</b>", parse_mode="HTML")
                    except: pass
                    continue
                ref = last_report or elected
                lr = datetime.strptime(ref[:19], "%Y-%m-%d %H:%M:%S")
                days = (datetime.now() - lr).days
                if days >= REPORT_DAYS:
                    w = db.add_sub_admin_warning(uid)
                    try:
                        await bot.send_message(uid,
                            f"⚠️ <b>Ogohlantirish #{w}!</b>\nHisobot yozish muddati o'tdi!\n3 ta = lavozimdan olinish.",
                            parse_mode="HTML")
                    except: pass
                    if w >= 3:
                        db.remove_sub_admin(uid)
                        try: await bot.send_message(uid, "❌ <b>3 ta ogohlantirish — lavozimdan olindingiz!</b>", parse_mode="HTML")
                        except: pass
                        for admin_id in ADMIN_IDS:
                            try: await bot.send_message(admin_id, f"❌ {fname} ({uid}) lavozimdan olindi (3 ogohlantirish).", parse_mode="HTML")
                            except: pass
            except: pass

# ══════════════════════════════════════════════════════════════════════════════
# GROQ AVTOSAVOL
# ══════════════════════════════════════════════════════════════════════════════
async def groq_auto_question():
    CATS = ["Matematika","Tarix","Geografiya","Biologiya","Fizika","Kimyo","Adabiyot","Ingliz tili","Umumiy bilim"]
    while True:
        await asyncio.sleep(3600)
        try:
            cat = random.choice(CATS)
            diff = random.choice(["oson","orta","qiyin"])
            diff_name = {"oson":"oson (boshlang'ich)","orta":"o'rta daraja","qiyin":"qiyin (yuqori)"}[diff]
            prompt = (
                f"Sen o'zbek tilida viktorina savoli yaratuvchisan.\n"
                f"Kategoriya: {cat}\nQiyinlik: {diff_name}\n\n"
                f"FAQAT quyidagi JSON formatda javob ber:\n"
                f'[{{"savol":"savol matni","A":"variant","B":"variant","C":"variant","D":"variant","javob":"A","izoh":"tushuntirish"}}]\n\n'
                f"Qoidalar: savol aniq, bir ma'noli, o'zbek tilida.")
            response = await ai_req(prompt)
            json_m = re.search(r'\[.*?\]', response, re.DOTALL)
            if not json_m: continue
            data = json.loads(json_m.group())
            if not data: continue
            d = data[0]
            q_text = d.get("savol","").strip()
            options = f"{d.get('A','')}|{d.get('B','')}|{d.get('C','')}|{d.get('D','')}".strip("|")
            correct = d.get("javob","A").strip().upper()
            izoh = d.get("izoh","").strip()
            if not q_text or not correct: continue
            coins = {"oson":3,"orta":5,"qiyin":8}[diff]
            pq_id = db.add_pending_question(
                sub_admin_id=0, text=q_text, q_type="test",
                options=options, correct=correct, coins=coins,
                category=cat, difficulty=diff, explanation=izoh)
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id,
                        f"🤖 <b>Groq AI yangi savol!</b>\n\n"
                        f"📂 {cat}  {DIFF_ICONS.get(diff,'🟡')} {diff}\n\n"
                        f"❓ {q_text}\n\n"
                        f"A. {d.get('A','')}  B. {d.get('B','')}\n"
                        f"C. {d.get('C','')}  D. {d.get('D','')}\n\n"
                        f"✅ To'g'ri: <b>{correct}</b>\n💡 {izoh}\n\n"
                        f"'⏳ Kutayotgan savollar' dan tasdiqlang.",
                        parse_mode="HTML")
                except: pass
        except Exception as e:
            logging.error(f"auto_q error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
async def main():
    await bot.set_my_commands([
        types.BotCommand(command="start",      description="🚀 Botni boshlash"),
        types.BotCommand(command="savol",      description="🎯 Guruhda savol (faqat admin)"),
        types.BotCommand(command="reyting",    description="🏆 Guruh reytingi"),
        types.BotCommand(command="stat",       description="📊 Guruh statistikasi"),
        types.BotCommand(command="skip",       description="⏭ Savolni o'tkazish (guruh admin)"),
        types.BotCommand(command="sozboshi",   description="🎮 So'z o'yinini boshlash"),
        types.BotCommand(command="sozstop",    description="🛑 So'z o'yinini to'xtatish"),
        types.BotCommand(command="sozreyting", description="🏅 So'z o'yini reytingi"),
        types.BotCommand(command="sozqosh",    description="📝 So'z qo'shish (admin)"),
        types.BotCommand(command="sozlar",     description="📋 So'zlar ro'yxati (admin)"),
        types.BotCommand(command="cancel",     description="❌ Amalni bekor qilish"),
    ])
    asyncio.create_task(check_sub_terms())
    asyncio.create_task(groq_auto_question())
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())

# ══════════════════════════════════════════════════════════════════════════════
# SO'Z O'YINI (TABOO / KROKO'DIL)
# ══════════════════════════════════════════════════════════════════════════════
import asyncio as _asyncio

# Aktiv o'yinlar: chat_id -> {game_id, word_id, word, explainer_id, msg_id, task, used_word_ids, round}
word_games: dict = {}
# Timeout task: chat_id -> asyncio.Task
word_explainer_tasks: dict = {}

def wg_scores_text(scores):
    if not scores: return "Hali hech kim ball olmadi."
    medals = ["🥇","🥈","🥉"]
    lines = []
    for i,(uid,fname,uname,exp,guess,total) in enumerate(scores):
        m = medals[i] if i < 3 else f"{i+1}."
        name = fname or uname or str(uid)
        lines.append(f"{m} <b>{name}</b> — {total} ball (tushuntirdi:{exp} topdi:{guess})")
    return "\n".join(lines)

# ── ADMIN: SO'Z QO'SHISH ──────────────────────────────────────────────────────
class WordSt(StatesGroup):
    add_words = State()
    bulk_words = State()

@dp.message(Command("sozqosh"))
async def cmd_soz_qosh(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(WordSt.add_words)
    count = db.get_word_count()
    await message.answer(
        f"📝 <b>So'z qo'shish</b>\n\nHozir bazada: <b>{count} ta</b> so'z\n\n"
        "Har qatorda bitta so'z yozing:\n"
        "<code>olma\ndaraxt\nkompyuter</code>\n\n"
        "<i>/cancel — bekor</i>",
        parse_mode="HTML")

@dp.message(WordSt.add_words)
async def add_words_handler(message: types.Message, state: FSMContext):
    if not message.text: return
    if message.text in MENU_TEXTS: await state.clear(); await route_menu(message, state); return
    words = [w.strip() for w in message.text.split("\n") if w.strip()]
    added = 0
    for word in words:
        try:
            db.add_word(word, added_by=message.from_user.id)
            added += 1
        except Exception as e:
            logging.error(f"word add: {e}")
    await state.clear()
    await message.answer(
        f"✅ <b>{added} ta so'z qo'shildi!</b>\nJami bazada: <b>{db.get_word_count()}</b> ta so'z",
        parse_mode="HTML", reply_markup=admin_menu())

@dp.message(Command("sozlar"))
async def cmd_sozlar(message: types.Message):
    if not is_admin(message.from_user.id): return
    words = db.get_all_words(30)
    if not words:
        await message.answer("📝 So'zlar yo'q. /sozqosh bilan qo'shing.")
        return
    text = f"📝 <b>So'zlar ro'yxati ({db.get_word_count()} ta)</b>\n\n"
    for w_id, word, cat, is_active in words:
        icon = "✅" if is_active else "❌"
        text += f"{icon} #{w_id} — <b>{word}</b> [{cat}]\n"
    text += "\n<i>/sozochir [id] — so'zni o'chirish</i>"
    await send_long(message.chat.id, text, parse_mode="HTML")

@dp.message(Command("sozochir"))
async def cmd_soz_ochir(message: types.Message):
    if not is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("❌ Format: /sozochir [id]"); return
    db.delete_word(int(parts[1]))
    await message.answer(f"✅ So'z #{parts[1]} o'chirildi.")

# ── GURUHDA O'YIN BOSHLASH ────────────────────────────────────────────────────
@dp.message(Command("sozboshi"))
async def cmd_soz_boshi(message: types.Message):
    if message.chat.type not in ("group","supergroup"): return
    chat_id = message.chat.id
    uid = message.from_user.id

    if db.get_word_count() < 3:
        await message.reply(
            "❌ So'zlar yetarli emas!\n"
            "Admin /sozqosh buyrug'i bilan so'z qo'shsin.")
        return

    if chat_id in word_games:
        await message.reply("⏳ O'yin allaqachon ketmoqda! /sozstop — to'xtatish")
        return

    game_id = db.create_word_game(chat_id, uid)
    starter_name = message.from_user.first_name or str(uid)

    word_games[chat_id] = {
        "game_id": game_id,
        "word_id": None,
        "word": None,
        "explainer_id": None,
        "explainer_name": None,
        "msg_id": None,
        "used_word_ids": [],
        "round": 0,
    }

    await message.answer(
        f"🎮 <b>SO'Z O'YINI BOSHLANDI!</b>\n\n"
        f"O'yinni boshlagan: <b>{starter_name}</b>\n\n"
        f"Qoidalar:\n"
        f"🎯 Tushuntiruvchi so'zni ko'rib, guruhga tushuntiradi\n"
        f"✅ Kim topsa → +2 ball\n"
        f"💡 Tushuntiruvchi → +1 ball\n\n"
        f"Birinchi so'z yuklanmoqda...",
        parse_mode="HTML")

    await asyncio.sleep(1)
    await _next_round(chat_id, game_id)

async def _next_round(chat_id, game_id):
    """Yangi raund — yangi so'z va tushuntiruvchi tayinlash"""
    if chat_id not in word_games: return
    game = word_games[chat_id]
    used = game["used_word_ids"]

    # Yangi so'z olish
    word_row = db.get_random_word(exclude_ids=used if used else None)
    if not word_row:
        # Barcha so'zlar tugadi — ro'yxatni tozalab qayta boshlash
        game["used_word_ids"] = []
        word_row = db.get_random_word()
    if not word_row:
        await bot.send_message(chat_id, "❌ So'zlar tugadi! Admin yangi so'z qo'shing.")
        return

    w_id, word, cat = word_row
    game["used_word_ids"].append(w_id)
    game["word_id"] = w_id
    game["word"] = word
    game["round"] += 1
    game["explainer_id"] = None
    game["explainer_name"] = None
    game["msg_id"] = None

    db.set_game_word_and_explainer(game_id, w_id, None, None, game["round"])

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="👁 So'zni ko'rish (tushuntiruvchi bo'lish)",
            callback_data=f"wg_see_{chat_id}_{game_id}")]])

    sent = await bot.send_message(
        chat_id,
        f"🎮 <b>Yangi o'yin boshlandi!</b>\n\n"
        f"👤 Tushuntiruvchi: <i>hali tanlanmadi</i>\n\n"
        f"Boshqalar so'zni topishga harakat qilsin! ⏳ 5 daqiqa vaqt bor.\n\n"
        f"👇 Tushuntiruvchi bo'lish uchun tugmani bosing:",
        parse_mode="HTML", reply_markup=kb)

    game["msg_id"] = sent.message_id

    # 2 soniyalik timeout — agar bosilmasa, keyinchi bosgan oladi
    # Bu timeout faqat "birinchi bosish" uchun emas
    # Telegram da "2 soniya" ni quyidagicha amalga oshiramiz:
    # Tugma bosilganda timestamp tekshiramiz
    game["round_started"] = asyncio.get_event_loop().time()

    # 5 daqiqalik raund timeout
    if chat_id in word_explainer_tasks:
        word_explainer_tasks[chat_id].cancel()
    word_explainer_tasks[chat_id] = asyncio.create_task(
        _round_timeout(chat_id, game_id, sent.message_id, 300))

@dp.callback_query(F.data.startswith("wg_see_"))
async def wg_see_word(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    chat_id = int(parts[2])
    game_id = int(parts[3])
    uid = callback.from_user.id
    fname = callback.from_user.first_name or str(uid)

    # Botga obuna tekshirish
    user = db.get_user(uid)
    if not user:
        me = await bot.get_me()
        await callback.answer(
            f"❌ Coin olish uchun avval botga qo'shiling!\nt.me/{me.username}",
            show_alert=True)
        return

    if chat_id not in word_games:
        await callback.answer("O'yin topilmadi!", show_alert=True); return

    game = word_games[chat_id]
    if game["game_id"] != game_id:
        await callback.answer("Eski o'yin!", show_alert=True); return

    # Agar tushuntiruvchi allaqachon bor bo'lsa
    if game["explainer_id"] is not None:
        if game["explainer_id"] == uid:
            # O'zi qayta bosyapti — so'zni ko'rsatish
            word = game["word"]
            await callback.answer(f"🔤 Yashirin so'z: {word}", show_alert=True)
        else:
            await callback.answer("⏳ Tushuntiruvchi allaqachon bor!", show_alert=True)
        return

    # Yangi tushuntiruvchi tayinlash
    game["explainer_id"] = uid
    game["explainer_name"] = fname
    game["last_explainer_time"] = asyncio.get_event_loop().time()

    db.set_game_word_and_explainer(game_id, game["word_id"], uid, fname, game["round"])

    word = game["word"]

    # Guruhga xabar yangilash
    try:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👁 So'zni ko'rish", callback_data=f"wg_see_{chat_id}_{game_id}")],
            [InlineKeyboardButton(text="⏭ Keyingi so'z", callback_data=f"wg_next_{chat_id}_{game_id}"),
             InlineKeyboardButton(text="⏮ Oldingi o'tkazish", callback_data=f"wg_skip_{chat_id}_{game_id}")],
            [InlineKeyboardButton(text="🔤 So'zni ochish (ochish)", callback_data=f"wg_reveal_{chat_id}_{game_id}")]])
        await bot.edit_message_text(
            f"🎮 <b>Yangi o'yin boshlandi!</b>\n\n"
            f"👤 Tushuntiruvchi: <b>{fname}</b>\n\n"
            f"Boshqalar so'zni topishga harakat qilsin! ⏳ 5 daqiqa vaqt bor.",
            chat_id=chat_id, message_id=game["msg_id"],
            parse_mode="HTML", reply_markup=kb)
    except: pass

    # Tushuntiruvchiga so'zni ko'rsatish
    await callback.answer(f"🔤 Yashirin so'z: {word}", show_alert=True)

@dp.callback_query(F.data.startswith("wg_next_"))
async def wg_next_word(callback: types.CallbackQuery):
    """Faqat tushuntiruvchi keyingi so'zga o'tkazadi"""
    parts = callback.data.split("_")
    chat_id = int(parts[2])
    game_id = int(parts[3])
    uid = callback.from_user.id

    if chat_id not in word_games:
        await callback.answer("O'yin topilmadi!"); return
    game = word_games[chat_id]
    if game["explainer_id"] != uid:
        await callback.answer("Siz tushuntiruvchi emassiz!", show_alert=True); return

    await callback.answer("⏭ Keyingi so'z!")
    try: await bot.edit_message_reply_markup(chat_id=chat_id, message_id=game["msg_id"], reply_markup=None)
    except: pass
    await bot.send_message(chat_id, f"⏭ <b>{game['explainer_name']}</b> so'zni o'tkazdi.", parse_mode="HTML")
    await _next_round(chat_id, game_id)

@dp.callback_query(F.data.startswith("wg_skip_"))
async def wg_skip(callback: types.CallbackQuery):
    """Oldingi so'zni o'tkazish (tushuntiruvchi uchun)"""
    await wg_next_word(callback)

@dp.callback_query(F.data.startswith("wg_reveal_"))
async def wg_reveal(callback: types.CallbackQuery):
    """Tushuntiruvchi so'zni ochib, raundni yakunlaydi"""
    parts = callback.data.split("_")
    chat_id = int(parts[2])
    game_id = int(parts[3])
    uid = callback.from_user.id

    if chat_id not in word_games:
        await callback.answer("O'yin topilmadi!"); return
    game = word_games[chat_id]
    if game["explainer_id"] != uid:
        await callback.answer("Siz tushuntiruvchi emassiz!", show_alert=True); return

    word = game["word"]
    await callback.answer(f"So'z: {word}", show_alert=True)

# Guruhda javob tekshirish
@dp.message(F.chat.type.in_({"group","supergroup"}))
async def handle_word_game_guess(message: types.Message):
    """So'z o'yinida javob tekshirish — guruh xabarlar handleri"""
    # Avval oddiy savol tizimini tekshirish (handle_group_msg ham guruhda)
    # Bu handler oxirida joylashgan shuning uchun avvalgi handler ishlaydi
    pass

# ── O'YIN TUGASH / TO'XTATISH ─────────────────────────────────────────────────
@dp.message(Command("sozstop"))
async def cmd_soz_stop(message: types.Message):
    if message.chat.type not in ("group","supergroup"): return
    chat_id = message.chat.id
    uid = message.from_user.id
    try:
        member = await bot.get_chat_member(chat_id, uid)
        if member.status not in ("administrator","creator") and not is_admin(uid):
            await message.reply("❌ Faqat admin to'xtatishi mumkin."); return
    except: pass
    await _end_word_game(chat_id)

@dp.message(Command("sozreyting"))
async def cmd_soz_reyting(message: types.Message):
    if message.chat.type not in ("group","supergroup"): return
    top = db.get_word_game_leaderboard(message.chat.id, 10)
    if not top:
        await message.reply("🏆 Hali hech kim ball olmagan!")
        return
    medals = ["🥇","🥈","🥉"]
    text = f"🏆 <b>{message.chat.title} — So'z O'yini Reytingi</b>\n\n"
    for i,(uid,fname,uname,exp,guess,total) in enumerate(top):
        m = medals[i] if i < 3 else f"{i+1}."
        name = fname or uname or str(uid)
        text += f"{m} <b>{name}</b> — {total} ball (tushuntirdi:{exp} topdi:{guess})\n"
    await message.reply(text, parse_mode="HTML")

async def _round_timeout(chat_id, game_id, msg_id, seconds):
    """5 daqiqa o'tsa raund tugaydi"""
    await asyncio.sleep(seconds)
    if chat_id not in word_games: return
    game = word_games[chat_id]
    if game["game_id"] != game_id: return
    word = game["word"] or "?"
    try:
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=None)
    except: pass
    await bot.send_message(
        chat_id,
        f"⏰ <b>Vaqt tugadi!</b>\n\n"
        f"Yashirin so'z: <b>{word}</b>\n\n"
        f"Keyingi so'z yuklanmoqda...",
        parse_mode="HTML")
    await asyncio.sleep(2)
    await _next_round(chat_id, game_id)

async def _end_word_game(chat_id):
    """O'yinni tugatish"""
    if chat_id not in word_games:
        try: await bot.send_message(chat_id, "❌ Aktiv o'yin yo'q.")
        except: pass
        return
    game = word_games[chat_id]
    game_id = game["game_id"]
    if chat_id in word_explainer_tasks:
        word_explainer_tasks[chat_id].cancel()
        word_explainer_tasks.pop(chat_id, None)
    # Natijalar
    scores = db.get_word_game_scores(game_id)
    db.finish_word_game(chat_id)
    word_games.pop(chat_id, None)
    scores_text = wg_scores_text(scores)
    await bot.send_message(
        chat_id,
        f"🏁 <b>O'YIN TUGADI!</b>\n\n"
        f"🏆 <b>Natijalar:</b>\n{scores_text}\n\n"
        f"Yangi o'yin: /sozboshi",
        parse_mode="HTML")

# ── GURUH XABARLARINI QAYTA ISHLASH (SO'Z O'YINI UCHUN) ──────────────────────
# Eslatma: handle_group_msg allaqachon yuqorida savol javob uchun belgilangan.
# Quyidagi middleware orqali so'z o'yini javobi tekshiriladi.

@dp.message(F.chat.type.in_({"group","supergroup"}) & F.text)
async def handle_word_guess(message: types.Message):
    """So'z o'yini taxmini — faqat so'z o'yini aktiv bo'lsa"""
    chat_id = message.chat.id
    if chat_id not in word_games: return
    if not message.text or message.text.startswith("/"): return
    if message.text in MENU_TEXTS: return

    game = word_games[chat_id]
    uid = message.from_user.id
    fname = message.from_user.first_name or str(uid)
    uname = message.from_user.username or ""

    # Tushuntiruvchi o'zi ayta olmaydi
    if uid == game.get("explainer_id"): return

    word = game.get("word","")
    if not word: return

    # Javob tekshirish (case-insensitive)
    if message.text.strip().lower() == word.strip().lower():
        explainer_id = game.get("explainer_id")
        explainer_name = game.get("explainer_name","?")
        game_id = game["game_id"]

        # Ball berish
        db.add_word_score(game_id, chat_id, uid, fname, uname, guessed=1)
        if explainer_id:
            exp_user = db.get_user(explainer_id)
            exp_fname = exp_user[2] if exp_user else explainer_name
            exp_uname = exp_user[1] if exp_user else ""
            db.add_word_score(game_id, chat_id, explainer_id, exp_fname, exp_uname, explained=1)

        # Coin berish
        db.add_coins(uid, 5)  # topgan
        if explainer_id: db.add_coins(explainer_id, 3)  # tushuntirgan

        # Raundni yakunlash
        if chat_id in word_explainer_tasks:
            word_explainer_tasks[chat_id].cancel()
            word_explainer_tasks.pop(chat_id, None)

        # Tugmani o'chirish
        if game.get("msg_id"):
            try: await bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=game["msg_id"], reply_markup=None)
            except: pass

        await message.reply(
            f"🎉 <b>{fname}</b> topdi! So'z: <b>{word}</b>\n\n"
            f"✅ {fname}: +2 ball (+5 coin)\n"
            f"💡 {explainer_name}: +1 ball (+3 coin)\n\n"
            f"⏳ Keyingi so'z yuklanmoqda...",
            parse_mode="HTML")

        await asyncio.sleep(2)
        await _next_round(chat_id, game_id)

# ── ADMIN: SO'Z O'YINI MENYUSIGA QO'SHISH ────────────────────────────────────
# /start da buyruqlar ro'yxatiga qo'shiladi (main() da)
