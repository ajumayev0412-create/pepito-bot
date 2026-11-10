"""Leadlarni oddiy ko'rinishga keltirish, mijozlarni (telefon/Telegram bo'yicha) birlashtirish."""
import re
from dataclasses import dataclass, field
from datetime import datetime


def norm_phone(v):
    d = re.sub(r"\D", "", str(v or ""))
    return d[-9:] if len(d) >= 9 else None


def norm_tg(v):
    d = re.sub(r"\D", "", str(v or "").strip().split(".")[0])
    return d or None


def norm_user(v):
    s = str(v or "").strip().lower().lstrip("@")
    return s or None


def contact_keys(contact):
    """Kontaktdan telefon / Telegram ID / username kalitlarini ajratadi."""
    keys = set()
    for f in (contact or {}).get("custom_fields_values") or []:
        code = (f.get("field_code") or "").upper()
        name = (f.get("field_name") or "").lower()
        vals = [v.get("value") for v in f.get("values") or []]
        if code == "PHONE" or "телефон" in name or "telefon" in name or "phone" in name:
            for v in vals:
                p = norm_phone(v)
                if p:
                    keys.add("p:" + p)
        elif "telegram" in name and "id" in name:
            for v in vals:
                t = norm_tg(v)
                if t:
                    keys.add("t:" + t)
        elif "telegram" in name and "user" in name:
            for v in vals:
                u = norm_user(v)
                if u:
                    keys.add("u:" + u)
    return keys


@dataclass
class Lead:
    id: int
    name: str
    created: datetime
    closed: datetime | None
    price: float
    status_id: int
    status: str
    resp: str
    tags: list
    keys: set = field(default_factory=set)
    cid: str | None = None      # mijoz identifikatori (None = aloqa ma'lumoti yo'q)
    rank: int | None = None     # mijozning nechanchi leadi (0 = birinchi)
    gap_h: float | None = None  # oldingi leaddan necha soat o'tgan


def build_leads(raw, contacts, statuses, users, cfg):
    out = []
    for r in raw:
        emb = r.get("_embedded") or {}
        tags = [t.get("name", "") for t in emb.get("tags") or []]
        cons = emb.get("contacts") or []
        main = next((c for c in cons if c.get("is_main")), cons[0] if cons else None)
        keys = contact_keys(contacts.get(main["id"])) if main and main.get("id") in contacts else set()
        status = statuses.get(r.get("status_id"), str(r.get("status_id")))
        closed_ts = r.get("closed_at") or None
        if closed_ts is None and status.lower() in cfg.delivered:
            closed_ts = r.get("updated_at")  # yopilish sanasi yo'q bo'lsa
        out.append(Lead(
            id=r["id"], name=r.get("name") or "",
            created=datetime.fromtimestamp(r["created_at"], cfg.tz),
            closed=datetime.fromtimestamp(closed_ts, cfg.tz) if closed_ts else None,
            price=float(r.get("price") or 0),
            status_id=r.get("status_id"), status=status,
            resp=users.get(r.get("responsible_user_id"), "Noma'lum"),
            tags=tags, keys=keys,
        ))
    return out


def assign_customers(leads):
    """Bitta telefon yoki Telegram ID/username'ga ega leadlar = bitta mijoz."""
    parent = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for l in leads:
        ks = sorted(l.keys)
        for k in ks:
            parent.setdefault(k, k)
        for k in ks[1:]:
            a, b = find(ks[0]), find(k)
            if a != b:
                parent[b] = a
    groups = {}
    for l in leads:
        l.cid = find(sorted(l.keys)[0]) if l.keys else None
        if l.cid:
            groups.setdefault(l.cid, []).append(l)
    for g in groups.values():
        g.sort(key=lambda x: (x.created, x.id))
        prev = None
        for i, l in enumerate(g):
            l.rank = i
            l.gap_h = None if prev is None else (l.created - prev).total_seconds() / 3600
            prev = l.created
    return leads
