import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DashboardSmokeTests(unittest.TestCase):
    def test_dashboard_data_builds_from_saved_outputs(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "dashboard" / "build_data.py")],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("latest 2026-06-22", result.stdout)
        content = (ROOT / "dashboard" / "data.js").read_text(encoding="utf-8")
        payload = json.loads(content.removeprefix("window.VIREO_DATA = ").removesuffix(";\n"))
        self.assertEqual(payload["overview"]["default_week"], "2026-06-22")
        self.assertEqual(payload["overview"]["by_week"]["2026-06-22"]["tickets_handled"], 192)
        self.assertEqual(
            sum(payload["overview"]["by_week"]["2026-06-22"]["issues"].values()),
            payload["overview"]["by_week"]["2026-06-22"]["tickets_created"],
        )
        self.assertEqual(payload["repeat_contacts"]["delivery_rate"], 14.34)
        self.assertEqual(payload["repeat_contacts"]["pilot_target"], 10.76)
        self.assertEqual(payload["repeat_contacts"]["capacity_value_inr"], 9350)
        self.assertTrue(payload["leaderboard"]["by_week"]["2026-06-22"])
        self.assertEqual(
            sum(row["closed"] for row in payload["leaderboard"]["by_week"]["2026-06-22"]),
            payload["overview"]["by_week"]["2026-06-22"]["tickets_handled"],
        )

    def test_dashboard_has_required_product_views(self):
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        for phrase in (
            "Vireo Support Weekly Digest",
            "Agent leaderboard",
            "Support Opportunities",
            "Support-capacity value, not guaranteed cash savings.",
        ):
            self.assertIn(phrase, html)
        self.assertLess(html.index("Weekly Digest</button>"), html.index("Agent Leaderboard</button>"))
        self.assertLess(html.index("Agent Leaderboard</button>"), html.index("Support Opportunities</button>"))

    def test_dashboard_week_controls_are_synchronized_and_opportunities_are_bounded(self):
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="digest-week-select"', html)
        self.assertIn('id="leaderboard-week-select"', html)
        self.assertNotIn('id="issue-search"', html)
        self.assertIn('id="issue-summary"', html)
        self.assertIn('id="weekly-issue-list"', html)
        self.assertIn("function setSelectedWeek(week)", script)
        self.assertIn("categories.slice(0, 5)", script)
        self.assertIn("14.34%", html)
        self.assertIn("10.76%", html)
        self.assertIn("₹9,350", html)
        self.assertNotIn("is excluded", html)


if __name__ == "__main__":
    unittest.main()
