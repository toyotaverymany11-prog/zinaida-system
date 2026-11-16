import copy
from datetime import datetime, timezone
import unittest

from production.core import ProductionError
from production.speech import prepare_batch


class SpeechPlanning(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 16, tzinfo=timezone.utc)
        self.spec = {"schema_version": 1, "model": "s2.1-pro-free",
                     "quote": {"model": "s2.1-pro-free", "unit": "million_utf8_bytes", "usd_per_unit": "0",
                               "checked_at": "2026-11-15T00:00:00Z", "valid_until": "2026-11-17T00:00:00Z",
                               "source": "https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits.md"},
                     "voices": {"narrator": {"version": "v1", "provider_voice_id": "a" * 32,
                                             "sample_sha256": "b" * 64}},
                     "lines": [{"id": "line1", "voice": "narrator", "spoken_text": "Привет, мир!",
                                "directed_text": "[warm] Привет, мир!"},
                               {"id": "line2", "voice": "narrator", "spoken_text": "До завтра.",
                                "directed_text": "До завтра."}]}

    def test_counts_russian_utf8_and_tags_not_characters(self):
        self.spec["model"] = self.spec["quote"]["model"] = "s2.1-pro"
        self.spec["quote"]["usd_per_unit"] = "15"
        r = prepare_batch(self.spec, now=self.now)
        self.assertEqual(r["takes"][0]["utf8_bytes"], len("[warm] Привет, мир!".encode()))
        self.assertEqual(r["total_utf8_bytes"], 46)
        self.assertEqual(r["estimated_usd"], "0.00069")
        self.assertEqual(r["external_requests_sent"], 0)

    def test_unknown_model_cannot_silently_fall_back_to_paid(self):
        self.spec["model"] = "s2.1-pro-fre"
        with self.assertRaisesRegex(ProductionError, "Unknown speech model"):
            prepare_batch(self.spec, now=self.now)

    def test_delivery_edit_only_invalidates_its_own_take(self):
        a = prepare_batch(self.spec, now=self.now)
        self.spec["lines"][0]["directed_text"] = "[sarcastic] Привет, мир!"
        b = prepare_batch(self.spec, now=self.now)
        self.assertNotEqual(a["takes"][0]["cache_key"], b["takes"][0]["cache_key"])
        self.assertEqual(a["takes"][1]["cache_key"], b["takes"][1]["cache_key"])

    def test_other_voice_or_model_cannot_reuse_approved_audio_key(self):
        a = prepare_batch(self.spec, now=self.now)
        self.spec["voices"]["narrator"]["provider_voice_id"] = "c" * 32
        b = prepare_batch(self.spec, now=self.now)
        self.assertNotEqual(a["takes"][0]["cache_key"], b["takes"][0]["cache_key"])

    def test_spoken_words_cannot_change_with_acting_direction(self):
        self.spec["lines"][0]["directed_text"] = "[warm] Привет!"
        with self.assertRaisesRegex(ProductionError, "preserve"):
            prepare_batch(self.spec, now=self.now)

    def test_missing_voice_is_not_replaced_with_provider_default(self):
        self.spec["voices"]["narrator"]["provider_voice_id"] = ""
        with self.assertRaisesRegex(ProductionError, "voice ID"):
            prepare_batch(self.spec, now=self.now)

    def test_expired_or_invalid_quote_blocks_preparation(self):
        for patch in ({"valid_until": "2026-11-16T00:00:00Z"}, {"checked_at": "2026-11-16"},
                      {"model": "drama-3"}, {"unit": "characters"}):
            spec = copy.deepcopy(self.spec); spec["quote"].update(patch)
            with self.subTest(patch=patch), self.assertRaises(ProductionError):
                prepare_batch(spec, now=self.now)

    def test_free_offer_cannot_be_extended_by_local_configuration(self):
        self.spec["quote"]["valid_until"] = "2027-01-01T00:00:00Z"
        with self.assertRaisesRegex(ProductionError, "promotion"):
            prepare_batch(self.spec, now=self.now)

    def test_paid_model_cannot_use_zero_subscription_cost(self):
        self.spec["model"] = self.spec["quote"]["model"] = "drama-3"
        with self.assertRaisesRegex(ProductionError, "Paid models"):
            prepare_batch(self.spec, now=self.now)


if __name__ == "__main__":
    unittest.main()
