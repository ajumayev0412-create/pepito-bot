import requests


def split_text(t, n=3900):
    out, cur = [], ""
    for line in t.split("\n"):
        if len(cur) + len(line) + 1 > n and cur:
            out.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        out.append(cur)
    return out


class Telegram:
    def __init__(self, token, api="https://api.telegram.org", chat_ids=None):
        if not token:
            raise RuntimeError("TG_BOT_TOKEN kiritilmagan.")
        self.url = f"{api.rstrip('/')}/bot{token}"
        self.chat_ids = chat_ids or []

    def _call(self, method, **params):
        r = requests.post(f"{self.url}/{method}", json=params, timeout=40)
        data = r.json() if r.content else {}
        if not data.get("ok"):
            raise RuntimeError(f"Telegram xatosi: {data.get('description') or r.status_code}")
        return data["result"]

    def send(self, text, chat_ids=None):
        targets = chat_ids or self.chat_ids
        if not targets:
            raise RuntimeError("TG_CHAT_ID kiritilmagan.")
        for chat in targets:
            for chunk in split_text(text):
                self._call("sendMessage", chat_id=chat, text=chunk, parse_mode="HTML",
                           disable_web_page_preview=True)

    def updates(self, offset=None):
        p = {"timeout": 0, "allowed_updates": ["message"]}
        if offset:
            p["offset"] = offset
        return self._call("getUpdates", **p)
