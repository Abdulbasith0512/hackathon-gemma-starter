"""The front-end is plain files; make sure they parse and are wired together."""

import re
import shutil
import subprocess
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"


class FrontEndFilesTests(unittest.TestCase):
    def test_javascript_parses(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        result = subprocess.run([node, "--check", str(WEB / "app.js")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_html_references_existing_assets_and_every_id_the_script_uses(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        js = (WEB / "app.js").read_text(encoding="utf-8")
        for asset in re.findall(r'(?:href|src)="/static/([^"]+)"', html):
            self.assertTrue((WEB / asset).exists(), asset)
        ids = set(re.findall(r'id="([^"]+)"', html))
        used = set(re.findall(r'\$\("#([\w-]+)"\)', js))
        created_by_the_script = {"tick"}  # the "still working" timer inside the loading bubble
        self.assertEqual(sorted(used - ids - created_by_the_script), [])

    def test_no_secrets_or_api_keys_in_the_front_end(self):
        for f in WEB.iterdir():
            text = f.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"AIza[0-9A-Za-z_-]{20,}")
            self.assertNotIn("GOOGLE_API_KEY", text)

    def test_the_css_defines_a_dark_theme_and_respects_reduced_motion(self):
        css = (WEB / "styles.css").read_text(encoding="utf-8")
        self.assertIn("--bg:", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("@media (max-width: 900px)", css)


if __name__ == "__main__":
    unittest.main()
