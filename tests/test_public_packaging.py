"""Offline public-release hygiene; no network, git or installed browser required."""
import json
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class PublicPackagingTests(unittest.TestCase):
    def test_license_and_version_metadata_agree(self):
        package = json.loads((ROOT / 'package.json').read_text())
        locked = json.loads((ROOT / 'package-lock.json').read_text())
        dashboard = json.loads((ROOT / 'dashboard/manifest.json').read_text())
        manifest = (ROOT / 'plugin.yaml').read_text()
        match = re.search(r'^version: (.+)$', manifest, re.M)
        assert match is not None, 'plugin version is required'
        version = match.group(1).strip('"')
        self.assertEqual(package['license'], 'MIT')
        self.assertEqual(locked['packages']['']['license'], 'MIT')
        self.assertEqual(package['version'], version)
        self.assertEqual(locked['version'], version)
        self.assertEqual(dashboard['version'], version)
        self.assertTrue((ROOT / 'LICENSE').read_text().startswith('MIT License\n'))
        self.assertTrue((ROOT / 'dashboard/brand/Manrope-OFL.txt').is_file())
        self.assertIn('THIRD_PARTY_NOTICES.md', (ROOT / 'README.md').read_text())

    def test_local_documentation_links_resolve(self):
        docs = list(ROOT.glob('*.md'))
        for folder in ('docs', 'dashboard', 'skills'):
            docs.extend(p for p in (ROOT / folder).rglob('*.md') if 'node_modules' not in p.parts)
        for path in docs:
            for target in re.findall(r'\[[^\]\n]*\]\(([^)\s]+)\)', path.read_text()):
                parsed = urlsplit(target)
                if parsed.scheme or not parsed.path:
                    continue
                with self.subTest(document=str(path.relative_to(ROOT)), target=target):
                    self.assertTrue((path.parent / unquote(parsed.path)).exists())

    def test_browser_helpers_do_not_embed_machine_paths(self):
        for name in ('scripts/exercise_adapter.py', 'tests/test_browser.py',
                     'tests/test-browser-node.cjs', 'tests/test-browser-quality-node.cjs'):
            text = (ROOT / name).read_text()
            with self.subTest(file=name):
                self.assertIn('REPAGER_CHROMIUM_PATH', text)
                self.assertNotRegex(text, r"['\"]/opt/[^'\"]+")
        self.assertIn('required=True', (ROOT / 'scripts/exercise_adapter.py').read_text())

    def test_workbench_documents_displayed_guards(self):
        text = (ROOT / 'skills/workbench/SKILL.md').read_text()
        for name in ('expected_version', 'record_version', 'verification_signature'):
            self.assertIn(name, text)

    def test_current_release_copy_is_not_private_or_unlicensed(self):
        readme = (ROOT / 'README.md').read_text()
        submission = (ROOT / 'docs/SUBMISSION.md').read_text()
        self.assertNotIn('Private development, version', readme)
        self.assertNotIn('private and unlicensed', readme)
        self.assertNotIn('all still closed', submission)
        self.assertIn('0.3.0', submission)


if __name__ == '__main__':
    unittest.main()
