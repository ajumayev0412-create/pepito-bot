"""Ishga tushirish:  python -m app.main <buyruq>
Buyruqlar: test | chatid | daily | weekly | today | week | month | alerts | poll
"""
import json
import sys
from datetime import datetime, timedelta

from .config import Config
from .amocrm import Amo, AmoError
from .model import build_leads, assign_customers, contact_keys
from .metrics import age_minutes
from . import reports
from .telegram import Telegram

HELP = ("🤖 <b>Pepito hisobot boti</b>\n"
        "/bugun — bugungi natija\n"
        "/hafta — oxirgi 7 kun (oldingi 7 kun bilan solishtirma)\n"
        "/oy — shu oy boshidan\n"
        "/tegilmagan — «Yangi lid»da tegilmagan leadlar\n\n"
        "<i>Buyruqqa javob 10 daqiqagacha kechikishi mumkin.</i>")


# ---------- yordamchi ----------
def pipeline_info(cfg, amo):
    pls = amo.pipelines()
    if not pls:
        raise AmoError("amoCRMda voronka topilmadi.")
    pick = next((p for p in pls if p.get("name", "").lower() == cfg.pipeline.lower()), None)
    if pick is None and len(pls) == 1:
        pick = pls[0]
    if pick is None:
        names = ", ".join(f"«{p.get('name')}»" for p in pls)
        raise AmoError(f"«{cfg.pipeline}» voronkasi topilmadi. Mavjud voronkalar: {names}. "
                       f"PIPELINE_NAME sozlamasini to'g'rilang.")
    statuses = {s["id"]: s["name"] for s in (pick.get("_embedded") or {}).get("statuses") or []}
    return pick["id"], statuses


def load_history(cfg, amo):
    pid, statuses = pipeline_info(cfg, amo)
    users = amo.users()
    since = int(datetime.fromisoformat(cfg.history_from).replace(tzinfo=cfg.tz).timestamp())
    params = {"with": "contacts", "filter[created_at][from]": since}
    raw = [r for r in amo.pages("/api/v4/leads", "leads", params) if r.get("pipeline_id") == pid]
    cids = set()
    for r in raw:
        cons = (r.get("_embedded") or {}).get("contacts") or []
        main = next((c for c in cons if c.get("is_main")), cons[0] if cons else None)
        if main:
            cids.add(main["id"])
    contacts = amo.contacts(cids)
    leads = assign_customers(build_leads(raw, contacts, statuses, users, cfg))
    print(f"Yuklandi: {len(leads)} ta lead, {len(contacts)} ta kontakt")
    return leads


def stage_leads(cfg, amo, stage_names):
    pid, statuses = pipeline_info(cfg, amo)
    ids = [sid for sid, nm in statuses.items() if nm.lower() in stage_names]
    if not ids:
        raise AmoError(f"Bosqichlar topilmadi: {stage_names}. NEW_STAGE / MISSED_STAGE nomlarini tekshiring.")
    params = {}
    for i, sid in enumerate(ids):
        params[f"filter[statuses][{i}][pipeline_id]"] = pid
        params[f"filter[statuses][{i}][status_id]"] = sid
    raw = list(amo.pages("/api/v4/leads", "leads", params))
    return build_leads(raw, {}, statuses, amo.users(), cfg)


def load_state(cfg):
    try:
        with open(cfg.state_file, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(cfg, state):
    with open(cfg.state_file, "w", encoding="utf-8") as f:
        json.dump(state, f)


def midnight(d):
    return d.replace(hour=0, minute=0, second=0, microsecond=0)


# ---------- hisobotlar ----------
def text_today(cfg, leads, now):
    return reports.daily_text(cfg, leads, midnight(now), now + timedelta(seconds=1), now,
                              f"Bugun, soat {now:%H:%M} gacha")


def text_daily(cfg, leads, now):
    if now.hour < 6:  # tungi ishga tushirish: tugagan kunni hisoblaymiz
        end = midnight(now)
        start = end - timedelta(days=1)
    else:
        start, end = midnight(now), now + timedelta(seconds=1)
    return reports.daily_text(cfg, leads, start, end, now, f"Kunlik hisobot — {reports.date_s(start)}")


def text_weekly(cfg, leads, now):
    this_monday = midnight(now) - timedelta(days=now.weekday())
    return reports.week_text(cfg, leads, this_monday - timedelta(days=7), this_monday, "Haftalik hisobot")


def text_week_rolling(cfg, leads, now):
    start = midnight(now) - timedelta(days=6)
    return reports.week_text(cfg, leads, start, now + timedelta(seconds=1), "Oxirgi 7 kun")


def text_untouched(cfg, amo, now):
    leads = stage_leads(cfg, amo, [cfg.new_stage])
    return "\n".join(["📋 <b>Tegilmagan leadlar</b>"] + reports.untouched_lines(leads, cfg, now))


# ---------- ogohlantirish ----------
def run_alerts(cfg, amo, tg):
    now = cfg.now()
    if not (cfg.work_from <= now.hour < cfg.work_to):
        print("Ish vaqtidan tashqari, ogohlantirish yuborilmadi.")
        return
    state = load_state(cfg)
    leads = stage_leads(cfg, amo, [cfg.new_stage, cfg.missed_stage])
    cand = []
    for l in leads:
        a = age_minutes(l, now)
        if cfg.alert_min <= a <= cfg.alert_max_age_h * 60:
            cand.append((l, 2 if a >= cfg.alert_esc else 1))
    alerted = state.get("alerted", {})
    if "init" not in state:  # birinchi ishga tushish: eski leadlar bilan spam qilmaymiz
        state["init"] = True
        state["alerted"] = {str(l.id): lvl for l, lvl in cand}
        save_state(cfg, state)
        rows = [l for l in leads if l.status.lower() == cfg.new_stage]
        tg.send("🔔 <b>Ogohlantirish tizimi yoqildi.</b> Bundan keyin yangi leadlar "
                f"{cfg.alert_min} daqiqa javobsiz tursa, shu yerga xabar keladi.\n"
                f"Hozir «Yangi lid»da {len(rows)} ta lead turibdi.")
        return
    send1, send2, new_alerted = [], [], {}
    for l, lvl in cand:
        prev = alerted.get(str(l.id), 0)
        new_alerted[str(l.id)] = max(prev, lvl)
        if prev < lvl:
            (send2 if lvl == 2 else send1).append(l)
    if send1:
        tg.send(reports.alert_text(send1, cfg, now, cfg.amo_base, 1))
    if send2:
        tg.send(reports.alert_text(send2, cfg, now, cfg.amo_base, 2))
    state["alerted"] = new_alerted  # yopilgan/o'tib ketganlar tozalanadi
    save_state(cfg, state)
    print(f"Ogohlantirish: {len(send1)} + {len(send2)} ta lead")


# ---------- bot buyruqlari ----------
def run_poll(cfg, amo, tg):
    state = load_state(cfg)
    ups = tg.updates(state.get("tg_offset"))
    cache = {}

    def history():
        if "h" not in cache:
            cache["h"] = load_history(cfg, amo)
        return cache["h"]

    for u in ups:
        state["tg_offset"] = u["update_id"] + 1
        msg = u.get("message") or {}
        chat = str(msg.get("chat", {}).get("id", ""))
        if chat not in cfg.chat_ids:
            continue
        cmd = (msg.get("text") or "").strip().lower().split()[0].split("@")[0] if msg.get("text") else ""
        now = cfg.now()
        try:
            if cmd in ("/start", "/yordam", "/help"):
                out = HELP
            elif cmd == "/bugun":
                out = text_today(cfg, history(), now)
            elif cmd == "/hafta":
                out = text_week_rolling(cfg, history(), now)
            elif cmd == "/oy":
                out = reports.month_text(cfg, history(), now)
            elif cmd == "/tegilmagan":
                out = text_untouched(cfg, amo, now)
            else:
                continue
        except Exception as ex:  # noqa
            out = f"⚠️ Xato: {reports.e(ex)}"
        tg.send(out, [chat])
    save_state(cfg, state)
    print(f"Buyruqlar qayta ishlandi: {len(ups)} ta yangilanish")


# ---------- test ----------
def run_test(cfg, amo, tg):
    pid, statuses = pipeline_info(cfg, amo)
    names = {v.lower() for v in statuses.values()}
    lines = ["✅ amoCRM bilan ulanish ishlayapti.", f"Voronka: «{cfg.pipeline}», bosqichlar: {len(statuses)} ta"]
    for label, nm in [("Yetkazilgan", cfg.delivered[0] if cfg.delivered else ""), ("Yangi lid", cfg.new_stage),
                      ("Propushenniy", cfg.missed_stage)]:
        ok = nm in names
        lines.append(f"{'✔️' if ok else '❌'} {label} bosqichi: «{nm}»" + ("" if ok else " — voronkada topilmadi!"))
    data = amo.get("/api/v4/leads", {"limit": 50, "with": "contacts", "order[created_at]": "desc"}) or {}
    sample = (data.get("_embedded") or {}).get("leads") or []
    cids = set()
    for r in sample:
        cons = (r.get("_embedded") or {}).get("contacts") or []
        main = next((c for c in cons if c.get("is_main")), cons[0] if cons else None)
        if main:
            cids.add(main["id"])
    contacts = amo.contacts(cids) if cids else {}
    ph = tgid = tgu = 0
    field_names = set()
    for c in contacts.values():
        ks = contact_keys(c)
        ph += any(k.startswith("p:") for k in ks)
        tgid += any(k.startswith("t:") for k in ks)
        tgu += any(k.startswith("u:") for k in ks)
        for f in c.get("custom_fields_values") or []:
            field_names.add(str(f.get("field_name")))
    lines.append(f"Namuna: {len(sample)} ta lead, {len(contacts)} ta kontakt. Topildi: telefon {ph}, "
                 f"Telegram ID {tgid}, Telegram username {tgu}")
    if contacts and not (ph or tgid):
        lines.append("⚠️ Kontaktlardan telefon/Telegram ID o'qilmadi. Kontakt maydonlari nomi: "
                     + ", ".join(sorted(field_names)) + ". Shu nomlarni menga yuboring, moslashtirib beraman.")
    if any("❌" in l for l in lines):
        lines.append("Bosqich nomlari mos kelmasa, GitHub'dagi Variables bo'limida DELIVERED_STAGE, "
                     "NEW_STAGE, MISSED_STAGE ni to'g'rilang. Voronkadagi bosqichlar: "
                     + "; ".join(statuses.values()))
    tg.send("\n".join(reports.e(x) for x in lines))
    print("\n".join(lines))


def run_chatid(cfg):
    tg = Telegram(cfg.tg_token, cfg.tg_api)
    ups = tg.updates()
    seen = {}
    for u in ups:
        c = (u.get("message") or {}).get("chat") or {}
        if c.get("id") is not None:
            seen[c["id"]] = c.get("title") or c.get("username") or c.get("first_name") or ""
    if not seen:
        print("Hech narsa topilmadi. Botga /start yozing (yoki guruhga qo'shib, xabar yozing), keyin qayta ishga tushiring.")
    for cid, nm in seen.items():
        print(f"CHAT ID: {cid}   ({nm})")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    cfg = Config()
    if cmd == "chatid":
        run_chatid(cfg)
        return 0
    tg = Telegram(cfg.tg_token, cfg.tg_api, cfg.chat_ids)
    try:
        amo = Amo(cfg.amo_base, cfg.amo_token)
        now = cfg.now()
        if cmd == "test":
            run_test(cfg, amo, tg)
        elif cmd == "daily":
            tg.send(text_daily(cfg, load_history(cfg, amo), now))
        elif cmd == "weekly":
            tg.send(text_weekly(cfg, load_history(cfg, amo), now))
        elif cmd == "today":
            tg.send(text_today(cfg, load_history(cfg, amo), now))
        elif cmd == "week":
            tg.send(text_week_rolling(cfg, load_history(cfg, amo), now))
        elif cmd == "month":
            tg.send(reports.month_text(cfg, load_history(cfg, amo), now))
        elif cmd == "alerts":
            run_alerts(cfg, amo, tg)
        elif cmd == "poll":
            run_poll(cfg, amo, tg)
        else:
            print("Noma'lum buyruq:", cmd)
            return 2
    except Exception as ex:
        print("XATO:", ex)
        if cmd in ("test", "daily", "weekly", "today", "week", "month"):
            try:
                tg.send(f"⚠️ <b>Xato ({cmd}):</b> {reports.e(ex)}")
            except Exception:
                pass
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
