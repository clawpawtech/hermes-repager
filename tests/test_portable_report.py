"""Offline report tests. Synthetic PNGs/receipts are NOT live browser proof."""
import base64
import copy
import html
from html.parser import HTMLParser
import importlib
import struct
import unittest
from unittest.mock import patch
import zlib

from repager.report import render_report
import repager.report as report_module


PAYLOAD = '</style><script>alert("SYNTHETIC")</script><img src="https://evil.invalid/" onerror="x"> & \'quoted\''


def synthetic_png(color):
    """One-pixel test color, not a captured page or a viewport assertion."""
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(b'\0' + bytes(color))) + chunk(b'IEND', b''))


def fixture():
    """Fully synthetic current + legacy protocol-1 receipt, thirteen checks."""
    section = {'headline_id': 'h', 'body_ids': ['b', 'b2'], 'cta_id': 'c',
               'layout': 'stack', 'alignment': 'left', 'spacing': 'comfortable',
               'background': '#ffffff', 'foreground': '#000000', 'accent': '#F7931A',
               'button_text': '#000000'}
    record = {
        'id': 'a' * 32, 'audience': 'SYNTHETIC reviewers', 'goal': 'SYNTHETIC compare copy',
        'source': {'url': 'https://synthetic.invalid/page', 'title': 'SYNTHETIC fixture',
                   'captured_at': '2026-01-01T00:00:00Z', 'limitations': ['Synthetic evidence only.'],
                   'viewports': []},
        'source_integrity': {'source_hash': 'b' * 64, 'signature': 'NEVER_DISPLAY_SOURCE_SIGNATURE'},
        'contract': {'headline_id': 'h', 'body_ids': ['b', 'b2'], 'cta_id': 'c',
                     'cta_text': 'Synthetic CTA', 'cta_destination': 'https://synthetic.invalid/start',
                     'approved_at': '2026-01-01T00:01:00Z'},
        'revisions': [{'number': 1, 'artifact_hash': 'c' * 64, 'contract_hash': 'd' * 64,
                       'section': section, 'created_at': '2026-01-01T00:02:00Z',
                       'model': 'synthetic-model', 'provider': 'synthetic-provider',
                       'instruction': 'NEVER_DISPLAY_RAW_PROMPT', 'signature': 'NEVER_DISPLAY_REVISION_SIGNATURE'}],
        'verification': {'revision': 1, 'artifact_hash': 'c' * 64, 'source_hash': 'b' * 64,
                         'contract_hash': 'd' * 64, 'checked_at': '2026-01-01T00:03:00Z',
                         'signature': 'NEVER_DISPLAY_RECEIPT_SIGNATURE',
                         'viewports': [], 'limitations': ['No live browser used.'],
                         'checks': [{'id': 'synthetic-' + str(i), 'label': 'Synthetic check ' + str(i),
                                     'status': ('pass', 'fail', 'unknown')[i % 3],
                                     'detail': 'Synthetic receipt detail; not live verification.'} for i in range(13)]}}
    images = {}
    for i, (name, width, height) in enumerate((('desktop', 1440, 900), ('mobile', 390, 844))):
        src = {'name': name, 'width': width, 'height': height, 'screenshot': f'source-{name}.png',
               'elements': [{'id': 'h', 'text': '  Exact synthetic headline\n'},
                            {'id': 'b', 'text': 'Synthetic body <keep text>.'},
                            {'id': 'b2', 'text': 'Second body\nline.'},
                            {'id': 'c', 'text': 'Synthetic CTA', 'href': 'https://synthetic.invalid/start'}]
               if name == 'desktop' else [{'id': 'mobile-only', 'text': 'DO_NOT_BIND_MOBILE_COPY'}]}
        before = synthetic_png((20 + i, 40, 60))
        record['source']['viewports'].append(src)
        images[src['screenshot']] = before
        prev = {'name': name, 'width': width, 'height': height,
                'screenshot': f'r1-{"e" * 32}-preview-{name}.png'}
        record['verification']['viewports'].append(prev)
        images[prev['screenshot']] = synthetic_png((100 + i, 120, 140))
    return record, images


class Parsed(HTMLParser):
    def __init__(self, data):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []
        self.feed(data)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


class PortableReportTests(unittest.TestCase):
    def setUp(self):
        self.record, self.images = fixture()

    def report(self):
        return render_report(self.record, self.images).decode('utf-8')

    def test_four_exact_bound_images_and_explicit_viewports(self):
        document = self.report()
        parsed = Parsed(document)
        images = [attrs for tag, attrs in parsed.tags if tag == 'img']
        self.assertEqual(len(images), 4)
        self.assertEqual({base64.b64decode(img['src'].split(',', 1)[1]) for img in images}, set(self.images.values()))
        for image in images:
            self.assertTrue(image['src'].startswith('data:image/png;base64,'))
            self.assertIn('Before' if 'original' in image['alt'] else 'After', image['alt'])
            self.assertIn(f"{image['width']} × {image['height']} px", image['alt'])
        self.assertEqual([image['width'] for image in images], ['1440', '1440', '390', '390'])
        self.assertIn('  Exact synthetic headline\n', ''.join(parsed.text))
        self.assertIn('Synthetic body &lt;keep text&gt;.', document)
        self.assertNotIn('DO_NOT_BIND_MOBILE_COPY', document)
        self.assertIn('Different scope', document)
        self.assertIn('standalone TEXT-ONLY hero', document)
        self.assertIn('index.html - implementation', document)
        self.assertIn('review.html - review packet', document)

    def test_passive_csp_and_no_external_resource_attributes(self):
        parsed = Parsed(self.report())
        policy = next(a['content'] for t, a in parsed.tags if t == 'meta' and a.get('http-equiv') == 'Content-Security-Policy')
        for directive in ("default-src 'none'", 'img-src data:', "style-src 'unsafe-inline'", "script-src 'none'",
                          "object-src 'none'", "base-uri 'none'", "form-action 'none'"):
            self.assertIn(directive, policy)
        forbidden = {'script', 'iframe', 'object', 'embed', 'link', 'base', 'form', 'button', 'a', 'video', 'audio', 'source'}
        for tag, attrs in parsed.tags:
            self.assertNotIn(tag, forbidden)
            for key, value in attrs.items():
                self.assertFalse(key.lower().startswith('on'))
                if key in ('src', 'href', 'srcset', 'action', 'poster'):
                    self.assertEqual(tag, 'img')
                    self.assertEqual(key, 'src')
                    self.assertTrue(value.startswith('data:image/png;base64,'))
        self.assertNotIn('@import', self.report())
        self.assertNotIn('url(', self.report())

    def test_all_displayed_metadata_is_escaped(self):
        record = self.record
        record['audience'] = record['goal'] = PAYLOAD
        record['source']['url'] = 'https://synthetic.invalid/?q=' + PAYLOAD
        record['source']['title'] = record['source']['captured_at'] = PAYLOAD
        record['source']['limitations'] = [PAYLOAD]
        record['verification']['limitations'] = [PAYLOAD]
        record['verification']['checked_at'] = PAYLOAD
        record['contract']['approved_at'] = PAYLOAD
        record['contract']['cta_text'] = PAYLOAD
        record['contract']['cta_destination'] = 'https://synthetic.invalid/' + PAYLOAD
        for element in record['source']['viewports'][0]['elements']:
            element['text'] = PAYLOAD
            if element['id'] == 'c':
                element['href'] = record['contract']['cta_destination']
        record['revisions'][0].update(model=PAYLOAD, provider=PAYLOAD, created_at=PAYLOAD,
                                      safety_adjustments=[PAYLOAD, {'property': PAYLOAD, 'reason': PAYLOAD}])
        for check in record['verification']['checks']:
            check['label'] = check['detail'] = PAYLOAD
        record['decision'] = {'revision': 1, 'artifact_hash': 'c' * 64, 'verdict': PAYLOAD,
                              'reason': PAYLOAD, 'decided_at': PAYLOAD, 'signature': 'NEVER_DISPLAY_DECISION_SIGNATURE'}
        document = self.report()
        self.assertNotIn(PAYLOAD, document)
        self.assertIn(html.escape(PAYLOAD, quote=True), document)
        parsed = Parsed(document)
        self.assertIn(PAYLOAD, ''.join(parsed.text))
        self.assertFalse(any(t == 'script' for t, _ in parsed.tags))
        self.assertEqual(len([t for t, _ in parsed.tags if t == 'img']), 4)
        for _, attrs in parsed.tags:
            self.assertFalse(any(k.startswith('on') for k in attrs))
        self.assertNotIn('NEVER_DISPLAY', document)

    def test_deterministic_no_io_and_no_input_mutation_or_legacy_defaults(self):
        original = copy.deepcopy(self.record)
        images = copy.deepcopy(self.images)
        with patch('builtins.open', side_effect=AssertionError('filesystem access')), \
                patch('socket.socket', side_effect=AssertionError('network access')):
            first = render_report(self.record, self.images)
            second = render_report(self.record, self.images)
        self.assertIsInstance(first, bytes)
        self.assertEqual(first, second)
        self.assertEqual(self.record, original)
        self.assertEqual(self.images, images)
        self.assertNotIn('protocol', self.record['verification'])
        self.assertNotIn('decision', self.record)
        self.assertNotIn('origin', self.record['revisions'][0])
        self.assertNotIn('parent_revision', self.record['revisions'][0])

    def test_module_reload_has_no_resource_io(self):
        with patch('builtins.open', side_effect=AssertionError('resource read at import')), \
                patch('socket.socket', side_effect=AssertionError('network at import')):
            importlib.reload(report_module)
        self.assertIn('repager', self.report())

    def test_protocol_one_is_thirteen_actual_checks_no_upgrade_or_score(self):
        document = self.report()
        self.assertIn('13 checks', document)
        self.assertIn('Protocol 1 (legacy; not upgraded or re-run)', document)
        self.assertIn('5 pass', document)
        self.assertIn('4 fail', document)
        self.assertIn('4 unknown', document)
        self.assertIn('Unknown is not pass', document)
        self.assertIn('general quality score', document)
        for check in self.record['verification']['checks']:
            self.assertIn(check['id'], document)
            self.assertIn(check['label'], document)
            self.assertIn(check['detail'], document)
        self.record['verification']['protocol'] = 2
        self.assertIn('Protocol 2 (as recorded', self.report())
        self.assertIn('13 checks', self.report())

    def test_missing_foreign_and_invalid_images_fail_cleanly(self):
        name = next(iter(self.images))
        variants = [None, {}, {k: v for k, v in self.images.items() if k != name},
                    dict(self.images, foreign=b'foreign'), dict(self.images, **{name: 'not bytes'}),
                    dict(self.images, **{name: b'<svg onload="x"/>'}), dict(self.images, **{name: b''}),
                    dict(self.images, **{name: b'\x89PNG\r\n\x1a\n'}),
                    dict(self.images, **{name: self.images[name][:-1]}),
                    dict(self.images, **{name: self.images[name] + b'<script>bad</script>'}),
                    dict(self.images, **{name: self.images[name][:-4] + b'BAD!'})]
        for value in variants:
            with self.subTest(value_type=type(value)), self.assertRaises(ValueError):
                render_report(self.record, value)
        for name in ('../source-desktop.png', '/source-desktop.png', 'https://evil.invalid/x.png',
                     'data:image/png;base64,AA', 'source-desktop.png" onerror="x', 'foreign.png'):
            record = copy.deepcopy(self.record)
            record['source']['viewports'][0]['screenshot'] = name
            images = dict(self.images)
            images[name] = images.pop('source-desktop.png')
            with self.subTest(name=name), self.assertRaises(ValueError):
                render_report(record, images)

    def test_receipt_current_binding_and_viewport_failures(self):
        for key, value in (('revision', 2), ('artifact_hash', '0' * 64)):
            record = copy.deepcopy(self.record)
            record['verification'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                render_report(record, self.images)
        record = copy.deepcopy(self.record)
        record['verification']['viewports'][0]['screenshot'] = f'r2-{"e" * 32}-preview-desktop.png'
        with self.assertRaises(ValueError):
            render_report(record, self.images)
        for number in (True, 1.0, '1', '1|.*', 0):
            record = copy.deepcopy(self.record)
            record['revisions'][0]['number'] = record['verification']['revision'] = number
            with self.subTest(number=number), self.assertRaises(ValueError):
                render_report(record, self.images)
        for bad in ([], [self.record['source']['viewports'][0]] * 2,
                    [dict(self.record['source']['viewports'][0], width=True), self.record['source']['viewports'][1]]):
            record = copy.deepcopy(self.record)
            record['source']['viewports'] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                render_report(record, self.images)
        self.record['contract']['cta_text'] = 'Different CTA'
        with self.assertRaises(ValueError):
            self.report()

    def test_local_remix_parent_changed_props_and_safety_adjustments(self):
        parent = copy.deepcopy(self.record['revisions'][0])
        current = copy.deepcopy(parent)
        current.update(number=2, origin='local-remix', parent_revision=1,
                       safety_adjustments=[{'property': 'button_text', 'requested': '#ffffff',
                                            'applied': '#000000', 'reason': 'Synthetic adjustment.'}])
        current['section']['layout'] = 'split'
        self.record['revisions'].append(current)
        self.record['verification']['revision'] = 2
        for viewport in self.record['verification']['viewports']:
            old = viewport['screenshot']
            viewport['screenshot'] = old.replace('r1-', 'r2-', 1)
            self.images[viewport['screenshot']] = self.images.pop(old)
        document = self.report()
        self.assertIn('LOCAL_REMIX', document)
        self.assertIn('no model inference for this revision', document)
        self.assertNotIn('Recorded model', document)
        self.assertIn('Changes from parent revision 1', document)
        self.assertIn('layout: <code>stack</code> → <code>split</code>', document)
        self.assertIn('Synthetic adjustment.', document)
        self.assertNotIn('instruction', document)

    def test_decision_absent_or_recorded_not_fake_endorsement(self):
        document = self.report()
        self.assertIn('Not recorded.', document)
        self.assertIn('No endorsement is implied', document)
        self.record['decision'] = {'revision': 1, 'artifact_hash': 'c' * 64, 'verdict': 'needs_changes',
                                   'reason': 'SYNTHETIC: review spacing', 'signature': 'SECRET_SIGNATURE'}
        document = self.report()
        self.assertIn('needs_changes', document)
        self.assertIn('SYNTHETIC: review spacing', document)
        self.assertIn('not deployment approval', document)
        self.assertIn('not independently verified', document)
        self.assertNotIn('SECRET_SIGNATURE', document)
        self.assertNotIn('NEVER_DISPLAY', document)

    def test_unknown_origin_is_not_invented_and_bad_record_is_value_error(self):
        current = self.record['revisions'][0]
        current.pop('model')
        current.pop('provider')
        self.assertIn('Origin not recorded', self.report())
        for record in (None, {}, {'revisions': []}):
            with self.subTest(record=record), self.assertRaises(ValueError):
                render_report(record, self.images)
        self.record['verification']['checks'][0]['status'] = PAYLOAD
        with self.assertRaises(ValueError):
            self.report()


if __name__ == '__main__':
    unittest.main()
