"""Hisob-kitoblar. Mantiq siz bilan birga tekshirilgan tahlilga mos."""
import re
from collections import Counter, defaultdict

SRC_ORDER = ["Telegram / boshqa", "Kiruvchi qo'ng'iroq", "Chiquvchi qo'ng'iroq", "Propushenniy", "Forma"]


def source(l):
    t = l.name or ""
    tags = " ".join(l.tags)
    if t.startswith("Facebook") or re.search(r"fb\d{6,}", tags) or "target" in tags.lower():
        return "Forma"
    if t.startswith("Входящий") or "Входящий" in tags:
        return "Kiruvchi qo'ng'iroq"
    if "Исходящий" in tags:
        return "Chiquvchi qo'ng'iroq"
    if t.startswith("Пропущенный") or "Пропущенный" in tags or "Клиент не ответил" in tags:
        return "Propushenniy"
    return "Telegram / boshqa"


def form_key(l):
    """Lead forma bo'lsa, formaning nomi (teg + Facebook forma raqami oxiri)."""
    tags = ", ".join(l.tags)
    m = re.search(r"fb\d{6,}", tags)
    if m:
        brand = next((t for t in l.tags if t in ("babystep", "kabrito", "target", "friso")), "nomsiz")
        return f"{brand} …{m.group(0)[-4:]}"
    if any(t.startswith("импорт_") for t in l.tags):
        return "Import ro'yxat"
    if (l.name or "").startswith("Facebook") or (l.name or "").startswith("f:"):
        return "Boshqa forma"
    return None


def is_delivered(l, cfg):
    return l.status.lower() in cfg.delivered


def is_lost(l):
    return l.status.lower().startswith("sotib olmadi") or l.status_id == 143


def ltype(l):
    if not l.cid:
        return "unknown"
    return "new" if l.rank == 0 else "repeat"


def money(l, cfg):
    return l.price if l.price <= cfg.price_cap else 0


def summary(leads, cfg, start, end):
    created = [l for l in leads if start <= l.created < end]
    delivered = [l for l in leads if is_delivered(l, cfg) and l.closed and start <= l.closed < end]
    revenue = sum(money(l, cfg) for l in delivered)
    big = [l for l in delivered if l.price > cfg.price_cap]
    c_types = Counter(ltype(l) for l in created)
    d_types = Counter(ltype(l) for l in delivered)
    cust = {l.cid for l in delivered if l.cid}

    c_src = Counter(source(l) for l in created)
    d_src = Counter(source(l) for l in delivered)
    created_delivered = sum(1 for l in created if is_delivered(l, cfg))

    sellers = defaultdict(lambda: {"created": 0, "delivered": 0, "revenue": 0.0})
    for l in created:
        sellers[l.resp]["created"] += 1
    for l in delivered:
        sellers[l.resp]["delivered"] += 1
        sellers[l.resp]["revenue"] += money(l, cfg)

    forms = defaultdict(lambda: {"leads": 0, "delivered": 0, "untouched": 0})
    for l in created:
        k = form_key(l)
        if k:
            forms[k]["leads"] += 1
            forms[k]["delivered"] += 1 if is_delivered(l, cfg) else 0
            forms[k]["untouched"] += 1 if l.status.lower() == cfg.new_stage else 0

    return {
        "created": len(created),
        "created_new": c_types["new"], "created_repeat": c_types["repeat"], "created_unknown": c_types["unknown"],
        "created_repeat_24h": sum(1 for l in created if ltype(l) == "repeat" and l.gap_h is not None and l.gap_h <= 24),
        "delivered": len(delivered), "revenue": revenue,
        "avg_check": revenue / (len(delivered) - len(big)) if len(delivered) - len(big) else 0,
        "unique_customers": len(cust),
        "delivered_nocontact": sum(1 for l in delivered if not l.cid),
        "delivered_new": d_types["new"], "delivered_repeat": d_types["repeat"], "delivered_unknown": d_types["unknown"],
        "created_delivered": created_delivered,
        "conv_created": created_delivered / len(created) if created else 0,
        "c_src": dict(c_src), "d_src": dict(d_src),
        "sellers": dict(sellers), "forms": dict(forms),
        "big_deals": len(big),
    }


def untouched(leads, cfg, now, stages=None):
    """Belgilangan bosqichdagi (odatda 'Yangi lid') leadlar, eng eskisidan boshlab."""
    stages = stages or [cfg.new_stage]
    rows = [l for l in leads if l.status.lower() in stages]
    rows.sort(key=lambda l: l.created)
    return rows


def age_minutes(l, now):
    return (now - l.created).total_seconds() / 60
