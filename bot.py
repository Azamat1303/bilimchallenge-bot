import logging
import asyncio
import random
import re
import aiohttp
from aiogram import Bot, Dispatcher, types,
F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import
MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State,
StatesGroup
from aiogram.types import
InlineKeyboardMarkup, InlineKeyboardButton,
ReplyKeyboardMarkup, KeyboardButton
from database import db
from config import BOT_TOKEN, ADMIN_IDS,
QUESTION_TIME, PENALTY_PERCENT,
TIMEOUT_PENALTY, STREAK_BONUSES,
GROQ_API_KEY, GROQ_MODEL, GEMINI_API_KEY
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
DIFFICULTY_ICONS = {"oson": "🟢", "orta":
"🟡", "qiyin": "🔴"}
DIFFICULTY_NAMES = {"oson": "Oson", "orta":
"O'rta", "qiyin": "Qiyin"}
IELTS_TYPES = ["writing", "essay",
"reading", "speaking", "listening"]
DIFFICULTY_TIME = {"oson": 30, "orta": 60,
"qiyin": 90}
active_timers = {}
ILLEGAL_WORDS = ["bomb", "portlat",
"qotil", "terror", "narkotik", "hack"]
STICKER_QUESTION =
"CAACAgQAAxkBAAFK2GFqGBZkvOQYIqxuYRxOg8yZ_k
GpCQACLhMAAqtUsFGayERH0PRbYTsE"
STICKER_CORRECT_LOW =
"CAACAgIAAxkBAAFK2HxqGBcuYTvi4L__VuLGnOmw_0
h3MQACT6cAAiS3qEprLmY89x6ufjsE"
STICKER_CORRECT_MID =
"CAACAgQAAxkBAAFK2FxqGBZODMIw26R9HpabXj_GXX
HY_QAC9wsAAsVA0FKiYzU0cZkIATsE"
STICKER_CORRECT_HIGH =
"CAACAgIAAxkBAAFK2HFqGBa54WJlIjngkLvRxQyv_i
ejvAACUqEAAs2uqEoU5ts6XT2m-DsE"
STICKERS_CORRECT_RANDOM =
["CAACAgIAAxkBAAFK2BdqGBSDpT9UJGnf8A933Skuj
hR1ugAC7i4AAu2JwEjbRw5y8ATySTsE","CAACAgIAA
xkBAAFK2B1qGBSg7YLcDzG45IMbWD9yLQd2twACxCwA
AmyCwUhW4u2V7FLn2jsE","CAACAgIAAxkBAAFK2Chq
GBT8ht7vPfWPVNZSJ99eSrO4aAACpy4AAlsmwUgiQZe
-63v_8DsE"]
STICKER_WRONG_LOW =
"CAACAgIAAxkBAAFK2I5qGBe3fhF_QafwvVtn9eZZJ2
wyYgACwnEAAj3NaUpk2l3tCbDGJTsE"
STICKER_WRONG_MID =
"CAACAgIAAxkBAAFK2GZqGBaGcsKcNXFNKzEjnwAB_N
6SLx4AAiZjAAIexglIbW6k0yQK8f47BA"
STICKER_WRONG_HIGH =
"CAACAgIAAxkBAAFK2ABqGBdBbZ364p3pJn7rIUWgmY
P_ZwACe5gAArNyiUj8ULr6FLOqsTsE"
STICKERS_WRONG_RANDOM =
["CAACAgIAAxkBAAFK2B9qGBSy53xM_fWFSR3_QB-b-
96PzwACuUIAAkSZyEj30qYDy3h_-
TsE","CAACAgIAAxkBAAFK2CFqGBTQxCg8PTNAy8ELJ
PO1ekiKQAACcSkAAthiwUi7vlkGdgu7SjsE"]
STICKERS_TIMEOUT =
["CAACAgIAAxkBAAFK2CpqGBT9Y8JM8DQ_k5oZ_koPS
4fNlgACWiYAAlDgwEhOxSLS4ALrSDsE","CAACAgIAA
xkBAAFK2CVqGBTpcrLFTrOLIF6ZRjaUHU_NxwACei0A
AhRdCUkIUGBOZbVgrjsE"]
STICKER_LEADERBOARD =
"CAACAgQAAxkBAAFK2F5qGBZib8V7GFYDhDMw8H10Ba
JIfgAChBYAAkfnsFEm5zMVxs4-nDsE"
STICKER_TOP1 =
"CAACAgQAAxkBAAFK2pVqGC8QLY1z08fADOc-
QGogLJWn2AACFxsAAvdb0FEvAAGtAAFifD0MOwQ"
STICKER_TOP2 =
"CAACAgQAAxkBAAFK2E9qGBXpsYQFe_Q2qKm4WQcn5l
ZeRAACGhYAAkQp2VGaVMouneMzrjsE"
STICKER_TOP3 =
"CAACAgQAAxkBAAFK2FJqGBXrg1BmRPSdqE663UwwKV
FsWAACnxQAAk8s6FDKghp6_6nUJDsE"
STICKER_TOP5 =
"CAACAgQAAxkBAAFK2FZqGBX4e7mmRfTgeyt3WLZCD4
xSdQADFwACZFbRUYAvpAABVerDrjsE"
STICKER_TOP10=
"CAACAgQAAxkBAAFK2FhqGBYKX7aALmALEnidgp-
wFO-3nQAC2RYAAj6CKVFONJy-EgNA5TsE"
def get_correct_sticker(c):
if c<=1: return STICKER_CORRECT_LOW
elif c<=5: return
random.choice(STICKERS_CORRECT_RANDOM)
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
class AdminStates(StatesGroup):
waiting_question_type=State();
waiting_question_text=State();
waiting_options=State()
waiting_correct_answer=State();
waiting_coin_reward=State();
waiting_difficulty=State()
waiting_category=State();
waiting_explanation=State();
waiting_image=State()
waiting_time_limit=State();
waiting_new_category=State();
editing_field=State()
editing_value=State();
broadcast_text=State();
broadcast_image=State()
class UserStates(StatesGroup):
answering_open=State();
sending_feedback=State();
answering_premium=State()
answering_ielts=State();
ai_chat=State();
ai_chat_confirm_debt=State()
def is_admin(uid): return uid in ADMIN_IDS
def main_menu(uid):
b=[[KeyboardButton(text="🎯 Savol
olish"),KeyboardButton(text="🏆 Reyting")],
[KeyboardButton(text="👤
Profilim"),KeyboardButton(text="ℹ
Yordam")],
[KeyboardButton(text="📝
Taklif/Shikoyat"),KeyboardButton(text="🎓
IELTS")],
[KeyboardButton(text="🤖 AI Chat")]]
if is_admin(uid):
b.append([KeyboardButton(text="⚙ Admin
Panel")])
return
ReplyKeyboardMarkup(keyboard=b,resize_keybo
ard=True)
def admin_menu():
b=[[KeyboardButton(text="➕ Savol
qo'shish"),KeyboardButton(text="📋 Savollar
ro'yxati")],
[KeyboardButton(text="✏ Savol
tahrirlash"),KeyboardButton(text="🗑 Savol
o'chirish")],
[KeyboardButton(text="📂
Kategoriyalar"),KeyboardButton(text="📊
Statistika")],
[KeyboardButton(text="👥
Foydalanuvchilar"),KeyboardButton(text="💬
Takliflar")],
[KeyboardButton(text="📢 Xabar
yuborish"),KeyboardButton(text="🔙 Asosiy
menyu")]]
return
ReplyKeyboardMarkup(keyboard=b,resize_keybo
ard=True)
def streak_bonus(s):
b=1.0
for t in sorted(STREAK_BONUSES.keys()):
if s>=t: b=STREAK_BONUSES[t]
return b
def streak_msg(s):
if s>=10: return f"🔥🔥🔥 SUPER STREAK
x{s}!"
if s>=5: return f"🔥🔥 STREAK x{s}!"
if s>=3: return f"🔥 STREAK x{s}!"
return ""
def shuffle_options(opts_str,
correct_letter):
opts=opts_str.split("|")
ci=ord(correct_letter.upper())-65
if ci>=len(opts): return
opts_str,correct_letter
ct=opts[ci];
idx=list(range(len(opts)));
random.shuffle(idx)
shuffled=[opts[i] for i in idx];
nci=shuffled.index(ct)
return "|".join(shuffled),chr(65+nci)
def check_answer(user_ans, correct_ans):
uc=user_ans.strip().lower()
return uc in [a.strip().lower() for a
in correct_ans.split("\n") if a.strip()]
async def ai_req(prompt):
try:
url=f"https://generativelanguage.googleapis
.com/v1beta/models/gemini-1.5-
flash:generateContent?key={GEMINI_API_KEY}"
async with aiohttp.ClientSession()
as s:
async with s.post(url,headers=
{"Content-Type":"application/json"},
json={"contents":[{"parts":
[{"text":prompt}]}]},
timeout=aiohttp.ClientTimeout(total=30)) as
r:
d=await r.json()
if "candidates" in d and
d["candidates"]:
return d["candidates"]
[0]["content"]["parts"][0]["text"]
except: pass
try:
async with aiohttp.ClientSession()
as s:
async with
s.post("https://api.groq.com/openai/v1/chat
/completions",
headers=
{"Authorization":f"Bearer
{GROQ_API_KEY}","Content-
Type":"application/json"},
json=
{"model":GROQ_MODEL,"messages":
[{"role":"user","content":prompt}],"max_tok
ens":1000},
timeout=aiohttp.ClientTimeout(total=30)) as
r:
d=await r.json()
return d["choices"][0]
["message"]["content"]
except: pass
return "⚠ AI hozirda ishlamayapti."
async def ai_chat_req(history, user_text):
sys="Siz BilimChallenge botining
yordamchi AI sisiz. O'zbek tilida qisqa va
foydali javob bering."
try:
prompt=sys+"\n\n"
for h in history[-6:]:
role="Foydalanuvchi" if
h["role"]=="user" else "AI"
prompt+=f"{role}:
{h['content']}\n"
prompt+=f"Foydalanuvchi:
{user_text}\nAI:"
url=f"https://generativelanguage.googleapis
.com/v1beta/models/gemini-1.5-
flash:generateContent?key={GEMINI_API_KEY}"
async with aiohttp.ClientSession()
as s:
async with s.post(url,headers=
{"Content-Type":"application/json"},
json={"contents":[{"parts":
[{"text":prompt}]}]},
timeout=aiohttp.ClientTimeout(total=30)) as
r:
d=await r.json()
if "candidates" in d and
d["candidates"]:
return d["candidates"]
[0]["content"]["parts"][0]["text"]
except: pass
try:
msgs=
[{"role":"system","content":sys}]+history[-
6:]+[{"role":"user","content":user_text}]
async with aiohttp.ClientSession()
as s:
async with
s.post("https://api.groq.com/openai/v1/chat
/completions",
headers=
{"Authorization":f"Bearer
{GROQ_API_KEY}","Content-
Type":"application/json"},
json=
{"model":GROQ_MODEL,"messages":msgs,"max_to
kens":800},
timeout=aiohttp.ClientTimeout(total=30)) as
r:
d=await r.json()
return d["choices"][0]
["message"]["content"]
except: pass
return "⚠ AI hozirda ishlamayapti."
def parse_band(text):
for p in [r'Band\s*Score[:\s]+(\d+\.?
\d*)',r'(\d+\.?
\d*)\s*/\s*9(?:\.0)?',r'(\d+\.?
\d*)\s*ball']:
m=re.search(p,text,re.IGNORECASE)
if m:
try:
v=float(m.group(1))
if v<=9: return v
except: pass
return None
@dp.message(Command("start"))
async def cmd_start(message:
types.Message):
user=message.from_user
db.add_user(user.id,user.username or
"",user.first_name or "")
await message.answer(
f"🧠 <b>BilimChallenge</b> ga xush
kelibsiz, {user.first_name}!\n\n"
"🎯 Savollarga javob bering\n💰
Coinlar to'plang\n"
"🔥 Streak yig'ing\n🏆 Global
reyting\n🎓 IELTS — AI bilan\n🤖 AI
Chat\n\n"
"Boshlash uchun <b>Savol
olish</b>!",
parse_mode="HTML",reply_markup=main_menu(us
er.id))
@dp.message(Command("cancel"))
@dp.message(Command("stop"))
async def cancel_cmd(message:
types.Message, state: FSMContext):
await state.clear()
await message.answer("❌ Bekor
qilindi.",reply_markup=main_menu(message.fr
om_user.id))
@dp.message(F.text=="🎯 Savol olish")
async def get_question_start(message:
types.Message, state: FSMContext):
await state.clear()
cats=db.get_categories()
if not cats:
await message.answer("😔 Hozircha
savollar yo'q!"); return
buttons=[]; row=[]
for cat in cats:
row.append(InlineKeyboardButton(text=f"📂
{cat}",callback_data=f"cat_{cat}"))
if len(row)==2:
buttons.append(row); row=[]
if row: buttons.append(row)
buttons.append([InlineKeyboardButton(text="
🌐 Aralash
(barcha)",callback_data="cat_Barchasi")])
await message.answer("📂 <b>Kategoriya
tanlang:
</b>",parse_mode="HTML",reply_markup=Inline
KeyboardMarkup(inline_keyboard=buttons))
@dp.callback_query(F.data.startswith("cat_"
))
async def category_chosen(callback:
types.CallbackQuery, state: FSMContext):
category=callback.data[4:]
await
state.update_data(category=category)
try: await callback.message.delete()
except: pass
kb=InlineKeyboardMarkup(inline_keyboard=[
[InlineKeyboardButton(text="📝 Test
savollar",callback_data=f"qmode_test_{categ
ory}")],
[InlineKeyboardButton(text="✍
Ochiq
savollar",callback_data=f"qmode_open_{categ
ory}")],
[InlineKeyboardButton(text="🌐
Aralash",callback_data=f"qmode_all_{categor
y}")]])
await callback.message.answer(f"📂 <b>
{category}</b>\n\nSavol turini
tanlang:",parse_mode="HTML",reply_markup=kb
)
await callback.answer()
@dp.callback_query(F.data.startswith("qmode
_"))
async def qmode_chosen(callback:
types.CallbackQuery, state: FSMContext):
parts=callback.data.split("_",2);
mode,category=parts[1],parts[2]
await
state.update_data(category=category,qmode=m
ode)
try: await callback.message.delete()
except: pass
await
send_question(callback.message,callback.fro
m_user.id,state,category,mode)
await callback.answer()
async def
send_question(message,user_id,state,categor
y,mode="all"):
if mode=="test":
q=db.get_random_question(user_id,category,q
_type="test")
elif mode=="open":
q=db.get_random_question(user_id,category,q
_type="open")
else:
q=db.get_random_question(user_id,category,q
_type=None)
if not q:
cats=db.get_categories(); buttons=
[]; row=[]
for cat in cats:
row.append(InlineKeyboardButton(text=f"📂
{cat}",callback_data=f"cat_{cat}"))
if len(row)==2:
buttons.append(row); row=[]
if row: buttons.append(row)
buttons.append([InlineKeyboardButton(text="
🌐 Aralash",callback_data="cat_Barchasi")])
await message.answer("🎉 <b>Bu
bo'limdagi savollar tugadi!</b>\n\nBoshqa
kategoriyani tanlang:",
parse_mode="HTML",reply_markup=InlineKeyboa
rdMarkup(inline_keyboard=buttons)); return
q_id,q_text,q_type,options,correct,coins,ca
t,difficulty,explanation,image_id,time_limi
t=q
if q_type=="premium":
await
send_premium_question(message,user_id,state
,category); return
diff_icon=DIFFICULTY_ICONS.get(difficulty,"
🟡")
diff_name=DIFFICULTY_NAMES.get(difficulty,"
O'rta")
q_time=DIFFICULTY_TIME.get(difficulty,30)
header=(f"🆔 <b>#{q_id}</b> 📂 <b>
{cat}</b> {diff_icon} <b>{diff_name}
</b>\n"
f"💰 To'g'ri: <b>+{coins}
coin</b> ❌ Noto'g'ri: <b>-
{round(coins*PENALTY_PERCENT,1)}
coin</b>\n"
f"⏱ Vaqt: <b>{q_time}
soniya</b>\n\n❓ <b>{q_text}</b>")
try: await
bot.send_sticker(message.chat.id,sticker=ST
ICKER_QUESTION)
except: pass
if q_type=="test":
shuffled_opts,new_correct=shuffle_options(o
ptions,correct)
opts_list=shuffled_opts.split("|")
kb=InlineKeyboardMarkup(inline_keyboard=[
[InlineKeyboardButton(text=f"
{chr(65+i)}.
{opt[:64]}",callback_data=f"ans_{q_id}_{chr
(65+i)}_{new_correct}")]
for i,opt in
enumerate(opts_list)])
if image_id:
try: sent=await
bot.send_photo(message.chat.id,photo=image_
id,caption=header,parse_mode="HTML",reply_m
arkup=kb)
except: sent=await
message.answer(header,parse_mode="HTML",rep
ly_markup=kb)
else: sent=await
message.answer(header,parse_mode="HTML",rep
ly_markup=kb)
await
state.update_data(question_id=q_id,msg_id=s
ent.message_id,chat_id=message.chat.id)
if user_id in active_timers:
active_timers[user_id].cancel()
active_timers[user_id]=asyncio.create_task(
question_timeout(user_id,q_id,sent.message_
id,message.chat.id,coins,state,q_time))
else:
await
state.set_state(UserStates.answering_open)
await
state.update_data(question_id=q_id,correct=
correct,coins=coins,explanation=explanation
)
text=header+"\n\n✍ <b>Javobingizni
yozing:</b>"
if image_id:
try: sent=await
bot.send_photo(message.chat.id,photo=image_
id,caption=text,parse_mode="HTML")
except: sent=await
message.answer(text,parse_mode="HTML")
else: sent=await
message.answer(text,parse_mode="HTML")
await message.answer("👆 Javob
yozing:",reply_markup=InlineKeyboardMarkup(
inline_keyboard=[
[InlineKeyboardButton(text="⏭
O'tkazib
yuborish",callback_data=f"skip_open_{q_id}"
)]]))
if user_id in active_timers:
active_timers[user_id].cancel()
active_timers[user_id]=asyncio.create_task(
question_timeout(user_id,q_id,sent.message_
id,message.chat.id,coins,state,q_time))
async def
question_timeout(user_id,q_id,msg_id,chat_i
d,coins,state,q_time=30):
total=q_time; wait=total-10
if wait>0: await asyncio.sleep(wait)
timer_msg=None
for remaining in range(10,0,-1):
if
db.already_answered(user_id,q_id):
if timer_msg:
try: await
timer_msg.delete()
except: pass
return
filled=int((remaining/total)*10)
block="🟥" if remaining<=3 else
("🟧" if remaining<=6 else "🟨")
bar=block*filled+"⬜"*(10-filled)
try:
if timer_msg is None:
timer_msg=await
bot.send_message(chat_id,f"⏱ <b>
{remaining}s</b> {bar}",parse_mode="HTML")
else: await
timer_msg.edit_text(f"⏱ <b>
{remaining}s</b> {bar}",parse_mode="HTML")
except: pass
await asyncio.sleep(1)
if db.already_answered(user_id,q_id):
if timer_msg:
try: await timer_msg.delete()
except: pass
return
db.save_answer(user_id,q_id,False);
penalty=round(coins*TIMEOUT_PENALTY,1)
db.add_coins(user_id,-penalty);
db.update_streak(user_id,False)
if timer_msg:
try: await timer_msg.delete()
except: pass
try: await
bot.edit_message_reply_markup(chat_id=chat_
id,message_id=msg_id,reply_markup=None)
except: pass
try: await
bot.send_sticker(chat_id,sticker=random.cho
ice(STICKERS_TIMEOUT))
except: pass
data=await state.get_data()
cat=data.get("category","Barchasi");
mode=data.get("qmode","all")
try:
await bot.send_message(chat_id,f"⏰
<b>Vaqt tugadi!</b>\n❌ -{penalty} coin
(45%)",parse_mode="HTML",
reply_markup=InlineKeyboardMarkup(inline_ke
yboard=[[InlineKeyboardButton(text="➡
Keyingi
savol",callback_data=f"next_{mode}_{cat}")]
]))
except: pass
active_timers.pop(user_id,None)
@dp.callback_query(F.data.startswith("ans_"
))
async def handle_test_answer(callback:
types.CallbackQuery, state: FSMContext):
parts=callback.data.split("_")
q_id,ua,cl=int(parts[1]),parts[2],parts[3]
uid=callback.from_user.id
if db.already_answered(uid,q_id):
await callback.answer("⚠
Allaqachon javob
bergansiz!",show_alert=True); return
q=db.get_question_by_id(q_id)
if not q:
await callback.answer("Savol
topilmadi!",show_alert=True); return
q_id,q_text,q_type,options,correct,coins,ca
t,diff,explanation,image_id,tl=q
is_correct=ua.upper()==cl.upper()
db.save_answer(uid,q_id,is_correct)
if uid in active_timers:
active_timers[uid].cancel();
active_timers.pop(uid,None)
data=await state.get_data()
cat2=data.get("category","Barchasi");
mode=data.get("qmode","all")
if is_correct:
ns=db.update_streak(uid,True);
bonus=streak_bonus(ns);
earned=round(coins*bonus,1)
db.add_coins(uid,earned); text=f"✅
<b>To'g'ri!</b> +{earned} coin 🎉"
if bonus>1: text+=f"\n🔥 Streak
bonusi x{bonus}!"
sm=streak_msg(ns)
if sm: text+=f"\n{sm}"
else:
db.update_streak(uid,False);
penalty=round(coins*PENALTY_PERCENT,1)
db.add_coins(uid,-penalty)
opts_list=options.split("|");
ci=ord(correct.upper())-65
ct=opts_list[ci] if
ci<len(opts_list) else correct
text=f"❌ <b>Noto'g'ri!</b> -
{penalty} coin\n✅ To'g'ri javob: <b>{ct}
</b>"
if explanation: text+=f"\n\n💡 <i>
{explanation}</i>"
ud=db.get_user(uid); text+=f"\n\n💰
Coinlar: <b>{round(ud[3],1) if ud else 0}
</b> 🔥 Streak: <b>{ud[6] if ud else 0}
</b>"
try: await
callback.message.edit_reply_markup(reply_ma
rkup=None)
except: pass
try: await
bot.send_sticker(callback.message.chat.id,s
ticker=get_correct_sticker(coins) if
is_correct else get_wrong_sticker(coins))
except: pass
await
callback.message.answer(text,parse_mode="HT
ML",reply_markup=InlineKeyboardMarkup(inlin
e_keyboard=[[InlineKeyboardButton(text="➡
Keyingi
savol",callback_data=f"next_{mode}_{cat2}")
]]))
await callback.answer()
@dp.message(UserStates.answering_open)
async def handle_open_answer(message:
types.Message, state: FSMContext):
data=await state.get_data()
q_id,correct,coins=data["question_id"],data
["correct"],data["coins"]
explanation=data.get("explanation","");
cat=data.get("category","Barchasi");
mode=data.get("qmode","all")
uid=message.from_user.id
if db.already_answered(uid,q_id): await
state.clear(); return
is_correct=check_answer(message.text,correc
t)
db.save_answer(uid,q_id,is_correct)
if uid in active_timers:
active_timers[uid].cancel();
active_timers.pop(uid,None)
if is_correct:
ns=db.update_streak(uid,True);
bonus=streak_bonus(ns);
earned=round(coins*bonus,1)
db.add_coins(uid,earned); text=f"✅
<b>To'g'ri!</b> +{earned} coin 🎉"
if bonus>1: text+=f"\n🔥 Streak
bonusi x{bonus}!"
sm=streak_msg(ns)
if sm: text+=f"\n{sm}"
else:
db.update_streak(uid,False);
penalty=round(coins*PENALTY_PERCENT,1)
db.add_coins(uid,-penalty);
fc=correct.split("\n")[0].strip()
text=f"❌ <b>Noto'g'ri!</b> -
{penalty} coin\n✅ To'g'ri javob: <b>{fc}
</b>"
if explanation: text+=f"\n\n💡 <i>
{explanation}</i>"
ud=db.get_user(uid); text+=f"\n\n💰
Coinlar: <b>{round(ud[3],1) if ud else 0}
</b> 🔥 Streak: <b>{ud[6] if ud else 0}
</b>"
try: await
bot.send_sticker(message.chat.id,sticker=ge
t_correct_sticker(coins) if is_correct else
get_wrong_sticker(coins))
except: pass
await
message.answer(text,parse_mode="HTML",reply
_markup=InlineKeyboardMarkup(inline_keyboar
d=[[InlineKeyboardButton(text="➡ Keyingi
savol",callback_data=f"next_{mode}_{cat}")]
]))
await state.clear()
@dp.callback_query(F.data.startswith("skip_
open_"))
async def skip_open(callback:
types.CallbackQuery, state: FSMContext):
data=await state.get_data();
cat=data.get("category","Barchasi");
mode=data.get("qmode","all")
await state.clear()
try: await
callback.message.edit_reply_markup(reply_ma
rkup=None)
except: pass
await callback.message.answer("⏭
O'tkazib
yuborildi.",reply_markup=InlineKeyboardMark
up(inline_keyboard=
[[InlineKeyboardButton(text="➡ Keyingi
savol",callback_data=f"next_{mode}_{cat}")]
]))
await callback.answer()
@dp.callback_query(F.data.startswith("next_
"))
async def next_question(callback:
types.CallbackQuery, state: FSMContext):
parts=callback.data.split("_",2);
mode,cat=parts[1],parts[2]
await
state.update_data(category=cat,qmode=mode)
try: await
callback.message.edit_reply_markup(reply_ma
rkup=None)
except: pass
await
send_question(callback.message,callback.fro
m_user.id,state,cat,mode)
await callback.answer()
@dp.callback_query(F.data.startswith("premi
um_start_"))
async def premium_start(callback:
types.CallbackQuery, state: FSMContext):
await
send_premium_question(callback.message,call
back.from_user.id,state,callback.data[14:])
await callback.answer()
async def
send_premium_question(message,user_id,state
,category):
q=db.get_random_question(user_id,category,q
_type="premium")
if not q:
await message.answer("😔 Premium
savollar tugadi!"); return
q_id,q_text,q_type,options,correct,coins,ca
t,diff,explanation,image_id,tl=q
await
state.set_state(UserStates.answering_premiu
m)
await
state.update_data(question_id=q_id,correct=
correct,coins=coins,explanation=explanation
,category=category,attempts=0)
header=(f"⭐ <b>PREMIUM SAVOL</b> 🆔 #
{q_id}\n📂 <b>{cat}</b>\n"
f"💰 To'g'ri: <b>+{coins}
coin</b>\n🔄 3 ta urinish | ⏭ O'tkazish
| ❌ Jarima yo'q\n\n❓ <b>{q_text}</b>")
skip_kb=InlineKeyboardMarkup(inline_keyboar
d=[[InlineKeyboardButton(text="⏭ O'tkazib
yuborish",callback_data=f"skip_premium_{q_i
d}_{category}")]])
if image_id:
try: await
bot.send_photo(message.chat.id,photo=image_
id,caption=header+"\n\n✍ <b>Javob yozing:
</b>",parse_mode="HTML")
except: await
message.answer(header+"\n\n✍ <b>Javob
yozing:</b>",parse_mode="HTML")
else: await message.answer(header+"\n\n
✍ <b>Javob yozing:</b>",parse_mode="HTML")
await message.answer("👆 Javob yozing
yoki o'tkazing:",reply_markup=skip_kb)
@dp.message(UserStates.answering_premium)
async def handle_premium(message:
types.Message, state: FSMContext):
data=await state.get_data()
q_id,correct,coins=data["question_id"],data
["correct"],data["coins"]
explanation=data.get("explanation","");
cat=data.get("category","Barchasi");
attempts=data.get("attempts",0)
uid=message.from_user.id
if db.already_answered(uid,q_id): await
state.clear(); return
is_correct=check_answer(message.text,correc
t)
if is_correct:
db.save_answer(uid,q_id,True);
ns=db.update_streak(uid,True);
bonus=streak_bonus(ns)
earned=round(coins*bonus,1);
db.add_coins(uid,earned)
text=f"✅ <b>To'g'ri!</b> +{earned}
coin 🎉"
if bonus>1: text+=f"\n🔥 Streak
bonusi x{bonus}!"
if explanation: text+=f"\n\n💡 <i>
{explanation}</i>"
ud=db.get_user(uid); text+=f"\n\n💰
Coinlar: <b>{round(ud[3],1) if ud else 0}
</b>"
try: await
bot.send_sticker(message.chat.id,sticker=ge
t_correct_sticker(coins))
except: pass
await
message.answer(text,parse_mode="HTML",reply
_markup=InlineKeyboardMarkup(inline_keyboar
d=[[InlineKeyboardButton(text="⭐ Keyingi
premium
savol",callback_data=f"premium_start_{cat}"
)]]))
await state.clear()
else:
attempts+=1; remaining=3-attempts
if remaining>0:
await
state.update_data(attempts=attempts)
await message.answer(f"❌
Noto'g'ri! <b>{remaining} ta urinish</b>
qoldi:",parse_mode="HTML")
else:
db.save_answer(uid,q_id,False);
db.update_streak(uid,False)
try: await
bot.send_sticker(message.chat.id,sticker=ra
ndom.choice(STICKERS_WRONG_RANDOM))
except: pass
await message.answer("😔 3 ta
urinish
tugadi.",reply_markup=InlineKeyboardMarkup(
inline_keyboard=
[[InlineKeyboardButton(text="⭐ Keyingi
premium
savol",callback_data=f"premium_start_{cat}"
)]]))
await state.clear()
@dp.callback_query(F.data.startswith("skip_
premium_"))
async def skip_premium(callback:
types.CallbackQuery, state: FSMContext):
parts=callback.data.split("_");
q_id,cat=int(parts[2]),parts[3]
db.save_answer(callback.from_user.id,q_id,F
alse); await state.clear()
try: await
callback.message.edit_reply_markup(reply_ma
rkup=None)
except: pass
await callback.message.answer("⏭
O'tkazib
yuborildi.",reply_markup=InlineKeyboardMark
up(inline_keyboard=
[[InlineKeyboardButton(text="⭐ Keyingi
premium
savol",callback_data=f"premium_start_{cat}"
)]]))
await callback.answer()
@dp.message(F.text=="🎓 IELTS")
async def ielts_menu(message:
types.Message):
kb=InlineKeyboardMarkup(inline_keyboard=[
[InlineKeyboardButton(text="📝
Writing",callback_data="ielts_writing"),Inl
ineKeyboardButton(text="✍
Essay",callback_data="ielts_essay")],
[InlineKeyboardButton(text="📖
Reading",callback_data="ielts_reading"),Inl
ineKeyboardButton(text="🗣
Speaking",callback_data="ielts_speaking")],
[InlineKeyboardButton(text="🎧
Listening",callback_data="ielts_listening")
]])
await message.answer("🎓 <b>IELTS
bo'limlari</b>\n\nAI yordamida mashq
qiling!",parse_mode="HTML",reply_markup=kb)
@dp.callback_query(F.data.startswith("ielts
_"))
async def ielts_section(callback:
types.CallbackQuery, state: FSMContext):
section=callback.data[6:]
q=db.get_random_question(callback.from_user
.id,q_type=section)
if not q:
await callback.answer("🎉 Bu
bo'limdagi barcha savollarga javob
berdingiz!",show_alert=True); return
q_id,q_text,q_type,options,correct,coins,ca
t,diff,explanation,image_id,tl=q
await
state.set_state(UserStates.answering_ielts)
await
state.update_data(question_id=q_id,q_type=q
_type,coins=coins,section=section)
tl_note=f"\n⏰ <b>Vaqt:</b> {tl}" if tl
else ""
icons=
{"writing":"📝","essay":"✍","reading":"📖"
,"speaking":"🗣","listening":"🎧"}
header=f"{icons.get(section,'🎓')} <b>
{section.upper()}</b> 🆔 #{q_id}
{tl_note}\n\n❓ <b>{q_text}</b>"
if section=="reading": header+="\n\n📌
<i>Javoblarni qatorma-qator yozing</i>"
elif section in
["speaking","listening"]: header+="\n\n🎙
<i>Ovozli xabar yoki matn yuboring</i>"
else: header+="\n\n✍ <i>Javobingizni
yozing</i>"
if image_id:
try: await
bot.send_photo(callback.message.chat.id,pho
to=image_id,caption=header,parse_mode="HTML
")
except: await
callback.message.answer(header,parse_mode="
HTML")
else: await
callback.message.answer(header,parse_mode="
HTML")
await callback.message.answer("👆 Javob
yuboring:",reply_markup=InlineKeyboardMarku
p(inline_keyboard=
[[InlineKeyboardButton(text="⏭ O'tkazib
yuborish",callback_data=f"skip_ielts_{secti
on}")]]))
await callback.answer()
@dp.message(UserStates.answering_ielts)
async def handle_ielts(message:
types.Message, state: FSMContext):
data=await state.get_data()
q_id,coins,section=data["question_id"],data
["coins"],data["section"]
uid=message.from_user.id
if section=="reading":
if not message.text:
await message.answer("✍ Matn
yuboring!"); return
q=db.get_question_by_id(q_id);
correct_ans=q[4] if q else ""
uas=[a.strip().lower() for a in
message.text.split("\n") if a.strip()]
cls=[a.strip().lower() for a in
correct_ans.split("\n") if a.strip()]
cc=sum(1 for a in uas if a in cls);
total=len(cls)
score=round((cc/total*9),1) if
total>0 else 0
earned=round(coins*(cc/total),1) if
total>0 else 0
db.add_coins(uid,earned)
try:
db.save_answer(uid,q_id,cc==total)
except: pass
result=f"📖 <b>Reading
natijasi</b>\n\n✅ To'g'ri: <b>{cc}/{total}
</b>\nBand Score: <b>{score}/9.0</b>"
if cc<total:
wrong=[a for a in cls if a not
in uas]
result+="\n\n❌ To'g'ri
javoblar:\n"+"\n".join([f"• {w}" for w in
wrong])
result+=f"\n\n💰 +{earned} coin"
await
message.answer(result,parse_mode="HTML",rep
ly_markup=InlineKeyboardMarkup(inline_keybo
ard=[[InlineKeyboardButton(text=f"➡
Keyingi
{section.upper()}",callback_data=f"ielts_{s
ection}")]]))
await state.clear(); return
if section in ["speaking","listening"]:
if message.voice:
await message.answer("⏳ Tahlil
qilinmoqda...")
prompt=f"Siz IELTS
{section.capitalize()} baholovchisiz.
O'zbek tilida baholang. Foydalanuvchi
ovozli xabar yubordi. Umumiy tavsiyalar
bering. Band Score: X.X/9.0"
elif message.text:
await message.answer("⏳ AI
tahlil qilmoqda...")
prompt=f"Siz IELTS
{section.capitalize()} baholovchisiz.
O'zbek tilida
baholang:\n\n{message.text}\n\nBand Score:
X.X/9.0. Tavsiyalar bering."
else:
await message.answer("🎙 Ovozli
xabar yoki matn yuboring!"); return
elif section in ["writing","essay"]:
if not message.text:
await message.answer("✍ Matn
yuboring!"); return
await message.answer("⏳ AI tahlil
qilmoqda...")
if section=="writing":
prompt=f"Siz IELTS Writing
baholovchisiz. O'ZBEK TILIDA
baholang:\n\n{message.text}\n\n1.Task
Achievement 2.Coherence 3.Lexical Resource
4.Grammar\n\nBand Score: X.X/9.0\n3 ta
tavsiya."
else:
prompt=f"Siz akademik insho
mutaxassisisiz. O'ZBEK TILIDA tahlil
qiling:\n\n{message.text}\n\n1.Kirish
2.Argumentlar 3.Xulosa 4.Uslub
5.Grammatika\n\nUmumiy baho: X/10. 5 ta
tavsiya."
else:
await message.answer("❓ Noma'lum
bo'lim."); return
analysis=await ai_req(prompt)
band_score=parse_band(analysis)
earned=round(coins*(band_score/9.0),1)
if band_score else round(coins*0.5,1)
db.add_coins(uid,earned)
try: db.save_answer(uid,q_id,True)
except: pass
st=f"\n🎯 Band Score: <b>
{band_score}/9.0</b>" if band_score else ""
await message.answer(f"🤖 <b>AI Tahlil:
</b>\n\n{analysis}{st}\n\n💰 +{earned} coin
(max {coins})",
parse_mode="HTML",reply_markup=InlineKeyboa
rdMarkup(inline_keyboard=
[[InlineKeyboardButton(text=f"➡ Keyingi
{section.upper()}",callback_data=f"ielts_{s
ection}")]]))
await state.clear()
@dp.callback_query(F.data.startswith("skip_
ielts_"))
async def skip_ielts(callback:
types.CallbackQuery, state: FSMContext):
section=callback.data[11:]; await
state.clear()
try: await
callback.message.edit_reply_markup(reply_ma
rkup=None)
except: pass
await callback.message.answer("⏭
O'tkazib
yuborildi.",reply_markup=InlineKeyboardMark
up(inline_keyboard=
[[InlineKeyboardButton(text=f"➡ Keyingi
{section.upper()}",callback_data=f"ielts_{s
ection}")]]))
await callback.answer()
@dp.message(F.text=="🤖 AI Chat")
async def ai_chat_start(message:
types.Message, state: FSMContext):
cs=await state.get_state()
busy=
[UserStates.answering_open.state,UserStates
.answering_premium.state,UserStates.answeri
ng_ielts.state]
if cs in busy:
await message.answer("⚠ Avval
joriy savolingizga javob bering!"); return
user=db.get_user(message.from_user.id);
coins=round(user[3],1) if user else 0
if coins<=0:
await message.answer(f"❌ <b>AI
Chat ishlamaydi!</b>\n\n💰 Coinlaringiz:
<b>{coins}</b>\n\nAvval savollarga javob
berib coin to'plang!",parse_mode="HTML");
return
await
state.set_state(UserStates.ai_chat); await
state.update_data(chat_history=[])
await message.answer(f"🤖 <b>AI
Chat</b>\n\n💰 Coinlaringiz: <b>{coins}
</b>\n💸 Narx: har 15 belgi = 1
coin\n\nSavolingizni yozing!\n<i>Chiqish:
/stop</i>",
parse_mode="HTML",reply_markup=ReplyKeyboar
dMarkup(keyboard=[[KeyboardButton(text="🚪
AI Chatdan
chiqish")]],resize_keyboard=True))
@dp.message(F.text=="🚪 AI Chatdan
chiqish")
async def ai_chat_exit(message:
types.Message, state: FSMContext):
await state.clear()
await message.answer("👋 AI Chatdan
chiqdingiz!",reply_markup=main_menu(message
.from_user.id))
@dp.message(UserStates.ai_chat)
async def handle_ai_chat(message:
types.Message, state: FSMContext):
if not message.text: return
uid=message.from_user.id;
ut=message.text.strip()
for word in ILLEGAL_WORDS:
if word in ut.lower():
db.add_coins(uid,-10);
user=db.get_user(uid)
await message.answer(f"🚫
<b>JARIMA!</b>\n\n❌ -10 coin\n💰 Qoldi:
<b>{round(user[3],1) if user else 0}
</b>",parse_mode="HTML"); return
user=db.get_user(uid);
coins=round(user[3],1) if user else 0
if coins<=0:
await state.clear()
await message.answer("❌
<b>Coinlaringiz tugadi!
</b>",parse_mode="HTML",reply_markup=main_m
enu(uid)); return
data=await state.get_data();
history=data.get("chat_history",[])
await message.answer("⏳ AI
o'ylayapti...")
ai_reply=await ai_chat_req(history,ut)
cost=max(1,len(ai_reply)//15)
if coins<cost:
await
state.update_data(pending_reply=ai_reply,pe
nding_cost=cost,chat_history=history)
await
state.set_state(UserStates.ai_chat_confirm_
debt)
kb=InlineKeyboardMarkup(inline_keyboard=
[[InlineKeyboardButton(text="✅ Ha, qarz
olaman",callback_data="ai_debt_yes")],
[InlineKeyboardButton(text="❌
Yo'q",callback_data="ai_debt_no")]])
await message.answer(f"⚠ <b>Coin
yetarli emas!</b>\n\n💰 Sizda: <b>{coins}
</b>\n💸 Kerak: <b>{cost}</b>\n\nQarz
olasizmi?",parse_mode="HTML",reply_markup=k
b); return
db.add_coins(uid,-cost);
user=db.get_user(uid);
coins_left=round(user[3],1) if user else 0
history.append({"role":"user","content":ut}
);
history.append({"role":"assistant","content
":ai_reply})
await
state.update_data(chat_history=history);
await state.set_state(UserStates.ai_chat)
await message.answer(f"🤖
{ai_reply}\n\n💰 -{cost} coin | Qoldi:
<b>{coins_left}</b>",parse_mode="HTML")
@dp.callback_query(F.data=="ai_debt_yes")
async def ai_debt_yes(callback:
types.CallbackQuery, state: FSMContext):
data=await state.get_data()
ai_reply,cost,history=data.get("pending_rep
ly",""),data.get("pending_cost",0),data.get
("chat_history",[])
uid=callback.from_user.id;
db.add_coins(uid,-cost);
user=db.get_user(uid)
coins_left=round(user[3],1) if user
else 0
history.append({"role":"assistant","content
":ai_reply})
await
state.update_data(chat_history=history);
await state.set_state(UserStates.ai_chat)
try: await
callback.message.edit_reply_markup(reply_ma
rkup=None)
except: pass
await callback.message.answer(f"🤖
{ai_reply}\n\n💰 -{cost} coin | Qoldi:
<b>{coins_left}</b>",parse_mode="HTML")
await callback.answer()
@dp.callback_query(F.data=="ai_debt_no")
async def ai_debt_no(callback:
types.CallbackQuery, state: FSMContext):
try: await
callback.message.edit_reply_markup(reply_ma
rkup=None)
except: pass
await callback.message.answer("❌ Bekor
qilindi.")
await
state.set_state(UserStates.ai_chat); await
callback.answer()
@dp.message(F.text=="🏆 Reyting")
async def show_leaderboard(message:
types.Message):
top=db.get_leaderboard(10)
if not top:
await message.answer("😔 Hali hech
kim reyting ro'yxatida yo'q!"); return
try: await
bot.send_sticker(message.chat.id,sticker=ST
ICKER_LEADERBOARD)
except: pass
medals=["🥇","🥈","🥉"]
text="🏆 <b>Global Reyting — Top
10</b>\n\n"
for i,(uid,fname,uname,coins) in
enumerate(top):
medal=medals[i] if i<3 else f"
{i+1}."
name=fname or uname or f"User{uid}"
text+=f"{medal} <b>{name}</b> —
{round(coins,1)} coin\n"
rank=db.get_user_rank(message.from_user.id)
text+=f"\n📍 Sizning o'rningiz: <b>#
{rank}</b>"
await
message.answer(text,parse_mode="HTML")
rs=get_rank_sticker(rank)
if rs:
try:
await
bot.send_sticker(message.chat.id,sticker=rs
)
msgs={1:"🎉 BIRINCHI
O'RIN!",2:"🎉 IKKINCHI O'RIN!",3:"🎉
UCHINCHI O'RIN!"}
await message.answer(f"<b>
{msgs.get(rank,f'🎉 Top {rank} da
turibsiz!')}</b>",parse_mode="HTML")
except: pass
@dp.message(F.text=="👤 Profilim")
async def show_profile(message:
types.Message):
user=db.get_user(message.from_user.id)
if not user:
await message.answer("Profil
topilmadi!"); return
uid,username,fname,coins,total_ans,correct_
ans,streak,max_streak,join_date=user
rank=db.get_user_rank(uid)
accuracy=round((correct_ans/total_ans*100),
1) if total_ans>0 else 0
await message.answer(
f"👤 <b>Profil — {fname}</b>\n\n💰
Coinlar: <b>{round(coins,1)}</b>\n🏆
Reyting: <b>#{rank}</b>\n"
f"🔥 Streak: <b>{streak}</b> ⚡
Max: <b>{max_streak}</b>\n"
f"📝 Javob: <b>{total_ans}</b> ✅
To'g'ri: <b>{correct_ans}</b>\n"
f"🎯 Aniqlik: <b>{accuracy}%</b>\n
📅 Qo'shilgan: <b>{join_date[:10]}
</b>",parse_mode="HTML")
@dp.message(F.text=="ℹ Yordam")
async def show_help(message:
types.Message):
await message.answer("ℹ
<b>BilimChallenge — Yordam</b>\n\n🎯 Savol
olish — kategoriya va tur\n🎓 IELTS — AI
bilan mashq\n🤖 AI Chat — coinlar evaziga\n
🏆 Reyting — top 10\n\n💰 To'g'ri —
coin\n❌ Noto'g'ri — 30% jarima\n⏰ Vaqt —
45% jarima\n🔥x3=1.5 🔥🔥x5=2.0 🔥🔥🔥
x10=3.0\n🟢Oson=30s 🟡O'rta=60s
🔴Qiyin=90s",parse_mode="HTML")
@dp.message(F.text=="📝 Taklif/Shikoyat")
async def feedback_start(message:
types.Message, state: FSMContext):
await
state.set_state(UserStates.sending_feedback
)
await message.answer("📝 <b>Taklif yoki
shikoyatingizni yozing:</b>\n\n<i>/cancel —
bekor qilish</i>",parse_mode="HTML")
@dp.message(UserStates.sending_feedback)
async def receive_feedback(message:
types.Message, state: FSMContext):
user=message.from_user
db.save_feedback(user.id,user.first_name or
"",user.username or "",message.text)
await state.clear()
await message.answer("✅ <b>Xabaringiz
adminga yuborildi!
</b>",parse_mode="HTML",reply_markup=main_m
enu(user.id))
@dp.message(F.text=="⚙ Admin Panel")
async def admin_panel(message:
types.Message):
if not is_admin(message.from_user.id):
return
await message.answer("⚙ <b>Admin
Panel</b>",parse_mode="HTML",reply_markup=a
dmin_menu())
@dp.message(F.text=="🔙 Asosiy menyu")
async def back_to_main(message:
types.Message, state: FSMContext):
await state.clear()
await message.answer("🏠 Asosiy
menyu",reply_markup=main_menu(message.from_
user.id))
@dp.message(F.text=="💬 Takliflar")
async def show_feedbacks(message:
types.Message):
if not is_admin(message.from_user.id):
return
feedbacks=db.get_feedbacks(20)
if not feedbacks:
await message.answer("💬 Hali
taklif yo'q."); return
for fb in feedbacks[:10]:
fb_id,user_id,fname,username,fb_text,fb_dat
e,is_read=fb
read_icon="🆕" if not is_read else
"✅"
uname=f"@{username}" if username
else f"ID:{user_id}"
await message.answer(f"{read_icon}
<b>#{fb_id}</b> — {fname} ({uname})\n📅
{fb_date[:10]}\n\n{fb_text}",
parse_mode="HTML",reply_markup=InlineKeyboa
rdMarkup(inline_keyboard=
[[InlineKeyboardButton(text="🗑
O'chirish",callback_data=f"del_fb_{fb_id}")
]]))
await message.answer(f"Jami: <b>
{len(feedbacks)}</b> ta",parse_mode="HTML",
reply_markup=InlineKeyboardMarkup(inline_ke
yboard=[[InlineKeyboardButton(text="✅
Barchasini
tozalash",callback_data="mark_all_read")]])
)
@dp.callback_query(F.data.startswith("del_f
b_"))
async def delete_feedback(callback:
types.CallbackQuery):
db.delete_feedback(int(callback.data[7:]))
await callback.message.edit_text("🗑
O'chirildi.")
await callback.answer()
@dp.callback_query(F.data=="mark_all_read")
async def mark_all_read(callback:
types.CallbackQuery):
db.mark_feedbacks_read()
await callback.message.edit_text("✅
Tozalandi!")
await callback.answer()
@dp.message(F.text=="📂 Kategoriyalar")
async def manage_categories(message:
types.Message):
if not is_admin(message.from_user.id):
return
cats=db.get_categories_with_count()
text="📂 <b>Kategoriyalar</b>\n\n"
for cat,count in cats: text+=f"• <b>
{cat}</b> — {count} ta\n"
if not cats: text+="Hali kategoriya
yo'q"
kb=InlineKeyboardMarkup(inline_keyboard=
[[InlineKeyboardButton(text="➕ Yangi
kategoriya",callback_data="add_category")],
[InlineKeyboardButton(text="🗑
O'chirish",callback_data="del_category_list
")]])
await
message.answer(text,parse_mode="HTML",reply
_markup=kb)
@dp.callback_query(F.data=="add_category")
async def add_cat_start(callback:
types.CallbackQuery, state: FSMContext):
await
state.set_state(AdminStates.waiting_new_cat
egory)
await callback.message.answer("📂 Yangi
kategoriya nomini kiriting:")
await callback.answer()
@dp.message(AdminStates.waiting_new_categor
y)
async def save_new_category(message:
types.Message, state: FSMContext):
db.add_category(message.text.strip());
await state.clear()
await message.answer(f"✅ <b>
{message.text.strip()}</b>
qo'shildi!",parse_mode="HTML",reply_markup=
admin_menu())
@dp.callback_query(F.data=="del_category_li
st")
async def del_cat_list(callback:
types.CallbackQuery):
cats=db.get_categories()
if not cats:
await callback.answer("Kategoriya
yo'q!",show_alert=True); return
buttons=
[[InlineKeyboardButton(text=f"🗑
{c}",callback_data=f"delcat_{c}")] for c in
cats]
await callback.message.answer("Qaysi
kategoriyani
o'chirish?",reply_markup=InlineKeyboardMark
up(inline_keyboard=buttons))
await callback.answer()
@dp.callback_query(F.data.startswith("delca
t_"))
async def delete_category_cb(callback:
types.CallbackQuery):
cat=callback.data[7:];
db.delete_category(cat)
await callback.message.edit_text(f"✅
<b>{cat}</b>
o'chirildi!",parse_mode="HTML")
await callback.answer()
@dp.message(F.text=="➕ Savol qo'shish")
async def add_question_start(message:
types.Message, state: FSMContext):
if not is_admin(message.from_user.id):
return
await state.clear(); await
state.set_state(AdminStates.waiting_questio
n_type)
kb=InlineKeyboardMarkup(inline_keyboard=[
[InlineKeyboardButton(text="📝 Test
(A,B,C,D)",callback_data="qtype_test")],
[InlineKeyboardButton(text="✍
Ochiq savol",callback_data="qtype_open")],
[InlineKeyboardButton(text="⭐
Premium
savol",callback_data="qtype_premium")],
[InlineKeyboardButton(text="📝
IELTS
Writing",callback_data="qtype_writing")],
[InlineKeyboardButton(text="✍
IELTS Essay",callback_data="qtype_essay")],
[InlineKeyboardButton(text="📖
IELTS
Reading",callback_data="qtype_reading")],
[InlineKeyboardButton(text="🗣
IELTS
Speaking",callback_data="qtype_speaking")],
[InlineKeyboardButton(text="🎧
IELTS
Listening",callback_data="qtype_listening")
]])
await message.answer("📌 Savol turini
tanlang:",reply_markup=kb)
@dp.callback_query(F.data.startswith("qtype
_"))
async def choose_qtype(callback:
types.CallbackQuery, state: FSMContext):
qtype=callback.data[6:]
await state.update_data(q_type=qtype);
await
state.set_state(AdminStates.waiting_questio
n_text)
await callback.message.edit_text("✏
Savol matnini kiriting:")
await callback.answer()
@dp.message(AdminStates.waiting_question_te
xt)
async def get_question_text(message:
types.Message, state: FSMContext):
data=await state.get_data();
qtype=data["q_type"]
if message.text and
message.text.strip()=="/done":
accumulated=data.get("accumulated_text","")
if not accumulated:
await message.answer("⚠ Avval
matn yuboring!"); return
await
state.update_data(q_text=accumulated)
if qtype=="reading":
await
state.set_state(AdminStates.waiting_correct
_answer)
await message.answer("✅
To'g'ri javoblarni kiriting (har biri yangi
qatorda):")
elif qtype in IELTS_TYPES:
await
state.update_data(correct="",options="")
await
state.set_state(AdminStates.waiting_coin_re
ward)
await message.answer("💰 Bu
savol uchun necha coin?")
else:
await
state.set_state(AdminStates.waiting_correct
_answer)
await message.answer("✅
To'g'ri javobni kiriting:")
return
if qtype in ["reading"]+IELTS_TYPES:
prev=data.get("accumulated_text","")
new_text=
(prev+"\n"+message.text).strip() if prev
else message.text
await
state.update_data(accumulated_text=new_text
)
await message.answer(f"✅ Qabul
qilindi ({len(new_text)} belgi)\n\nDavom
eting yoki <b>/done</b>
yozing",parse_mode="HTML")
return
await
state.update_data(q_text=message.text)
if qtype=="test":
await
state.set_state(AdminStates.waiting_options
)
await message.answer("📋
Variantlarni kiriting (har biri yangi
qatorda):")
else:
await
state.set_state(AdminStates.waiting_correct
_answer)
await message.answer("✅ To'g'ri
javobni kiriting:")
@dp.message(AdminStates.waiting_options)
async def get_options(message:
types.Message, state: FSMContext):
options=[o.strip() for o in
message.text.split("\n") if o.strip()]
if len(options)<2:
await message.answer("⚠ Kamida 2
ta variant!"); return
await
state.update_data(options="|".join(options)
)
await
state.set_state(AdminStates.waiting_correct
_answer)
opts_text="\n".join([f"{chr(65+i)}.
{opt}" for i,opt in enumerate(options)])
await message.answer(f"📋
Variantlar:\n{opts_text}\n\n✅ To'g'ri
variant harfini kiriting (A/B/C/D):")
@dp.message(AdminStates.waiting_correct_ans
wer)
async def get_correct_answer(message:
types.Message, state: FSMContext):
await
state.update_data(correct=message.text.stri
p())
await
state.set_state(AdminStates.waiting_coin_re
ward)
await message.answer("💰 Necha coin?")
@dp.message(AdminStates.waiting_coin_reward
)
async def get_coins(message: types.Message,
state: FSMContext):
if not
message.text.replace(".","").isdigit():
await message.answer("⚠ Faqat
raqam!"); return
await
state.update_data(coins=float(message.text)
)
data=await state.get_data();
qtype=data["q_type"]
if qtype in IELTS_TYPES+["premium"]:
await
state.set_state(AdminStates.waiting_time_li
mit)
await message.answer("⏰ Vaqtni
kiriting (masalan: 20 daqiqa)\n<i>Kerak
bo'lmasa '-' yozing</i>",parse_mode="HTML")
else:
await
state.set_state(AdminStates.waiting_difficu
lty)
kb=InlineKeyboardMarkup(inline_keyboard=
[[InlineKeyboardButton(text="🟢
Oson",callback_data="diff_oson")],
[InlineKeyboardButton(text="🟡
O'rta",callback_data="diff_orta")],
[InlineKeyboardButton(text="🔴
Qiyin",callback_data="diff_qiyin")]])
await message.answer("📊 Qiyinlik
darajasi:",reply_markup=kb)
@dp.message(AdminStates.waiting_time_limit)
async def get_time_limit(message:
types.Message, state: FSMContext):
tl="" if message.text.strip()=="-" else
message.text.strip()
await
state.update_data(time_limit=tl,difficulty=
"orta")
data=await state.get_data();
qtype=data["q_type"]
if qtype in IELTS_TYPES:
await
state.update_data(category=qtype.upper())
await
state.set_state(AdminStates.waiting_explana
tion)
await message.answer("💡 Tavsif
(ixtiyoriy):\n<i>'-' = kerak
emas</i>",parse_mode="HTML")
else:
await
state.set_state(AdminStates.waiting_categor
y)
cats=db.get_categories(); buttons=
[]; row=[]
for cat in cats:
row.append(InlineKeyboardButton(text=cat,ca
llback_data=f"selcat_{cat}"))
if len(row)==2:
buttons.append(row); row=[]
if row: buttons.append(row)
buttons.append([InlineKeyboardButton(text="
➕ Yangi
kategoriya",callback_data="selcat_NEW")])
await message.answer("📂
Kategoriyani
tanlang:",reply_markup=InlineKeyboardMarkup
(inline_keyboard=buttons))
@dp.callback_query(F.data.startswith("diff_
"))
async def get_difficulty(callback:
types.CallbackQuery, state: FSMContext):
difficulty=callback.data.split("_")[1]
await
state.update_data(difficulty=difficulty,tim
e_limit="")
await
state.set_state(AdminStates.waiting_categor
y)
cats=db.get_categories(); buttons=[];
row=[]
for cat in cats:
row.append(InlineKeyboardButton(text=cat,ca
llback_data=f"selcat_{cat}"))
if len(row)==2:
buttons.append(row); row=[]
if row: buttons.append(row)
buttons.append([InlineKeyboardButton(text="
➕ Yangi
kategoriya",callback_data="selcat_NEW")])
await callback.message.edit_text("📂
Kategoriyani
tanlang:",reply_markup=InlineKeyboardMarkup
(inline_keyboard=buttons))
await callback.answer()
@dp.callback_query(F.data.startswith("selca
t_"))
async def select_category(callback:
types.CallbackQuery, state: FSMContext):
cat=callback.data[7:]
if cat=="NEW":
await
callback.message.edit_text("📂 Yangi
kategoriya nomini kiriting:")
await callback.answer(); return
await state.update_data(category=cat)
await
state.set_state(AdminStates.waiting_explana
tion)
await callback.message.edit_text("💡
Tavsif:\n<i>'-' = kerak
emas</i>",parse_mode="HTML")
await callback.answer()
@dp.message(AdminStates.waiting_category)
async def get_new_category(message:
types.Message, state: FSMContext):
db.add_category(message.text.strip())
await
state.update_data(category=message.text.str
ip())
await
state.set_state(AdminStates.waiting_explana
tion)
await message.answer("💡 Tavsif:\n<i>'-
' = kerak emas</i>",parse_mode="HTML")
@dp.message(AdminStates.waiting_explanation
)
async def get_explanation(message:
types.Message, state: FSMContext):
explanation="" if
message.text.strip()=="-" else
message.text.strip()
await
state.update_data(explanation=explanation)
await
state.set_state(AdminStates.waiting_image)
await message.answer("🖼 Rasm
(ixtiyoriy):\n• Rasm yuklang • URL
yuboring • <b>'-'</b> = kerak
emas",parse_mode="HTML")
@dp.message(AdminStates.waiting_image)
async def get_image(message: types.Message,
state: FSMContext):
image_id=""
if message.text and
message.text.strip()=="-": image_id=""
elif message.photo:
image_id=message.photo[-1].file_id
elif message.text and
message.text.startswith("http"):
image_id=message.text.strip()
await
state.update_data(image_id=image_id)
data=await state.get_data()
diff_icon=DIFFICULTY_ICONS.get(data.get("di
fficulty","orta"),"🟡")
options_display=""
if data["q_type"]=="test":
opts=data.get("options","").split("|")
options_display="\n"+"\n".join([f"
{chr(65+i)}. {opt}" for i,opt in
enumerate(opts)])
options_display+=f"\n✅ To'g'ri:
{data['correct'].upper()}"
elif data["q_type"] not in IELTS_TYPES:
options_display=f"\n✅ Javob:
{data['correct']}"
tl_info=f"\n⏰
{data.get('time_limit','')}" if
data.get("time_limit") else ""
confirm=(f"📋 <b>Tekshiring:
</b>\n\nTur: {data['q_type'].upper()}\n"
f"❓ {data['q_text'][:200]}
{options_display}\n"
f"💰 {data['coins']}
coin\n{diff_icon}
{DIFFICULTY_NAMES.get(data.get('difficulty'
,'orta'))}\n"
f"📂 {data.get('category','')}
{tl_info}\n🖼 {'Ha' if image_id else
'Yoq'}\n\nSaqlash?")
kb=InlineKeyboardMarkup(inline_keyboard=
[[InlineKeyboardButton(text="✅
Saqlash",callback_data="save_question"),Inl
ineKeyboardButton(text="❌
Bekor",callback_data="cancel_question")]])
await
message.answer(confirm,parse_mode="HTML",re
ply_markup=kb)
@dp.callback_query(F.data=="save_question")
async def save_question_cb(callback:
types.CallbackQuery, state: FSMContext):
data=await state.get_data()
db.add_question(text=data["q_text"],q_type=
data["q_type"],options=data.get("options","
"),
correct=data.get("correct",""),coins=data["
coins"],category=data.get("category","Umumi
y"),
difficulty=data.get("difficulty","orta"),ex
planation=data.get("explanation",""),
image_id=data.get("image_id",""),time_limit
=data.get("time_limit",""))
await state.clear()
await callback.message.edit_text("✅
<b>Savol saqlandi!</b>",parse_mode="HTML")
await callback.message.answer("⚙ Admin
Panel",reply_markup=admin_menu())
await callback.answer()
@dp.callback_query(F.data=="cancel_question
")
async def cancel_question(callback:
types.CallbackQuery, state: FSMContext):
await state.clear()
await callback.message.edit_text("❌
Bekor qilindi.")
await callback.message.answer("⚙ Admin
Panel",reply_markup=admin_menu())
await callback.answer()
@dp.message(F.text=="📋 Savollar ro'yxati")
async def list_questions(message:
types.Message):
if not is_admin(message.from_user.id):
return
questions=db.get_all_questions()
if not questions:
await message.answer("😔 Savollar
yo'q."); return
text=f"📋 <b>Jami: {len(questions)}
ta</b>\n\n"
for q in questions[:20]:
q_id,q_text,q_type,_,_,coins,category,diffi
culty=q
short=q_text[:30]+"..." if
len(q_text)>30 else q_text
text+=f"#{q_id}
{DIFFICULTY_ICONS.get(difficulty,'🟡')}
[{category}] {short} ({coins}💰)\n"
if len(questions)>20: text+=f"\n...va
yana {len(questions)-20} ta"
await
message.answer(text,parse_mode="HTML")
@dp.message(F.text=="🗑 Savol o'chirish")
async def delete_prompt(message:
types.Message):
if not is_admin(message.from_user.id):
return
await message.answer("🗑 O'chiriladigan
savol ID sini yuboring:")
@dp.message(F.text=="✏ Savol tahrirlash")
async def edit_prompt(message:
types.Message):
if not is_admin(message.from_user.id):
return
await message.answer("✏
Tahrirlanadigan savol ID sini yuboring:")
@dp.message(F.text.regexp(r'^\d+$'))
async def handle_id_input(message:
types.Message, state: FSMContext):
if not is_admin(message.from_user.id):
return
q_id=int(message.text);
q=db.get_question_by_id(q_id)
if not q:
await message.answer(f"❌ #{q_id}
topilmadi."); return
_,q_text,q_type,options,correct,coins,cat,d
iff,explanation,image_id,tl=q
short=q_text[:60]+"..." if
len(q_text)>60 else q_text
kb=InlineKeyboardMarkup(inline_keyboard=[
[InlineKeyboardButton(text="🗑
O'chirish",callback_data=f"del_{q_id}"),Inl
ineKeyboardButton(text="❌
Bekor",callback_data="del_cancel")],
[InlineKeyboardButton(text="✏
Savol matnini
o'zgartir",callback_data=f"edf_{q_id}_text"
)],
[InlineKeyboardButton(text="📋
Variantlarni
o'zgartir",callback_data=f"edf_{q_id}_optio
ns")],
[InlineKeyboardButton(text="✅
To'g'ri javobni
o'zgartir",callback_data=f"edf_{q_id}_corre
ct")],
[InlineKeyboardButton(text="💰
Coinni
o'zgartir",callback_data=f"edf_{q_id}_coins
")],
[InlineKeyboardButton(text="💡
Tavsifni
o'zgartir",callback_data=f"edf_{q_id}_expla
nation")],
[InlineKeyboardButton(text="📂
Kategoriyani
o'zgartir",callback_data=f"edf_{q_id}_categ
ory")],
[InlineKeyboardButton(text="⏰ Vaqt
limitini
o'zgartir",callback_data=f"edf_{q_id}_time_
limit")],
[InlineKeyboardButton(text="🖼
Rasmni
o'zgartir",callback_data=f"edf_{q_id}_image
_id")]])
await message.answer(f"#{q_id}
{DIFFICULTY_ICONS.get(diff,'🟡')}
[{cat}]\n❓ {short}\n💰 {coins} coin\nTur:
{q_type}",reply_markup=kb)
@dp.callback_query(F.data.startswith("edf_"
))
async def edit_field(callback:
types.CallbackQuery, state: FSMContext):
parts=callback.data.split("_");
q_id,field=int(parts[1]),parts[2]
await
state.update_data(edit_q_id=q_id,edit_field
=field)
await
state.set_state(AdminStates.editing_field)
q=db.get_question_by_id(q_id)
cv={}
if q:
_,q_text,q_type,options,correct,coins,cat,d
iff,explanation,image_id,tl=q
cv=
{"text":q_text,"options":options.replace("|
","\n") if options else
"","correct":correct,
"coins":str(coins),"explanation":explanatio
n or "Yo'q","category":cat,
"time_limit":tl or
"Yo'q","image_id":"Bor ✅" if image_id else
"Yo'q"}
current=cv.get(field,"")
prompts={"text":f"✏ Hozirgi:\n<i>
{current[:200]}</i>\n\nYangi matnni
kiriting:",
"options":f"📋 Hozirgi:\n<i>
{current}</i>\n\nYangi variantlarni
kiriting:",
"correct":f"✅ Hozirgi: <i>
{current}</i>\n\nYangi javobni kiriting:",
"coins":f"💰 Hozirgi: <i>
{current}</i>\n\nYangi miqdorni kiriting:",
"explanation":f"💡 Hozirgi:
<i>{current}</i>\n\nYangi tavsifni kiriting
('-' = o'chirish):",
"category":f"📂 Hozirgi: <i>
{current}</i>\n\nYangi kategoriyani
kiriting:",
"time_limit":f"⏰ Hozirgi: <i>
{current}</i>\n\nYangi vaqtni kiriting ('-'
= o'chirish):",
"image_id":f"🖼 Rasm: <i>
{current}</i>\n\nRasm yuboring yoki URL
kiriting ('-' = o'chirish):"}
await
callback.message.answer(prompts.get(field,"
Yangi qiymat:"),parse_mode="HTML")
await callback.answer()
@dp.message(AdminStates.editing_field)
async def save_edit(message: types.Message,
state: FSMContext):
data=await state.get_data();
q_id,field=data["edit_q_id"],data["edit_fie
ld"]
if field=="image_id":
value=message.photo[-1].file_id if
message.photo else ("" if
message.text.strip()=="-" else
message.text.strip())
elif field=="coins":
if not
message.text.replace(".","").isdigit():
await message.answer("⚠ Faqat
raqam!"); return
value=float(message.text)
elif field=="options":
value="|".join([o.strip() for o in
message.text.split("\n") if o.strip()])
elif field in
("explanation","time_limit"):
value="" if
message.text.strip()=="-" else
message.text.strip()
else: value=message.text.strip()
db.update_question_field(q_id,field,value)
await state.clear()
await message.answer(f"✅ #{q_id}
yangilandi!",reply_markup=admin_menu())
@dp.callback_query(F.data.startswith("del_"
))
async def confirm_delete(callback:
types.CallbackQuery):
if callback.data=="del_cancel":
await
callback.message.edit_text("❌ Bekor
qilindi."); await callback.answer(); return
q_id=int(callback.data.split("_")[1]);
db.delete_question(q_id)
await callback.message.edit_text(f"✅ #
{q_id} o'chirildi!")
await callback.answer()
@dp.message(F.text=="👥 Foydalanuvchilar")
async def list_users(message:
types.Message):
if not is_admin(message.from_user.id):
return
await message.answer(f"👥
<b>Foydalanuvchilar</b>\n\nJami: <b>
{db.get_total_users()}</b>\nFaol: <b>
{db.get_active_users()}
</b>",parse_mode="HTML")
@dp.message(F.text=="📊 Statistika")
async def show_stats(message:
types.Message):
if not is_admin(message.from_user.id):
return
s=db.get_stats()
await message.answer(f"📊
<b>Statistika</b>\n\n👥 {s['users']}\n❓
{s['questions']}\n📝 {s['answers']}\n✅
{s['correct']}\n🎯
{s['accuracy']}%",parse_mode="HTML")
@dp.message(F.text=="📢 Xabar yuborish")
async def broadcast_start(message:
types.Message, state: FSMContext):
if not is_admin(message.from_user.id):
return
await
state.set_state(AdminStates.broadcast_text)
await message.answer("📢 Xabar matnini
kiriting:\n<i>/cancel — bekor
qilish</i>",parse_mode="HTML")
@dp.message(AdminStates.broadcast_text)
async def broadcast_get_text(message:
types.Message, state: FSMContext):
await
state.update_data(broadcast_text=message.te
xt)
await
state.set_state(AdminStates.broadcast_image
)
await message.answer("🖼 Rasm
(ixtiyoriy):\nRasm yuklang yoki <b>'-'</b>
yozing",parse_mode="HTML")
@dp.message(AdminStates.broadcast_image)
async def broadcast_send(message:
types.Message, state: FSMContext):
data=await state.get_data();
text=data["broadcast_text"]
image_id=message.photo[-1].file_id if
message.photo else ("" if message.text and
message.text.strip()=="-" else
(message.text or ""))
await
state.update_data(broadcast_image=image_id)
kb=InlineKeyboardMarkup(inline_keyboard=
[[InlineKeyboardButton(text="📢
Yuborish",callback_data="confirm_broadcast"
),InlineKeyboardButton(text="❌
Bekor",callback_data="cancel_broadcast")]])
await message.answer(f"📢 <b>Xabar:
</b>\n\n{text}\n\n🖼 {'Ha' if image_id else
'Yoq'}\n\nYuborilsinmi?",parse_mode="HTML",
reply_markup=kb)
@dp.callback_query(F.data=="confirm_broadca
st")
async def do_broadcast(callback:
types.CallbackQuery, state: FSMContext):
data=await state.get_data();
text,image_id=data["broadcast_text"],data.g
et("broadcast_image","")
users=db.get_all_user_ids()
await callback.message.edit_text(f"📢
Yuborilmoqda... ({len(users)} ta)")
success=failed=0
for uid in users:
try:
if image_id: await
bot.send_photo(uid,photo=image_id,caption=t
ext,parse_mode="HTML")
else: await
bot.send_message(uid,text,parse_mode="HTML"
)
success+=1
except: failed+=1
await asyncio.sleep(0.05)
await state.clear()
await callback.message.answer(f"✅
{success} ta\n❌ {failed}
ta",reply_markup=admin_menu())
await callback.answer()
@dp.callback_query(F.data=="cancel_broadcas
t")
async def cancel_broadcast(callback:
types.CallbackQuery, state: FSMContext):
await state.clear()
await callback.message.edit_text("❌
Bekor.")
await callback.message.answer("⚙ Admin
Panel",reply_markup=admin_menu())
await callback.answer()
async def main():
await
dp.start_polling(bot,allowed_updates=dp.res
olve_used_update_types())
if __name__=="__main__":
asyncio.run(main())
