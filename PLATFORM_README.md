# BilimChallenge — To'liq Platforma (Bot + Backend + Websayt)

Bu paket 3 ta alohida qismdan iborat:

```
bot.py, database.py, config.py     ← Telegram bot (o'zgarishsiz, faqat WEBSITE_URL qo'shildi)
backend/                            ← Flask API server (Alwaysdata'ga qo'yiladi)
platform-frontend/                  ← Websayt (GitHub Pages'ga qo'yiladi)
```

**Muhim tushuncha:** Bot, backend va websayt — 3 ta alohida joyda ishlaydi, lekin **bitta PostgreSQL bazasini** ishlatadi. Shuning uchun botda ko'rgan coiningiz saytda ham aynan shu bo'ladi.

---

## 1-QADAM: Backend (Alwaysdata)

### 1.1. Fayllarni yuklash
`backend/` papkasidagi barcha fayllarni Alwaysdata hisobingizga (masalan SSH yoki FTP orqali) `~/bilimchallenge-api/` papkasiga yuklang:
- `app.py`
- `database.py`
- `config.py`
- `wsgi.py`
- `requirements.txt`

### 1.2. Kutubxonalarni o'rnatish
Alwaysdata SSH konsolida:
```bash
cd ~/bilimchallenge-api
pip install --user -r requirements.txt
```

### 1.3. `config.py` ni sozlash
Fayl ichida 2 narsani tekshiring:
```python
BOT_TOKEN = "..."   # bot.py dagi BILAN AYNAN BIR XIL bo'lishi SHART
GEMINI_API_KEY = "..."  # Google AI Studio'dan olingan kalit
```

### 1.4. Alwaysdata'da "Site" yaratish
1. Alwaysdata panelida **Sites** → **Add a site**
2. Type: **Python**
3. Command: `~/bilimchallenge-api/wsgi.py`
4. Domenni belgilang (masalan `bilimchallenge-api.alwaysdata.net`)

### 1.5. Tekshirish
Brauzerda oching:
```
https://sizning-hisobingiz.alwaysdata.net/api/health
```
Agar `{"status": "ok", ...}` ko'rinsa — backend ishlayapti.

---

## 2-QADAM: Telegram Login Widget'ni yoqish

Bot orqali saytga kirish uchun **BotFather**'da domenni ro'yxatdan o'tkazish kerak:

1. Telegram'da **@BotFather** ga o'ting
2. `/mybots` → botingizni tanlang
3. **Bot Settings** → **Domain**
4. Frontend joylashadigan domenni kiriting (2-qadamdan keyin aniq bo'ladi, masalan `username.github.io`)

**Eslatma:** Bu qadamni GitHub Pages sayti tayyor bo'lgandan keyin, uning aniq manzili bilan bajaring.

---

## 3-QADAM: Frontend (GitHub Pages)

### 3.1. Sozlamalarni to'ldirish
`platform-frontend/assets/config.js` faylini oching:
```js
const BC_CONFIG = {
  API_BASE: "https://sizning-hisobingiz.alwaysdata.net",  // 1-qadamdagi backend manzili
  BOT_USERNAME: "BilimChallenge_bot",                      // @ belgisisiz bot username
};
```

### 3.2. GitHub'ga yuklash
1. Yangi repository yarating (masalan `bilimchallenge-web`)
2. `platform-frontend/` ichidagi BARCHA fayllarni (papka strukturasi bilan) yuklang:
   ```
   index.html
   profile.html
   rating.html
   shop.html
   search.html
   games.html
   assets/
     style.css
     config.js
     api.js
   games/
     memory.html
     reflex.html
     logic.html
     wordchain.html
   ```
3. **Settings** → **Pages** → Source: `main` branch → Save
4. Bir necha daqiqadan keyin sayt tayyor: `https://username.github.io/bilimchallenge-web/`

### 3.3. Domenni BotFather'ga qaytish
2-qadamga qaytib, aniq domeningizni (`username.github.io`) BotFather'ga kiriting.

**Muhim:** Telegram Login Widget faqat **https** va **BotFather'da ro'yxatdan o'tgan domenda** ishlaydi. `localhost` yoki ro'yxatdan o'tmagan domenda login tugmasi ko'rinmaydi yoki xato beradi.

---

## 4-QADAM: Botni yangilash

`config.py` (bot uchun, backend uchun emas — ular alohida fayllar) dagi:
```python
WEBSITE_URL = "https://username.github.io/bilimchallenge-web"
```
ni haqiqiy GitHub Pages manzilingiz bilan almashtiring, botni qayta ishga tushiring.

---

## Nima ishlaydi?

| Sahifa | Funksiya |
|---|---|
| `index.html` | Bosh sahifa — kategoriya tanlash, savolga javob berish (bot bilan bir xil savollar/coinlar) |
| `profile.html` | Profil — coin, streak, liga, duel statistikasi, kiyilgan bezaklar |
| `rating.html` | Global reyting, top-3 podium |
| `shop.html` | Magazin — ramka/nishon/fon effekti sotib olish va kiyish |
| `search.html` | Foydalanuvchi qidirish (ism/username) |
| `games.html` | 4 ta mini o'yin markazi |
| `games/memory.html` | Juftlik topish (xotira) |
| `games/reflex.html` | Reaksiya sinovi (tezlik) |
| `games/logic.html` | Raqam ketma-ketligi (mantiq) |
| `games/wordchain.html` | So'z zanjiri (lug'at) |

## Mini o'yin coin tizimi

- Har o'yin **kunlik 40 coin** limitiga ega (barcha o'yinlar birgalikda)
- Coin miqdori natija sifatiga bog'liq (tezroq/aniqroq = ko'proq coin)
- Server tomonida imzo (`signature`) orqali tekshiriladi — brauzerdan to'g'ridan-to'g'ri "coin bering" so'rovi yuborib bo'lmaydi

## IELTS AI zaiflik tahlili

Backend'da `/api/ielts/weakness-check` va `/api/ielts/weekly-pattern` endpointlari bor — bu Gemini orqali foydalanuvchining IELTS javobidagi eng katta xatoni topib, "bunday qilsangiz yaxshi bo'lardi" tarzida maslahat beradi. **Eslatma:** hozircha bu endpointlar botning IELTS oqimiga ulanmagan — agar botda ham shu tahlilni ko'rsatishni xohlasangiz, alohida so'rang, bot.py ga integratsiya qilib beraman.

## Muammolarni bartaraf etish

**"Telegram Login" tugmasi ko'rinmayapti** → BotFather'da domen ro'yxatdan o'tmagan yoki https emas.

**API so'rovlari 401 qaytaryapti** → `BOT_TOKEN` bot.py va backend/config.py da bir xil emas.

**CORS xatosi konsolda** → `backend/config.py` dagi `FRONTEND_ORIGIN` ni aniq domeningizga o'rnating (masalan `"https://username.github.io"`), `"*"` o'rniga.

**Coin berilmayapti** → `/api/health` orqali backend PostgreSQL'ga ulanganini tekshiring.
