# 🧠 BilimChallenge Bot — O'rnatish Qo'llanmasi

## 📁 Fayllar
```
bilimchallenge/
├── bot.py           ← Asosiy bot kodi
├── database.py      ← Ma'lumotlar bazasi
├── config.py        ← Token va Admin ID
└── requirements.txt ← Kutubxonalar
```

---

## 🚀 1-QADAM — Python o'rnatish

Kompyuteringizda Python 3.10+ bo'lishi kerak.
Tekshirish: `python --version`

---

## 🤖 2-QADAM — Token olish

1. Telegramda **@BotFather** ga yozing
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting: `BilimChallenge`
4. Username kiriting: `bilimchallenge_bot` (yoki boshqa)
5. **Token** olasiz — uni nusxalab oling

---

## 🆔 3-QADAM — Admin ID olish

1. Telegramda **@userinfobot** ga `/start` yuboring
2. Sizning **ID** raqamingizni ko'rsatadi
3. Yoki **@getmyid_bot** ishlatishingiz mumkin

---

## ⚙️ 4-QADAM — config.py ni to'ldirish

`config.py` faylini oching va o'zgartiring:

```python
BOT_TOKEN = "1234567890:AAF..."    # ← Token shu yerga
ADMIN_IDS = [123456789]            # ← ID shu yerga
```

---

## 💻 5-QADAM — Kutubxonalarni o'rnatish

Terminal (cmd) da papkaga kiring va yozing:

```bash
pip install -r requirements.txt
```

---

## ▶️ 6-QADAM — Botni ishga tushirish

```bash
python bot.py
```

Agar hamma narsa to'g'ri bo'lsa, terminal da quyidagini ko'rasiz:
```
INFO: Bot started!
```

---

## 📱 7-QADAM — Botni tekshirish

1. Telegram da o'z botingizga `/start` yuboring
2. ⚙️ Admin Panel tugmasi paydo bo'lishi kerak
3. Savol qo'shing va test qiling!

---

## 🏠 Doimiy ishlatish (VPS/Server)

Agar bot doim ishlab turishi kerak bo'lsa, **VPS** kerak.
Masalan: **TimeWeb**, **Beget**, yoki **DigitalOcean**

VPS da:
```bash
# Yuklab olish
git clone ... yoki fayllarni yuklang

# O'rnatish
pip install -r requirements.txt

# Fonda ishlatish
nohup python bot.py &
```

---

## ❓ Muammolar

| Muammo | Yechim |
|--------|--------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` qayta ishlatish |
| `Unauthorized` | Token noto'g'ri, config.py ni tekshiring |
| Admin panel ko'rinmaydi | ID noto'g'ri, @userinfobot dan tekshiring |
| Bot javob bermaydi | Terminal da xato xabar bormi? |
