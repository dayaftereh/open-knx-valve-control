"""Offline KNX070 TP1 versus KNX/IP comparison tests."""
from datetime import date, datetime, timedelta, timezone
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from knx070_compare import match_frames, parse_serial_window


def tp(host_time: str = "12:34:56.000", payload: str = "1922") -> dict:
    return {
        "host_time": host_time, "source": "1.5.50", "destination": "4/4/2",
        "service": "GroupValueWrite", "payload_hex": payload,
        "short_value": None,
        "quality": {"checksum_ok": True, "even_parity_ok": True,
                    "start_stop_ok": True, "ack_valid": True},
    }


def ip(utc_time: str = "2026-10-17T10:34:56.030+00:00",
       payload: tuple[int, int] = (25, 34)) -> dict:
    return {
        "time_utc": utc_time, "source": "1.5.50", "destination": "4/4/2",
        "apci": "GroupValueWrite", "value": list(payload),
    }


class TestKNX070Match(unittest.TestCase):
    def test_exact_full_payload_and_time(self):
        r = match_frames([tp()], [ip()], date(2026, 10, 17), 120, 250)
        self.assertEqual(r["matched_count"], 1)
        self.assertEqual(r["tp_unmatched_count"], 0)
        self.assertEqual(r["median_abs_time_delta_ms"], 30)

    def test_payload_mismatch_detected(self):
        r = match_frames([tp()], [ip(payload=(25, 35))], date(2026, 10, 17),
                         120, 250)
        self.assertEqual(r["matched_count"], 0)
        self.assertEqual(r["tp_unmatched_count"], 1)

    def test_outside_time_window_detected(self):
        r = match_frames([tp()], [ip(utc_time="2026-10-17T10:34:57.000+00:00")],
                         date(2026, 10, 17), 120, 250)
        self.assertEqual(r["matched_count"], 0)

    def test_no_ip_reuse_for_repeated_telegram(self):
        r = match_frames([tp(), tp(host_time="12:34:56.100")], [ip()],
                         date(2026, 10, 17), 120, 250)
        self.assertEqual(r["matched_count"], 1)
        self.assertEqual(r["tp_unmatched_count"], 1)

    def test_invalid_tp_checksum_not_matched(self):
        bad = tp()
        bad["quality"]["checksum_ok"] = False
        r = match_frames([bad], [ip()], date(2026, 10, 17), 120, 250)
        self.assertEqual(r["tp_checksum_parity_ack_ok"], 0)
        self.assertEqual(r["matched_count"], 0)

    def test_serial_listening_window(self):
        with tempfile.TemporaryDirectory() as dirname:
            p = Path(dirname) / "log.txt"
            p.write_text(
                "12:34:50.500 KNX043 LISTENING RX_ONLY 120s TX_LOW\n"
                "12:35:31.500 STOP_REPLY KNX043 STOPPED RX_ONLY\n",
                encoding="utf-8")
            window = parse_serial_window(p, date(2026, 10, 17), 120)
            self.assertIsNotNone(window)
            self.assertEqual(window[0].isoformat(), "2026-10-17T12:34:50.500000+02:00")
            r = match_frames([tp()], [ip()], date(2026, 10, 17), 120, 250,
                             serial_window=window)
            self.assertEqual(r["ip_frames_during_serial_listen"], 1)
            self.assertEqual(r["ip_unmatched_during_serial_listen"], 0)


if __name__ == "__main__":
    unittest.main()
