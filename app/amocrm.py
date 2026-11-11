"""amoCRM API v4 mijozi (faqat o'qish)."""
import time
import requests


class AmoError(Exception):
    pass


class Amo:
    def __init__(self, base_url, token, pause=0.2):
        if not base_url or not token:
            raise AmoError("AMO_BASE_URL va AMO_TOKEN kiritilmagan.")
        self.base = base_url.rstrip("/")
        self.token = token
        self.pause = pause  # amoCRM: sekundiga 7 ta so'rovdan oshmasin
        self._new_session()

    def _new_session(self):
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Connection": "close",  # eski (uzilgan) ulanishlar muammosini oldini oladi
        })

    def get(self, path, params=None, retries=8):
        url = path if path.startswith("http") else self.base + path
        for i in range(retries):
            time.sleep(self.pause)
            try:
                r = self.s.get(url, params=params, timeout=60)
            except requests.exceptions.RequestException:
                # tarmoq uzilishi: yangi ulanish ochib, biroz kutib qayta urinamiz
                self._new_session()
                time.sleep(3 * (i + 1))
                continue
            if r.status_code == 204:
                return None
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 * (i + 1))
                continue
            if r.status_code == 401:
                raise AmoError("401: token noto'g'ri yoki muddati tugagan. Yangi token yarating.")
            if r.status_code == 403:
                raise AmoError("403: bu token uchun ruxsat yo'q (integratsiya huquqlarini tekshiring).")
            if r.status_code >= 400:
                raise AmoError(f"{r.status_code}: {r.text[:300]}")
            return r.json()
        raise AmoError("amoCRM javob bermadi (qayta urinishlar tugadi).")

    def pages(self, path, key, params=None):
        params = dict(params or {})
        params.setdefault("limit", 250)
        page = 1
        while True:
            params["page"] = page
            data = self.get(path, params)
            if not data:
                return
            items = (data.get("_embedded") or {}).get(key) or []
            if not items:
                return
            yield from items
            if "next" not in (data.get("_links") or {}):
                return
            page += 1

    def pipelines(self):
        data = self.get("/api/v4/leads/pipelines") or {}
        return (data.get("_embedded") or {}).get("pipelines") or []

    def users(self):
        return {u["id"]: u.get("name", str(u["id"])) for u in self.pages("/api/v4/users", "users")}

    def contacts(self, ids):
        out = {}
        ids = list(ids)
        for i in range(0, len(ids), 100):
            batch = ids[i:i + 100]
            for c in self.pages("/api/v4/contacts", "contacts", {"filter[id][]": batch}):
                out[c["id"]] = c
        return out
