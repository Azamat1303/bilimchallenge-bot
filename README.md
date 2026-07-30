# BilimChallenge Bot

## O'rnatish

```bash
pip install -r requirements.txt
python bot.py
```

## Fayllar
- `bot.py` — asosiy bot kodi
- `database.py` — PostgreSQL baza
- `config.py` — token va sozlamalar

## Sozlash (config.py)
- `BOT_TOKEN` — BotFather dan olingan token
- `ADMIN_IDS` — admin user ID
- `GROQ_API_KEY` — Groq API kaliti

## Guruh buyruqlari
- `/savol` — savol yuborish (admin)
- `/skip` — savolni o'tkazish (admin)
- `/reyting` — guruh reytingi
- `/stat` — statistika
- `/sozboshi` — so'z o'yini boshlash
- `/sozstop` — so'z o'yinini to'xtatish
- `/sozreyting` — so'z o'yini reytingi

## Admin buyruqlari
- `/sozqosh` — so'z qo'shish
- `/sozlar` — so'zlar ro'yxati
- `/sozochir [id]` — so'z o'chirish
