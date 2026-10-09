#!/usr/bin/env python3
"""Tests for outlook_email_fonts.py (run: python3 test_outlook_email_fonts.py)."""
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import outlook_email_fonts as o  # noqa: E402

YAHEI = "font-family:'Microsoft YaHei','微软雅黑',Arial,sans-serif;"
MSO = o.MSO_BLOCK

GOOD = f"""<!DOCTYPE html><html><head><meta charset="utf-8">{MSO}</head>
<body style="{YAHEI}"><table width="680" style="{YAHEI}"><tr>
<td style="{YAHEI} font-size:15px;">中文 <strong>重点</strong> text</td></tr>
<tr><td style="height:6px; font-size:1px;">&nbsp;</td></tr></table>
<p style="{YAHEI}">段落 <a href="https://example.com" style="{YAHEI}">链接</a></p></body></html>"""

OLD_STYLE = """<html><head></head>
<body style="font-family:-apple-system,'PingFang SC','Microsoft YaHei',Arial,sans-serif;">
<table width="680"><tr><td style="font-size:15px;">中文正文</td></tr></table></body></html>"""


class CheckTests(unittest.TestCase):
    def test_good_passes(self):
        self.assertEqual(o.check_html(GOOD), [])

    def test_missing_mso_block_fails(self):
        issues = o.check_html(GOOD.replace(MSO, ""))
        self.assertTrue(any("mso" in m for _, m in issues))

    def test_body_only_font_fails_on_td(self):
        issues = o.check_html(OLD_STYLE)
        self.assertTrue(any("<td>" in m for _, m in issues))

    def test_wrong_first_font_fails(self):
        bad = GOOD.replace(f'<p style="{YAHEI}">', "<p style=\"font-family:'PingFang SC','Microsoft YaHei',sans-serif;\">")
        issues = o.check_html(bad)
        self.assertTrue(any("<p>" in m and "PingFang" in m for _, m in issues))

    def test_web_fonts_fail(self):
        for snippet in ['<link href="https://fonts.googleapis.com/css2?family=Inter" rel="stylesheet">',
                        "<style>@font-face{font-family:X;src:url(x.woff)}</style>"]:
            bad = GOOD.replace("</head>", snippet + "</head>")
            self.assertTrue(any("Web font" in m for _, m in o.check_html(bad)), snippet)
        bad = GOOD.replace(f'<p style="{YAHEI}">', "<p style=\"font-family:'Microsoft YaHei',Inter,sans-serif;\">")
        self.assertTrue(any("Web font" in m for _, m in o.check_html(bad)))

    def test_spacer_without_text_ignored(self):
        self.assertEqual(o.check_html(GOOD), [])


class FixTests(unittest.TestCase):
    def test_fix_makes_old_style_pass_and_keeps_text(self):
        fixed = o.fix_html(OLD_STYLE)
        self.assertEqual(o.check_html(fixed), [])
        self.assertEqual(o.visible_text(fixed), o.visible_text(OLD_STYLE))
        self.assertIn("font-size:15px", fixed)

    def test_fix_is_idempotent(self):
        once = o.fix_html(OLD_STYLE)
        self.assertEqual(o.fix_html(once), once)

    def test_cli_check_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            g, b = Path(d, "g.html"), Path(d, "b.html")
            g.write_text(GOOD, encoding="utf-8")
            b.write_text(OLD_STYLE, encoding="utf-8")
            run = lambda p: subprocess.run([sys.executable, str(HERE / "outlook_email_fonts.py"), "check", str(p)], capture_output=True).returncode
            self.assertEqual(run(g), 0)
            self.assertEqual(run(b), 1)


class CopySyncTest(unittest.TestCase):
    def test_monthly_report_copy_identical(self):
        other = HERE.parent.parent / "monthly-report-workflow" / "scripts" / "outlook_email_fonts.py"
        if not other.exists():
            self.skipTest("monthly-report-workflow not installed alongside")
        h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(h(other), h(HERE / "outlook_email_fonts.py"),
                         "Keep visual-mail and monthly-report-workflow copies of outlook_email_fonts.py identical")


if __name__ == "__main__":
    unittest.main(verbosity=2)
