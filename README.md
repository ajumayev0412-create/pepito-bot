# Pepito: amoCRM → Telegram hisobot va ogohlantirish boti

Bepul GitHub Actions'da ishlaydi. Server kerak emas. Kod amoCRM'dan **faqat o'qiydi** (hech narsani o'zgartirmaydi),
Telegramga esa **faqat umumiy sonlar** yuboradi (mijoz ismi va telefoni yuborilmaydi).

## Nima qiladi

| Nima | Qachon | Mazmuni |
|---|---|---|
| Kunlik hisobot | har kuni 00:15 (Toshkent), o'tgan kun uchun | yangi leadlar (yangi/qayta murojaat), yetkazilgan, summa, o'rtacha chek, noyob mijozlar, manbalar, sotuvchilar, lead formalar, oy boshidan, tegilmagan leadlar |
| Haftalik hisobot | dushanba 09:00 | o'tgan hafta va undan oldingi hafta bilan solishtirma |
| Ogohlantirish | har ~10 daqiqada, 09:00–24:00 | «Yangi lid» yoki «Propusheniy» bosqichida 15 daqiqa tegilmagan lead haqida; 60 daqiqadan keyin ikkinchi (qizil) ogohlantirish |
| Bot buyruqlari | har ~10 daqiqada tekshiriladi | `/bugun`, `/hafta`, `/oy`, `/tegilmagan`, `/yordam` |

Hisob qoidalari (siz bilan tekshirilgan):
- **Yetkazilgan** = «Yetkazib berildi» bosqichiga o'tgan sdelka, **yopilgan sana** bo'yicha.
- **Noyob mijoz** = bir xil telefon yoki Telegram ID/username bo'yicha birlashtirilgan mijoz.
- **Yangi murojaat** = mijozning shu leaddan oldin hech qachon leadi bo'lmagan. **Qayta murojaat** = oldin ham leadi bo'lgan.
- **Manba**: lead sarlavhasi va teglaridan aniqlanadi (Forma / Kiruvchi / Chiquvchi / Propushenniy / Telegram-boshqa).
- Summasi 50 000 000 so'mdan katta sdelka tushumga qo'shilmaydi va hisobotda ogohlantiriladi (xato kiritilgan bo'lishi mumkin). `PRICE_CAP` bilan o'zgartiriladi.

---

## 1-qadam. Uchta kalit tayyorlash

### A) Telegram bot
1. Telegramda **@BotFather** ga yozing → `/newbot` → bot nomini kiriting.
2. U bergan uzun kod = **TG_BOT_TOKEN**. Uni hech kimga bermang.
3. Hisobotlar kelishi kerak bo'lgan joyni tanlang: o'zingiz yoki yopiq guruh (ROP + sotuvchilar). Guruh bo'lsa, botni guruhga qo'shing.
4. Botga `/start` yozing (guruhda bo'lsa, guruhga istalgan xabar yozing).
5. Chat ID ni 4-qadamdagi `chatid` buyrug'i bilan topamiz.

### B) amoCRM token
1. amoCRM'ga **administrator** sifatida kiring → **Sozlamalar → Integratsiyalar** (Интеграции).
2. **Integratsiya yaratish** (Создать интеграцию) → **Yopiq (private) integratsiya**. Nomi: `Telegram hisobot`.
3. Ruxsatlarda faqat **o'qish** (leadlar, kontaktlar, foydalanuvchilar) yetarli.
4. **Kalitlar va ruxsatlar** (Ключи и доступы) bo'limidan **uzoq muddatli token** (Долгосрочный токен) yarating va nusxalang = **AMO_TOKEN**.
   (Tugma nomlari amoCRM versiyasiga qarab biroz farq qilishi mumkin.)
5. Akkaunt manzili = **AMO_BASE_URL**, masalan `https://pepito.amocrm.ru` (oxirida `/` siz).

---

## 2-qadam. GitHub'ga joylash
1. https://github.com da bepul akkaunt oching.
2. **New repository** → nomi `pepito-bot` → **Public** tanlang → Create.
   *Nega Public:* ochiq repozitoriyda Actions daqiqalari cheklanmagan. Kodda kalit ham, ma'lumot ham yo'q, kalitlar faqat Secrets'da turadi.
   (Agar Private qilsangiz, `.github/workflows/alerts.yml` ichida `*/10` ni `*/30` ga o'zgartiring, aks holda bepul 2000 daqiqa tugab qoladi.)
3. **Add file → Upload files** → shu papkadagi **hamma fayl va papkalarni** (`app`, `tests`, `.github`, `README.md`, `requirements.txt`, `.gitignore`) sudrab tashlang → Commit.
   - `.github` papkasi ko'rinmasa (Mac): Finder'da `Cmd + Shift + .` bosing.
   - Baribir yuklanmasa: GitHub'da **Add file → Create new file**, nomiga `.github/workflows/reports.yml` deb yozib, ichiga fayl matnini qo'ying; xuddi shunday `alerts.yml` uchun.

## 3-qadam. Kalitlarni Secrets'ga kiritish
Repozitoriyda **Settings → Secrets and variables → Actions → New repository secret**. To'rtta secret yarating:

| Nomi | Qiymati |
|---|---|
| `AMO_BASE_URL` | `https://pepito.amocrm.ru` |
| `AMO_TOKEN` | amoCRM tokeni |
| `TG_BOT_TOKEN` | BotFather tokeni |
| `TG_CHAT_ID` | keyingi qadamda topiladi (hozircha `0` yozib turing) |

## 4-qadam. Chat ID topish va birinchi sinov
1. **Actions** bo'limi → chap tomonda **Hisobotlar** → **Run workflow** → buyruq: **chatid** → Run.
   (Birinchi marta Actions'ni yoqish tugmasini bosish kerak bo'lishi mumkin.)
2. Ish tugagach, uni oching → ichida `CHAT ID: 123456789` yozuvi bo'ladi. Shuni nusxalab, `TG_CHAT_ID` secretiga yozing (bir nechta bo'lsa, vergul bilan: `123,-100456`).
3. Yana **Run workflow** → buyruq: **test**. Telegramga xabar kelishi kerak:
   - ✅ amoCRM bilan ulanish ishlayapti
   - Yetkazilgan / Yangi lid / Propushenniy bosqichlari topildi (✔️) yoki yo'q (❌)
   - Namunadagi kontaktlardan nechtasida telefon va Telegram ID topilgani
4. Hammasi ✔️ bo'lsa, **today** buyrug'ini ishga tushirib, bugungi hisobotni ko'ring.
5. Ogohlantirish va buyruqlar o'zi ishlab ketadi (har 10 daqiqada). Birinchi ishga tushishda bot «Ogohlantirish tizimi yoqildi» deb yozadi, eski leadlar uchun alohida xabar bermaydi.

## Sozlamalar (ixtiyoriy)
**Settings → Secrets and variables → Actions → Variables** bo'limida. Bo'sh qoldirsangiz, standart qiymat ishlaydi.

| Nomi | Standart | Ma'nosi |
|---|---|---|
| `PIPELINE_NAME` | `Sotuv bo'limi` | voronka nomi |
| `DELIVERED_STAGE` | `Yetkazib berildi` | yetkazilgan bosqich nomi |
| `NEW_STAGE` | `Yangi lid` | yangi lid bosqichi |
| `MISSED_STAGE` | `Propusheniy` | propushenniy bosqichi |
| `ALERT_MINUTES` | `15` | necha daqiqadan keyin birinchi ogohlantirish |
| `ALERT_ESCALATE_MINUTES` | `60` | ikkinchi (qizil) ogohlantirish |
| `WORK_FROM_HOUR` / `WORK_TO_HOUR` | `9` / `24` | ogohlantirish yuboriladigan soatlar (Toshkent) |
| `HISTORY_FROM` | `2026-08-14` | tarix boshlanishi (qayta murojaatni aniqlash uchun) |
| `PRICE_CAP` | `50000000` | bundan katta summa tushumga qo'shilmaydi |

## Muammolar
| Xabar / holat | Sabab va yechim |
|---|---|
| `401: token noto'g'ri` | `AMO_TOKEN` xato yoki muddati tugagan. Yangi token yarating, Secrets'ni yangilang. |
| `voronkasi topilmadi` | `PIPELINE_NAME` ni xabardagi mavjud voronka nomiga o'zgartiring. |
| `❌ ... bosqichi topilmadi` | Variables'da `DELIVERED_STAGE` / `NEW_STAGE` / `MISSED_STAGE` ni voronkadagi aniq nomga to'g'rilang (xabarda ro'yxat bor). |
| «telefon/Telegram ID o'qilmadi» | Kontakt maydonlari nomi boshqacha. Xabardagi nomlarni menga yuboring, kodda moslashtiriladi. |
| Telegram `chat not found` | `TG_CHAT_ID` xato yoki bot guruhda yo'q / botga `/start` bosilmagan. |
| Hisobot kelmadi | Actions → ishga tushirish tarixini oching, qizil (xato) ishni bosib, loglarni o'qing. |

## Cheklovlar (bilib qo'ying)
- GitHub rejalashtirilgan ishlarni ba'zan **5–15 daqiqa kechiktiradi**. Ogohlantirish va bot buyruqlariga javob aniq 10 daqiqada emas, taxminan shu atrofda keladi. Bot buyruqlari bir zumda javob bermaydi.
- Repozitoriyda **60 kun hech qanday o'zgarish bo'lmasa**, GitHub rejalashtirilgan ishlarni o'chirib qo'yadi. Ikki oyda bir marta README'ga kichik o'zgarish kiritib saqlang yoki Actions'da ishlarni qayta yoqing.
- Kunlik/haftalik hisobotda butun tarix (14-avgustdan) yuklanadi, shuning uchun ish 3–5 daqiqa davom etishi mumkin.
- «Yaratilganlardan yetkazilgani» ko'rsatkichi ochiq leadlar yopilguncha taxminiy bo'ladi.
- Faqat Telegram ID si bor mijozni boshqa sdelkadagi telefon raqami bilan bog'lab bo'lmaydi (CRMda ikkalasi ham yozilgan bo'lsa, bog'lanadi).

## Xavfsizlik
- Kalitlarni **faqat** GitHub Secrets'ga yozing. Chatga, kodga, faylga yozmang. `.env` fayli `.gitignore`da, GitHub'ga yuklanmaydi.
- Kalit begonaga ko'rinib qolsa: amoCRM'da tokenni o'chirib yangisini yarating, BotFather'da `/revoke` qiling.
- Bot faqat `TG_CHAT_ID` dagi chatlarga javob beradi, boshqalarni e'tiborsiz qoldiradi.

## Mahalliy sinov (ixtiyoriy)
```
pip install -r requirements.txt
python -m unittest tests.test_metrics -v
```
