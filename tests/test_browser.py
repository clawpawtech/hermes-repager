"""Offline unit tests; real Chrome/network tests require REPAGER_BROWSER_INTEGRATION=1."""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from repager.browser import BrowserAdapter, is_public_ip, is_valid_http_url

CHROME = os.environ.get('REPAGER_CHROMIUM_PATH')
PUBLIC = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))]


class PolicyTests(unittest.TestCase):
    @patch('repager.browser.socket.getaddrinfo', return_value=PUBLIC)
    def test_urls(self, resolver):
        for url in ('https://example.com/', 'http://8.8.8.8:80/', 'https://[2606:4700::1111]/'):
            self.assertTrue(is_valid_http_url(url), url)
        for url in ('http://127.1', 'http://0x08080808', 'http://134744072', 'http://010.0.0.1', 'https://@example.com', 'https://u:p@example.com', 'https://example.com\\@evil.com', 'https://example.com/%0a', 'https://example.com/\t', 'https://example.com:80', 'http://example.com:443', 'file:///x', 'https:///example.com'):
            self.assertFalse(is_valid_http_url(url), url)

    def test_ip_ranges(self):
        for ip in ('8.8.8.8', '2606:4700:4700::1111'):
            self.assertTrue(is_public_ip(ip), ip)
        for ip in ('192.168.1.1', '169.254.0.1', '100.64.0.1', '192.0.0.9', '198.18.0.1', '203.0.113.1', '::1', '::ffff:8.8.8.8', '2002:0808:0808::1', '2001::1', '2001:db8::1'):
            self.assertFalse(is_public_ip(ip), ip)

    @patch('repager.browser.socket.getaddrinfo', return_value=PUBLIC + [(socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('::1', 443, 0, 0))])
    def test_mixed_dns_rejected(self, resolver):
        self.assertFalse(is_valid_http_url('https://example.com'))
        resolver.assert_called_once()

    @patch('repager.browser.socket.getaddrinfo', side_effect=AssertionError('verify must not resolve DNS'))
    def test_large_preview_and_trusted_sandbox_arg(self, resolver):
        with tempfile.TemporaryDirectory() as directory:
            adapter = BrowserAdapter(allow_no_sandbox=True)
            with patch.object(adapter, '_spawn_worker', return_value={'checks': []}) as worker:
                adapter.verify('<p>' + 'x' * 6000 + '</p>', 'https://example.com/keep/', Path(directory))
                payload = worker.call_args.args[-1]
                self.assertTrue(payload['allow_no_sandbox'])
                self.assertEqual(payload['expected_cta'], 'https://example.com/keep/')
                self.assertIsNone(payload['expected_copy'])
                expected_copy = {'headline': 'Exact', 'bodies': ['First', 'Second'], 'cta_label': 'Keep'}
                adapter.verify('<p>Exact</p>', 'https://example.com/keep/', Path(directory), expected_copy=expected_copy)
                self.assertEqual(worker.call_args.args[-1]['expected_copy'], expected_copy)
                with self.assertRaises(TypeError):
                    adapter.verify('<p>Exact</p>', 'https://example.com/keep/', Path(directory), expected_copy)  # type: ignore[call-arg]
            with self.assertRaises(ValueError):
                adapter.verify('x' * 131073, 'https://example.com/', Path(directory))

    def test_worker_environment_and_process_group_timeout(self):
        adapter = BrowserAdapter(timeout=1)
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'hang.cjs'
            pidfile = Path(directory) / 'pid'
            script.write_text("const cp=require('node:child_process');const fs=require('node:fs');const c=cp.spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{detached:true,stdio:'ignore'});fs.writeFileSync(process.argv[2],String(c.pid));setInterval(()=>{},1000);")
            # Actual subprocess and descendant; fixed worker args still read only JSON stdin.
            adapter._worker = script
            original = subprocess.Popen
            def spawn(argv, **kwargs):
                self.assertTrue(kwargs['start_new_session'])
                self.assertNotIn('REPAGER_TEST_SECRET', kwargs['env'])
                return original(argv + [str(pidfile)], **kwargs)
            with patch.dict(os.environ, {'REPAGER_TEST_SECRET': 'do-not-leak'}), patch('repager.browser.subprocess.Popen', side_effect=spawn):
                with self.assertRaises(TimeoutError):
                    adapter._spawn_worker('verify', {})
            pid = int(pidfile.read_text())
            self.addCleanup(self.kill_if_live, pid)
            stat = Path(f'/proc/{pid}/stat')
            # Signal delivery to a detached child is asynchronous even after
            # its parent exited. Assert bounded eventual cleanup, not scheduler
            # ordering on the very next Python instruction.
            deadline = time.monotonic() + 1
            while stat.exists() and stat.read_text().split()[2] != 'Z' and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(not stat.exists() or stat.read_text().split()[2] == 'Z', 'live descendant left behind after bounded cleanup interval')

    @staticmethod
    def kill_if_live(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


@unittest.skipUnless(os.environ.get('REPAGER_BROWSER_INTEGRATION') == '1', 'explicit live integration opt-in required')
class LiveBrowserTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.out = Path(self.directory.name)
        self.browser_adapter = BrowserAdapter(CHROME, timeout=90, allow_no_sandbox=os.environ.get('REPAGER_ALLOW_NO_SANDBOX') == '1')

    def assert_images(self, result):
        from PIL import Image
        for view in result['viewports']:
            with Image.open(self.out / view['screenshot']) as image:
                self.assertEqual(image.size, (view['width'], view['height']))

    @unittest.skipUnless(os.environ.get('REPAGER_PUBLIC_INTEGRATION') == '1', 'separate explicit public-network opt-in required')
    def test_capture_two_real_public_pages(self):
        for url in ('https://example.com', 'https://www.iana.org/help/example-domains'):
            result = self.browser_adapter.capture(url, self.out)
            self.assert_images(result)
            self.assertTrue(result['title'])
            self.assertTrue(all(v['elements'] for v in result['viewports']))
            self.assertLessEqual(len(result['palette']), 16)
            self.assertTrue(result['palette'])
            ids = [e['id'] for v in result['viewports'] for e in v['elements']]
            self.assertEqual(len(ids), len(set(ids)))

    def verify_fixture(self, body, expected='https://example.com/keep/'):
        report = self.browser_adapter.verify('<!doctype html><meta name="viewport" content="width=device-width"><body>' + body, expected, self.out)
        self.assert_images(report)
        self.assertEqual(report['protocol'], 2)
        self.assertEqual(len(report['checks']), 29)
        for name in ('desktop', 'mobile'):
            for suffix in ('headline-copy', 'body-copy', 'cta-label'):
                self.assertEqual(next(c for c in report['checks'] if c['id'] == f'{name}-{suffix}')['status'], 'unknown')
        ids = [c['id'] for c in report['checks']]
        self.assertEqual(len(ids), len(set(ids)))
        return {c['id']: c for c in report['checks']}

    def test_preview_large_tall_local_fixture(self):
        checks = self.verify_fixture('<a href="https://example.com/keep/">Keep</a><p>' + 'text ' * 1100 + '</p><div style="height:2500px">Tall</div>')
        for name in ('desktop', 'mobile'):
            for suffix in ('cta-destination', 'keyboard-focusable', 'visible-content', 'horizontal-overflow', 'scripts-disabled'):
                self.assertEqual(checks[f'{name}-{suffix}']['status'], 'pass', checks)
            self.assertEqual(checks[f'{name}-vertical-extent']['status'], 'unknown')

    def test_preview_hostile_scripts_and_network_denied(self):
        checks = self.verify_fixture('<script>window.__repagerHostile=1;document.body.innerHTML="PWNED";fetch("http://127.0.0.1/")</script><img src="http://127.0.0.1/secret"><iframe src="https://example.com/"></iframe><a href="https://example.com/keep/">Keep</a>')
        self.assertEqual(checks['preview-no-network']['status'], 'pass')
        self.assertGreater(checks['preview-no-network']['attempted_requests'], 0)
        for name in ('desktop', 'mobile'):
            self.assertEqual(checks[f'{name}-scripts-disabled']['status'], 'pass')

    def test_actual_failures_not_all_pass(self):
        checks = self.verify_fixture('<div style="width:2200px">Wide</div><a tabindex="-1" href="https://example.com/keep/">Keep</a>')
        self.assertEqual(checks['mobile-horizontal-overflow']['status'], 'fail')
        self.assertEqual(checks['desktop-keyboard-focusable']['status'], 'fail')
        checks = self.verify_fixture('<a href="https://example.com/keep">Different trailing slash</a>')
        self.assertEqual(checks['desktop-cta-destination']['status'], 'fail')
        checks = self.verify_fixture('<p style="display:none">Hidden</p>')
        self.assertEqual(checks['desktop-visible-content']['status'], 'fail')


if __name__ == '__main__':
    unittest.main()