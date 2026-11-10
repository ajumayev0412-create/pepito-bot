import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import Config
from app.model import Lead, assign_customers, contact_keys, norm_phone
from app.metrics import summary, source

TZ = ZoneInfo("Asia/Tashkent")


def L(i, created, keys, status="Yangi lid", closed=None, price=0, name="Сделка", tags=(), resp="A"):
    return Lead(id=i, name=name, created=created, closed=closed, price=price, status_id=1, status=status,
                resp=resp, tags=list(tags), keys=set(keys))


class T(unittest.TestCase):
    def test_phone(self):
        self.assertEqual(norm_phone("+998 90 123-45-67"), "901234567")
        self.assertEqual(norm_phone("901234567"), "901234567")
        self.assertIsNone(norm_phone("123"))

    def test_contact_keys(self):
        c = {"custom_fields_values": [
            {"field_code": "PHONE", "values": [{"value": "+998901234567"}]},
            {"field_name": "Telegram ID", "values": [{"value": "123456.0"}]},
            {"field_name": "Telegram username", "values": [{"value": "@Ali"}]}]}
        self.assertEqual(contact_keys(c), {"p:901234567", "t:123456", "u:ali"})

    def test_new_vs_repeat(self):
        cfg = Config()
        d0 = datetime(2026, 11, 1, 10, tzinfo=TZ)
        leads = [
            L(1, d0, {"p:1"}),
            L(2, d0 + timedelta(hours=2), {"p:1", "t:9"}),              # shu mijoz: qayta, 24 soat ichida
            L(3, d0 + timedelta(days=3), {"t:9"}, status="Yetkazib berildi",
              closed=d0 + timedelta(days=3, hours=1), price=400000),    # t:9 orqali bog'lanadi: qayta
            L(4, d0, {"p:2"}, status="Yetkazib berildi", closed=d0 + timedelta(hours=1), price=300000),
            L(5, d0, set()),                                             # aloqa yo'q
        ]
        assign_customers(leads)
        s = summary(leads, cfg, d0 - timedelta(days=1), d0 + timedelta(days=10))
        self.assertEqual((s["created_new"], s["created_repeat"], s["created_unknown"]), (2, 2, 1))
        self.assertEqual(s["created_repeat_24h"], 1)
        self.assertEqual((s["delivered"], s["delivered_new"], s["delivered_repeat"]), (2, 1, 1))
        self.assertEqual(s["revenue"], 700000)
        self.assertEqual(s["unique_customers"], 2)

    def test_source(self):
        mk = lambda name, tags=(): L(1, datetime(2026, 11, 1, tzinfo=TZ), set(), name=name, tags=tags)
        self.assertEqual(source(mk("Facebook №1")), "Forma")
        self.assertEqual(source(mk("Входящий 1 (998)")), "Kiruvchi qo'ng'iroq")
        self.assertEqual(source(mk("Сделка с X")), "Telegram / boshqa")

    def test_price_cap(self):
        cfg = Config()
        d0 = datetime(2026, 11, 1, 10, tzinfo=TZ)
        leads = [L(1, d0, {"p:1"}, status="Yetkazib berildi", closed=d0, price=265_000_000),
                 L(2, d0, {"p:2"}, status="Yetkazib berildi", closed=d0, price=400_000)]
        assign_customers(leads)
        s = summary(leads, cfg, d0 - timedelta(days=1), d0 + timedelta(days=1))
        self.assertEqual(s["revenue"], 400000)
        self.assertEqual(s["big_deals"], 1)


if __name__ == "__main__":
    unittest.main()
