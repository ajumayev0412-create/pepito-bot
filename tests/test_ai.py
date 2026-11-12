import json
import os
import threading
import unittest
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

from app import ai, main as M
from app.config import Config
from app.model import Lead, assign_customers

TZ = ZoneInfo("Asia/Tashkent")
CALLS = []


class Stub(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n))
        CALLS.append((self.headers.get("x-api-key"), body))
        if self.headers.get("x-api-key") != "KEY":
            self.send_response(401); self.end_headers(); return
        out = json.dumps({"content": [{"type": "text", "text": "**Xulosa:**\n• yaxshi\n• yomon"}]}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)


class FakeTG:
    def __init__(self, updates):
        self._u, self.sent = updates, []

    def updates(self, offset=None):
        return self._u

    def send(self, text, chat_ids=None):
        self.sent.append((chat_ids, text))


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 8799), Stub)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    def cfg(self, key="KEY"):
        os.environ.update(ANTHROPIC_API_KEY=key, AI_API_URL="http://127.0.0.1:8799/v1/messages",
                          TG_CHAT_ID="111", NOW_OVERRIDE="2026-11-09T14:00:00", STATE_FILE="/tmp/st_ai.json")
        return Config()

    def test_parse(self):
        self.assertEqual(M.parse_command("/savol@hisobotpepito_bot  qaysi sotuvchi sust?"), ("/savol", "qaysi sotuvchi sust?"))
        self.assertEqual(M.parse_command("/BUGUN"), ("/bugun", ""))
        self.assertEqual(M.parse_command(""), ("", ""))

    def test_summarize_cleans_markdown_and_strips_html(self):
        cfg = self.cfg()
        CALLS.clear()
        out = ai.summarize(cfg, '📊 <b>Hisobot</b> <a href="http://x/leads/detail/1">#1</a> telefon yo\'q', "kun")
        self.assertNotIn("**", out)
        sent = CALLS[0][1]
        self.assertIn("claude", sent["model"])
        self.assertNotIn("<b>", sent["messages"][0]["content"])
        self.assertNotIn("<a ", sent["messages"][0]["content"])

    def test_with_ai_falls_back_when_key_wrong(self):
        cfg = self.cfg(key="BAD")
        self.assertEqual(M.with_ai(cfg, "HISOBOT", "kun"), "HISOBOT")   # AI xato bo'lsa ham hisobot ketadi

    def test_with_ai_disabled_without_key(self):
        cfg = self.cfg(key="")
        self.assertEqual(M.with_ai(cfg, "HISOBOT", "kun"), "HISOBOT")

    def test_daily_limit(self):
        cfg = self.cfg(); cfg.ai_daily_limit = 2
        st = {}
        now = cfg.now()
        self.assertTrue(M.ai_allowed(cfg, st, now)); self.assertTrue(M.ai_allowed(cfg, st, now))
        self.assertFalse(M.ai_allowed(cfg, st, now))
        self.assertTrue(M.ai_allowed(cfg, st, now + timedelta(days=1)))

    def test_poll_savol(self):
        cfg = self.cfg()
        if os.path.exists(cfg.state_file):
            os.remove(cfg.state_file)
        d0 = cfg.now() - timedelta(hours=2)
        leads = assign_customers([Lead(1, "x", d0, None, 0, 1, "Yangi lid", "Ali", [], {"p:1"})])
        M.load_history = lambda c, a: leads
        ups = [
            {"update_id": 1, "message": {"chat": {"id": 111}, "text": "/savol@bot qaysi sotuvchi sust?"}},
            {"update_id": 2, "message": {"chat": {"id": 999}, "text": "/savol hammasini ayt"}},   # begona chat
            {"update_id": 3, "message": {"chat": {"id": 111}, "text": "/savol"}},                   # savolsiz
        ]
        tg = FakeTG(ups)
        CALLS.clear()
        M.run_poll(cfg, None, tg)
        self.assertEqual(len(CALLS), 1)                      # faqat bitta AI so'rovi
        self.assertEqual(len(tg.sent), 2)                    # begona chatga javob yo'q
        self.assertTrue(tg.sent[0][1].startswith("🤖"))
        self.assertIn("Savolni buyruqdan keyin", tg.sent[1][1])
        ctx = CALLS[0][1]["messages"][0]["content"]
        self.assertIn("SAVOL: qaysi sotuvchi sust?", ctx)
        self.assertNotIn("+998", ctx)


if __name__ == "__main__":
    unittest.main()
