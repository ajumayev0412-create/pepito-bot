"""Telegram uchun matnlar (o'zbekcha). Faqat umumiy sonlar: mijoz ismi/telefoni yuborilmaydi."""
import html
from datetime import timedelta
from .metrics import SRC_ORDER, summary, untouched, age_minutes

MONTHS = ["", "yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust",
          "sentabr", "oktabr", "noyabr", "dekabr"]


def n(x):
    return f"{int(round(x)):,}".replace(",", " ")


def som(x):
    return f"{n(x)} so'm"


def pct(a, b):
    return f"{a / b * 100:.1f}%" if b else "-"


def delta(new, old):
    if not old:
        return "-"
    d = (new - old) / old * 100
    return f"{d:+.1f}%"


def e(s):
    return html.escape(str(s), quote=False)


def date_s(d):
    return f"{d.day}-{MONTHS[d.month]} {d.year}"


def _block(s, title_created="Yangi leadlar"):
    L = []
    L.append(f"🆕 {title_created}: <b>{n(s['created'])}</b>")
    L.append(f"   yangi murojaat {n(s['created_new'])} · qayta murojaat {n(s['created_repeat'])}"
             f" · aniqlanmagan {n(s['created_unknown'])}")
    L.append(f"✅ Yetkazilgan: <b>{n(s['delivered'])}</b> ta · <b>{som(s['revenue'])}</b>")
    L.append(f"   o'rtacha chek: {som(s['avg_check'])}")
    L.append(f"   noyob mijozlar: {n(s['unique_customers'])}"
             + (f" (aloqa ma'lumotisiz: {n(s['delivered_nocontact'])})" if s["delivered_nocontact"] else ""))
    L.append(f"   yangi murojaatdan {n(s['delivered_new'])} · qayta murojaatdan {n(s['delivered_repeat'])}"
             f" · aniqlanmagan {n(s['delivered_unknown'])}")
    if s["big_deals"]:
        L.append(f"⚠️ {s['big_deals']} ta sdelkada summa juda katta, tushumga qo'shilmadi (tekshiring).")
    return L


def _sources(s):
    L = ["", "<b>Manbalar</b> (yangi leadlar → yetkazilgan)"]
    for k in SRC_ORDER:
        c, d = s["c_src"].get(k, 0), s["d_src"].get(k, 0)
        if c or d:
            L.append(f"• {k}: {n(c)} → {n(d)}")
    return L


def _sellers(s):
    L = ["", "<b>Sotuvchilar</b> (yangi leadlar / yetkazilgan / summa)"]
    rows = sorted(s["sellers"].items(), key=lambda kv: (-kv[1]["delivered"], -kv[1]["created"]))
    for name, v in rows:
        L.append(f"• {e(name)}: {n(v['created'])} / {n(v['delivered'])} / {v['revenue'] / 1e6:.1f} mln")
    return L


def _forms(s):
    if not s["forms"]:
        return []
    L = ["", "<b>Lead formalar</b> (leadlar / yetkazilgan / tegilmagan)"]
    for k, v in sorted(s["forms"].items(), key=lambda kv: -kv[1]["leads"]):
        L.append(f"• {e(k)}: {n(v['leads'])} / {n(v['delivered'])} / {n(v['untouched'])}")
    return L


def untouched_lines(leads, cfg, now):
    rows = untouched(leads, cfg, now)
    if not rows:
        return ["", "✅ «Yangi lid» bosqichida tegilmagan lead yo'q."]
    by = {}
    for l in rows:
        by.setdefault(l.resp, []).append(l)
    oldest_days = (now - rows[0].created).days
    L = ["", f"⚠️ <b>«Yangi lid»da tegilmagan: {n(len(rows))} ta</b> (eng eskisi {oldest_days} kun oldin)"]
    for name, ls in sorted(by.items(), key=lambda kv: -len(kv[1])):
        L.append(f"• {e(name)}: {n(len(ls))}")
    return L


def daily_text(cfg, leads, start, end, now, title):
    s = summary(leads, cfg, start, end)
    L = [f"📊 <b>{title}</b>"] + _block(s) + _sources(s) + _sellers(s) + _forms(s)
    ms = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    m = summary(leads, cfg, ms, end)
    L += ["", f"<b>Oy boshidan</b> ({ms.day}–{(end - timedelta(seconds=1)).day} {MONTHS[ms.month]})"]
    L += _block(m)
    L += untouched_lines(leads, cfg, now)
    return "\n".join(L)


def month_text(cfg, leads, now):
    ms = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    s = summary(leads, cfg, ms, now + timedelta(seconds=1))
    L = [f"📅 <b>{MONTHS[now.month].capitalize()} {now.year} — {now.day}-sanagacha</b>"] + _block(s)
    L += _sources(s) + _sellers(s) + _forms(s)
    return "\n".join(L)


def week_text(cfg, leads, start, end, title):
    s = summary(leads, cfg, start, end)
    p = summary(leads, cfg, start - timedelta(days=7), start)
    L = [f"🗓 <b>{title}</b>", f"<i>{date_s(start)} – {date_s(end - timedelta(seconds=1))}</i>", ""]
    L.append("<b>Oldingi hafta bilan solishtirma</b>")
    L.append(f"• Yangi leadlar: {n(s['created'])} ({delta(s['created'], p['created'])})")
    L.append(f"• Yetkazilgan: {n(s['delivered'])} ({delta(s['delivered'], p['delivered'])})")
    L.append(f"• Summa: {som(s['revenue'])} ({delta(s['revenue'], p['revenue'])})")
    L.append(f"• O'rtacha chek: {som(s['avg_check'])} ({delta(s['avg_check'], p['avg_check'])})")
    L.append(f"• Noyob mijozlar: {n(s['unique_customers'])} ({delta(s['unique_customers'], p['unique_customers'])})")
    L.append(f"• Yangi murojaat: {n(s['created_new'])} → yetkazilgan {n(s['delivered_new'])}")
    L.append(f"• Qayta murojaat: {n(s['created_repeat'])} → yetkazilgan {n(s['delivered_repeat'])}")
    L.append(f"• Yaratilganlardan yetkazilgani: {pct(s['created_delivered'], s['created'])} (ochiq leadlar hali kiradi)")
    L += _sources(s) + _sellers(s) + _forms(s)
    return "\n".join(L)


def alert_text(items, cfg, now, base, level):
    """items: [(lead)]; level 1 = birinchi ogohlantirish, 2 = kuchaytirilgan."""
    head = (f"⏰ <b>Javobsiz leadlar ({cfg.alert_min}+ daqiqa)</b>" if level == 1
            else f"🔴 <b>{cfg.alert_esc}+ daqiqa o'tdi, hali tegilmagan</b>")
    by = {}
    for l in items:
        by.setdefault(l.resp, []).append(l)
    L = [head]
    for name, ls in sorted(by.items(), key=lambda kv: -len(kv[1])):
        oldest = max(age_minutes(l, now) for l in ls)
        links = ", ".join(f'<a href="{base}/leads/detail/{l.id}">#{l.id}</a>' for l in ls[:5])
        more = f" va yana {len(ls) - 5} ta" if len(ls) > 5 else ""
        L.append(f"• {e(name)}: {len(ls)} ta (eng eskisi {int(oldest)} daq) — {links}{more}")
    return "\n".join(L)
