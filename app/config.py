"""Sozlamalar. Hammasi muhit o'zgaruvchilaridan (GitHub Secrets / Variables) olinadi."""
import os
from datetime import datetime
from zoneinfo import ZoneInfo


def _e(name, default=""):
    v = os.environ.get(name, "")
    return v.strip() if v and v.strip() else default


class Config:
    def __init__(self):
        self.amo_base = _e("AMO_BASE_URL").rstrip("/")
        self.amo_token = _e("AMO_TOKEN")
        self.tg_token = _e("TG_BOT_TOKEN")
        self.tg_api = _e("TG_API_BASE", "https://api.telegram.org")
        self.chat_ids = [c.strip() for c in _e("TG_CHAT_ID").split(",") if c.strip()]

        # CRMdagi nomlar (kichik-katta harf farqi yo'q). Bir nechta bo'lsa ";" bilan ajrating.
        self.pipeline = _e("PIPELINE_NAME", "Sotuv bo'limi")
        self.delivered = [s.strip().lower() for s in _e("DELIVERED_STAGE", "Yetkazib berildi").split(";") if s.strip()]
        self.new_stage = _e("NEW_STAGE", "Yangi lid").lower()
        self.missed_stage = _e("MISSED_STAGE", "Propusheniy").lower()

        self.history_from = _e("HISTORY_FROM", "2026-08-14")  # CRM ishga tushgan sana
        self.tz = ZoneInfo(_e("TIMEZONE", "Asia/Tashkent"))

        self.alert_min = int(_e("ALERT_MINUTES", "15"))
        self.alert_esc = int(_e("ALERT_ESCALATE_MINUTES", "60"))
        self.alert_max_age_h = int(_e("ALERT_MAX_AGE_HOURS", "24"))
        self.work_from = int(_e("WORK_FROM_HOUR", "9"))
        self.work_to = int(_e("WORK_TO_HOUR", "24"))

        # Bundan katta summali sdelka tushumga qo'shilmaydi va hisobotda ogohlantiriladi.
        self.price_cap = int(_e("PRICE_CAP", "50000000"))
        self.state_file = _e("STATE_FILE", "state.json")

        # Sun'iy intellekt (ixtiyoriy). Kalit bo'lmasa, AI qismi o'chiq turadi.
        # Ikki variant: Anthropic (Claude, pullik) yoki Google Gemini (bepul tarif mavjud).
        self.ai_key = _e("ANTHROPIC_API_KEY")
        self.gemini_key = _e("GEMINI_API_KEY")
        self.ai_provider = "anthropic" if self.ai_key else ("gemini" if self.gemini_key else "")
        default_model = "claude-sonnet-5-5" if self.ai_provider == "anthropic" else "gemini-2.5-flash"
        self.ai_model = _e("AI_MODEL", default_model)
        self.ai_url = _e("AI_API_URL", "")  # faqat sinov uchun
        self.ai_daily_limit = int(_e("AI_DAILY_LIMIT", "30"))  # kuniga /savol soni

    def now(self):
        ov = _e("NOW_OVERRIDE")  # faqat sinov uchun
        if ov:
            return datetime.fromisoformat(ov).replace(tzinfo=self.tz)
        return datetime.now(self.tz)
