"""Regression for the real deep-profile Chromium socket launch failure."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from repager.browser import BrowserAdapter

class TempDirTests(unittest.TestCase):
    def test_rejects_long_default_before_launch(self):
        browser=BrowserAdapter()
        with patch.dict('os.environ', {'TMPDIR':'/trusted/'+'x'*60}), patch('repager.browser.subprocess.Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError,'socket path'):
                browser._spawn_worker('capture', {})
            spawn.assert_not_called()
    def test_explicit_short_scratch_overrides_only_child_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            if len(directory.encode())>50:
                self.skipTest('Test runner scratch itself exceeds the documented socket budget')
            with patch.dict('os.environ', {'TMPDIR':'/trusted/'+'x'*60}), patch('repager.browser.subprocess.Popen') as spawn:
                process=spawn.return_value
                process.communicate.return_value=(b'{"ok":true}',b'')
                process.returncode=0
                browser=BrowserAdapter(temp_dir=directory)
                self.assertEqual(browser._spawn_worker('capture', {}),{'ok':True})
                self.assertEqual(spawn.call_args.kwargs['env']['TMPDIR'],directory)
                import os
                self.assertGreater(len(os.environ['TMPDIR']),50)
    def test_untrusted_or_long_temp_setting_rejected(self):
        for bad in ['relative/path','/trusted/'+'x'*60,42]:
            with self.assertRaises(ValueError):
                BrowserAdapter(temp_dir=bad)
