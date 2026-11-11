"""Deterministic, passive portable review. No I/O or authentication is done here.

The caller must validate and authenticate the record, current artifact and image
bytes before calling ``render_report``. This module neither changes signed data
nor treats hashes as independent attestation. Only explicitly selected metadata
is displayed; prompts, signatures and arbitrary record fields are never dumped.
"""
from __future__ import annotations

import base64
import html
import re
import struct
import zlib

__all__ = ['render_report']

_PROPS = ('layout', 'alignment', 'spacing', 'background', 'foreground', 'accent', 'button_text')
_CSP = ("default-src 'none'; img-src data:; style-src 'unsafe-inline'; "
        "script-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'")
_CSS = """
:root{color-scheme:light;--ink:#202522;--muted:#555f59;--line:#d7ddd7;--paper:#fff;--orange:#F7931A}
*{box-sizing:border-box}body{margin:0;background:#f3f5f1;color:var(--ink);font:16px/1.65 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1280px;margin:auto;padding:40px 36px 64px}header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid var(--orange);padding-bottom:22px;gap:16px}
.brand{font-size:28px;font-weight:800;letter-spacing:-1.2px}
.eyebrow{font-size:12px;letter-spacing:1.6px;text-transform:uppercase;font-weight:750;color:var(--muted)}h1{font-size:clamp(32px,5vw,54px);line-height:1.1;letter-spacing:-1.5px;margin:14px 0 20px;max-width:850px}h2{font-size:25px;line-height:1.25;letter-spacing:-.6px;margin:0 0 18px}h3{font-size:17px;margin:0 0 12px}p{margin:0 0 14px}.intro{padding:36px 0 18px}.lead{max-width:780px;font-size:19px}.card{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:26px;margin:22px 0}.notice{background:#fff4df;border-left:5px solid var(--orange);padding:18px 22px;border-radius:0 10px 10px 0;margin:22px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:22px;min-width:0}.grid>*{min-width:0}.meta{display:grid;grid-template-columns:minmax(120px,180px) minmax(0,1fr);gap:10px 20px;margin:0}dt{color:var(--muted);font-size:14px}dd{margin:0;overflow-wrap:anywhere;white-space:pre-wrap}code{font:13px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}.copy{white-space:pre-wrap;overflow-wrap:anywhere;border-left:2px solid var(--line);padding-left:18px}.copy p{white-space:pre-wrap}figure{margin:0;min-width:0}figcaption{font-size:14px;font-weight:650;margin-bottom:12px}img{display:block;max-width:100%;height:auto;border:1px solid var(--line);border-radius:8px;background:#f3f5f1}.image-frame{max-height:620px;overflow:auto;border-radius:8px}.mobile-shot{max-width:390px;margin:auto}.comparison{margin-top:28px}.counts{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}.pill{padding:5px 12px;border:1px solid var(--line);border-radius:999px;background:#f3f5f1;font-size:14px;font-weight:700}.pass{background:#e9f4ed;color:#235739}.fail{background:#fcebea;color:#8b2824}.unknown{background:#fff1d4;color:#684200}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px;text-align:left}th,td{border-bottom:1px solid var(--line);padding:14px 12px;vertical-align:top;overflow-wrap:anywhere}th{font-weight:700;background:#f6f7f4}td:first-child{min-width:145px}td:last-child{min-width:210px}td p{margin:8px 0 0}.small{font-size:14px;color:var(--muted)}ul{padding-left:22px}li{margin-bottom:8px;overflow-wrap:anywhere}summary{cursor:pointer;font-weight:650}details[open] summary{margin-bottom:16px}footer{border-top:1px solid var(--line);padding-top:22px;color:var(--muted);font-size:14px}.break{overflow-wrap:anywhere;white-space:pre-wrap}
@media(max-width:700px){main{padding:22px 16px 40px}header{align-items:flex-start}.grid{grid-template-columns:1fr}.card{padding:20px 16px;border-radius:12px}.meta{grid-template-columns:1fr;gap:4px}.meta dd{margin-bottom:12px}.lead{font-size:17px}h1{letter-spacing:-1px}.image-frame{max-height:none}th,td{padding:10px 8px}}
@media print{body{background:white;font-size:10pt}main{max-width:none;padding:0}header{padding-bottom:12px}.card{padding:14px;border-radius:0;break-inside:auto}.notice{border:1px solid #888;border-left:5px solid #F7931A}h1{font-size:30pt}h2,h3,figcaption{break-after:avoid}figure,tr,.counts{break-inside:avoid}.image-frame{max-height:none;overflow:visible}img{max-height:230mm;object-fit:contain;object-position:top}details>*{display:block}details summary{display:none}.table-wrap{overflow:visible}th,td{min-width:0!important}footer{margin-top:20px}}
"""


def _e(value):
    return html.escape(str(value), quote=True)


def _shown(value):
    return 'Not recorded' if value is None or value == '' else value


def _meta(items):
    return '<dl class="meta">' + ''.join(
        f'<dt>{_e(label)}</dt><dd>{_e(_shown(value))}</dd>' for label, value in items
    ) + '</dl>'


def _viewports(value):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError('report requires exactly desktop and mobile viewports')
    result = {}
    for viewport in value:
        if not isinstance(viewport, dict) or viewport.get('name') not in ('desktop', 'mobile'):
            raise ValueError('report viewport is invalid')
        name = viewport['name']
        if name in result:
            raise ValueError('report viewport is duplicated')
        for key in ('width', 'height'):
            number = viewport.get(key)
            if type(number) is not int or not 1 <= number <= 4000:
                raise ValueError('report viewport dimensions are invalid')
        result[name] = viewport
    return result


def _png(data):
    """Check the PNG container, without decoding or inflating untrusted pixels."""
    if not isinstance(data, bytes) or not data.startswith(b'\x89PNG\r\n\x1a\n'):
        return False
    offset = 8
    has_header = has_data = False
    while offset + 12 <= len(data):
        size = int.from_bytes(data[offset:offset + 4], 'big')
        end = offset + 12 + size
        if end > len(data):
            return False
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:end - 4]
        if zlib.crc32(data[offset + 4:end - 4]) != int.from_bytes(data[end - 4:end], 'big'):
            return False
        if not has_header:
            if kind != b'IHDR' or size != 13:
                return False
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
            if not (width and height and depth in depths.get(color, ()) and
                    compression == filtering == 0 and interlace in (0, 1)):
                return False
            has_header = True
        elif kind == b'IHDR':
            return False
        if kind == b'IDAT':
            has_data = True
        if kind == b'IEND':
            return size == 0 and has_data and end == len(data)
        offset = end
    return False


def _bind_images(record, images, current, receipt):
    source = _viewports(record['source']['viewports'])
    preview = _viewports(receipt['viewports'])
    names = []
    for name in ('desktop', 'mobile'):
        source_name = source[name].get('screenshot')
        preview_name = preview[name].get('screenshot')
        if source_name != f'source-{name}.png':
            raise ValueError('report source image is not controlled')
        pattern = rf'r{current["number"]}-[0-9a-f]{{32}}-preview-{name}\.png'
        if not isinstance(preview_name, str) or re.fullmatch(pattern, preview_name) is None:
            raise ValueError('report preview image is not controlled or current')
        names.extend((source_name, preview_name))
    if not isinstance(images, dict) or len(images) != 4 or set(images) != set(names):
        raise ValueError('report requires exactly the four bound images')
    for data in images.values():
        # Authentication and pixel decoding still belong to the caller/browser.
        if not _png(data):
            raise ValueError('report images must be PNG bytes')
    return source, preview


def _figure(viewport, images, title):
    uri = 'data:image/png;base64,' + base64.b64encode(images[viewport['screenshot']]).decode('ascii')
    label = f"{title} · {viewport['name'].capitalize()} · {viewport['width']} × {viewport['height']} px"
    cls = 'image-frame mobile-shot' if viewport['name'] == 'mobile' else 'image-frame'
    return (f'<figure><figcaption>{_e(label)}</figcaption><div class="{cls}">'
            f'<img src="{uri}" alt="{_e(label)}" width="{viewport["width"]}" '
            f'height="{viewport["height"]}"></div></figure>')


def _origin(current):
    origin = current.get('origin')
    if origin == 'local-remix':
        return 'LOCAL_REMIX - deterministic local remix; no model inference for this revision.'
    if origin == 'host-model' or (origin is None and (current.get('model') or current.get('provider'))):
        return 'MODEL - bounded layout generated through model inference; not model-authored HTML.'
    return 'Origin not recorded; model inference or local remix is not established.'


def _adjustments(current):
    if 'safety_adjustments' not in current:
        return ''
    values = current['safety_adjustments']
    entries = []
    if isinstance(values, list):
        for value in values:
            if isinstance(value, str):
                entries.append('<li>' + _e(value) + '</li>')
            elif isinstance(value, dict):
                entries.append('<li>' + _meta([
                    (key.replace('_', ' ').capitalize(), value[key])
                    for key in ('property', 'requested', 'applied', 'from', 'to', 'reason') if key in value
                ]) + '</li>')
    return '<h3>Recorded safety adjustments</h3><ul>' + ''.join(entries) + '</ul>' + (
        '' if entries else '<p>No safety adjustments recorded in this revision.</p>')


def _variant(record, current):
    section = current['section']
    output = '<h3>Current bounded properties</h3>' + _meta([(key.replace('_', ' ').capitalize(), section.get(key)) for key in _PROPS])
    if 'parent_revision' in current:
        parent_number = current['parent_revision']
        parent = next((r for r in record['revisions'] if r['number'] == parent_number), None)
        output += '<h3>Changes from parent revision ' + _e(parent_number) + '</h3>'
        if parent is None:
            output += '<p>Parent details unavailable; no property comparison claimed.</p>'
        else:
            rows = [(key, parent['section'].get(key), section.get(key)) for key in _PROPS
                    if parent['section'].get(key) != section.get(key)]
            output += ('<ul>' + ''.join(f'<li>{_e(k)}: <code>{_e(_shown(a))}</code> → <code>{_e(_shown(b))}</code></li>'
                                       for k, a, b in rows) + '</ul>') if rows else '<p>No bounded property changes.</p>'
    return output + _adjustments(current)


def _decision(record):
    decision = record.get('decision')
    output = ('<section class="card"><h2>Human review decision</h2>'
              '<p>This is a recorded human choice for the identified artifact, not deployment approval, '
              'a public attestation, or proof of production readiness.</p>')
    if decision is None:
        return output + '<p><strong>Not recorded.</strong> No endorsement is implied by this packet.</p></section>'
    return output + _meta([
        ('Revision', decision.get('revision')), ('Artifact SHA-256', decision.get('artifact_hash')),
        ('Verdict', decision.get('verdict')), ('Reason', decision.get('reason')),
        ('Check receipt signature', decision.get('verification_signature', 'Not recorded (legacy choice)')),
        *[(label, decision[key]) for key, label in (('decided_at', 'Decision timestamp'), ('recorded_at', 'Recorded timestamp')) if key in decision]
    ]) + '</section>'


def _review_trail(record):
    events = record.get('review_events', [])
    out = ['<section class="card"><h2>Historical review trail</h2><p>Not current export authority. '
           'These are retained signed observations and choices, not endorsement of the current proposal. '
           'Older already-discarded history cannot be reconstructed. Archived screenshots remain local; '
           'only the current four images are embedded in this packet.</p>']
    out.append('<h3>Candidate ledger</h3><p>Latest retained observations per revision, not current eligibility. '
               'Full event details follow; an absent entry does not establish that an older revision was never checked.</p><ul>')
    for rev in record['revisions']:
        selected = [e for e in events if e['payload']['revision'] == rev['number']]
        checks = next((e['payload'] for e in reversed(selected) if e['kind'] == 'verification'), None)
        choice = next((e['payload'] for e in reversed(selected) if e['kind'] == 'decision'), None)
        out.append('<li><strong>Revision ' + _e(rev['number']) + '</strong> · ' + _e(rev['section']['layout']) +
                   ' / ' + _e(rev['section']['spacing']) +
                   (' · ' + _e(', '.join(str(sum(c['status'] == s for c in checks['checks'])) + ' ' + s for s in ('pass', 'fail', 'unknown'))) if checks else ' · No retained checks') +
                   ('<p>' + _e(choice['verdict']) + ': ' + _e(choice['reason']) + '</p>' if choice else '<p>No retained choice.</p>') + '</li>')
    out.append('</ul>')
    if not events: return ''.join(out) + '<p>No audit events retained in this record.</p></section>'
    for event in events:
        p = event['payload']
        out.append('<details><summary>Event ' + _e(event['sequence']) + ' · Revision ' + _e(p['revision']) +
                   ' · ' + _e(event['kind']) + '</summary>')
        out.append(_meta([('Artifact SHA-256', p['artifact_hash']), ('Scope hash', p['contract_hash']),
                          ('Recorded into trail', event['recorded_at'])]))
        if event['kind'] == 'decision':
            out.append(_meta([('Verdict', p['verdict']), ('Reason', p['reason']), ('Choice recorded at', p['recorded_at'])]))
        else:
            out.append(_meta([('Browser checked at', p['checked_at']), ('Protocol', p.get('protocol', 1))]))
            out.append('<ul>' + ''.join('<li>' + _e(c['label']) + ': ' + _e(c['status']) + '</li>' for c in p['checks']) + '</ul>')
        out.append('</details>')
    return ''.join(out) + '</section>'


def render_report(record, images) -> bytes:
    """Render authenticated current evidence as a standalone UTF-8 review packet.

    ``images`` must contain exactly the source and current receipt's controlled
    desktop/mobile PNG basenames. Raises ``ValueError`` for missing, foreign or
    stale bindings. Inputs are never mutated, normalised or upgraded.
    """
    try:
        return _render(record, images).encode('utf-8')
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ValueError('report requires a complete current review record') from exc


def _render(record, images):
    current = record['revisions'][-1]
    receipt = record['verification']
    if type(current['number']) is not int or current['number'] < 1 or type(receipt['revision']) is not int:
        raise ValueError('report revision numbers must be positive integers')
    if receipt['revision'] != current['number'] or receipt['artifact_hash'] != current['artifact_hash']:
        raise ValueError('report receipt is not bound to the current artifact')
    source, preview = _bind_images(record, images, current, receipt)
    contract = record['contract']
    elements = {e['id']: e for e in source['desktop']['elements']}
    headline = elements[contract['headline_id']]['text']
    bodies = [elements[key]['text'] for key in contract['body_ids']]
    cta = elements[contract['cta_id']]
    if cta['text'] != contract['cta_text'] or cta['href'] != contract['cta_destination']:
        raise ValueError('report CTA is not bound to the source contract')
    checks = receipt['checks']
    counts = {status: sum(c['status'] == status for c in checks) for status in ('pass', 'fail', 'unknown')}
    if not checks or sum(counts.values()) != len(checks):
        raise ValueError('report check statuses are invalid')
    protocol = receipt.get('protocol', 1)
    out = [f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
           f'<meta http-equiv="Content-Security-Policy" content="{_e(_CSP)}">'
           '<meta name="viewport" content="width=device-width, initial-scale=1">'
           '<title>repager - private review packet</title><style>' + _CSS + '</style></head><body><main>',
           '<header><span class="brand">repager</span><span class="eyebrow">Private review packet<br>Evidence, not endorsement</span></header>',
           '<section class="intro"><div class="eyebrow">Text-only hero exploration</div><h1>A bounded proposal.<br>A clear review trail.</h1>'
           '<p class="lead">Review captured source evidence alongside one standalone hero proposal. '
           'Decide whether its exact copy, layout and destination merit further human review.</p>',
           _meta([('Audience', record.get('audience')), ('Goal', record.get('goal')),
                  ('Source title', record['source'].get('title')), ('Original source URL', record['source']['url']),
                  ('Captured at', record['source']['captured_at']), ('Current revision', current['number'])]), '</section>',
           '<aside class="notice"><strong>Different scope, not a like-for-like redesign.</strong> '
           'The original images show the source first screen, including any captured navigation, media or overlays. '
           'The proposal is a standalone TEXT-ONLY hero, not the original page or a repaired website. '
           'No performance deltas, conversion gains, or claim that the original site is fixed follow from this comparison. '
           'Source consent was not automatically bypassed by this report.</aside>',
           '<section class="card"><h2>Exact content in scope</h2><p class="small">Verbatim source-desktop selections bound by the current preservation contract. '
           'The destination is inert text; this packet does not contact the source.</p><h3>Headline</h3><div class="copy">' + _e(headline) + '</div>',
           '<h3>Body</h3><div class="copy">' + ''.join('<p>' + _e(body) + '</p>' for body in bodies) + '</div>',
           _meta([('CTA label', contract['cta_text']), ('CTA destination', contract['cta_destination']),
                  ('Contract approved at', contract.get('approved_at'))]), '</section>',
           '<section class="card"><h2>Before / proposal</h2><p class="small">Embedded recorded PNGs; the report itself does not render or recheck the implementation. '
           'Viewport dimensions below describe the captures, not your current display.</p>']
    for name in ('desktop', 'mobile'):
        out.append(f'<div class="comparison"><h3>{name.capitalize()} comparison</h3><div class="grid">' +
                   _figure(source[name], images, 'Before · original first screen') +
                   _figure(preview[name], images, 'After · standalone text-only hero') + '</div></div>')
    if counts['fail']:
        out.append('<aside class="notice"><strong>Review only - failed checks. Not eligible for implementation handoff.</strong> This passive report preserves failure evidence, not permission to use the implementation.</aside>')
    out.extend(['</section><section class="card"><h2>Current variant</h2><p class="break">' + _e(_origin(current)) + '</p>',
                _meta([('Revision created at', current.get('created_at')),
                       *[(label, current[key]) for key, label in (('model', 'Recorded model'), ('provider', 'Recorded provider'))
                         if key in current and current.get('origin') != 'local-remix']]),
                _variant(record, current), '</section>',
                '<section class="card"><h2>Recorded checks</h2>',
                '<p><strong>' + _e(len(checks)) + ' checks</strong> · Protocol ' + _e(protocol) +
                (' (legacy; not upgraded or re-run).' if protocol == 1 else ' (as recorded; not re-run by this report).') + '</p>',
                '<p>These statuses and details belong only to the current artifact and recorded viewports. '
                '<strong>Unknown is not pass.</strong> There is no general quality score.</p>',
                '<div class="counts">' + ''.join(f'<span class="pill {s}">{n} {s}</span>' for s, n in counts.items()) + '</div>',
                _meta([('Checked at', receipt.get('checked_at'))]),
                '<div class="table-wrap"><table><thead><tr><th scope="col">Check</th><th scope="col">Status</th><th scope="col">Recorded detail</th></tr></thead><tbody>'])
    for check in checks:
        status = check['status']  # Closed enum validated above; no dynamic CSS.
        detail = _e(check.get('detail', ''))
        for key in ('attempted_requests', 'denied_requests'):
            if key in check:
                detail += '<p>' + _e(key.replace('_', ' ').capitalize()) + ': ' + _e(check[key]) + '</p>'
        out.append('<tr><td>' + _e(check.get('label', check['id'])) + '<br><code>' + _e(check['id']) +
                   f'</code></td><td><span class="pill {status}">{status.upper()}</span></td><td class="break">' + detail + '</td></tr>')
    out.extend(['</tbody></table></div></section>', _decision(record), _review_trail(record),
                '<section class="card"><h2>Artifact identity &amp; provenance</h2>',
                _meta([('Review ID', record.get('id')), ('Revision', current['number']),
                       ('Artifact SHA-256', current['artifact_hash']),
                       ('Source hash', receipt.get('source_hash', (record.get('source_integrity') or {}).get('source_hash'))),
                       ('Contract hash', receipt.get('contract_hash', current.get('contract_hash'))),
                       ('Source captured at', record['source']['captured_at']), ('Checks recorded at', receipt.get('checked_at'))]),
                '<p class="small">Hashes identify bytes within this review trail. Local signatures are authenticated by the caller, '
                'not independently verified by this passive HTML. Neither hashes nor this packet establish independent trust or public attestation.</p></section>',
                '<section class="card"><h2>Limitations &amp; what is not proven</h2><ul>'])
    for label, limits in (('Source', record['source'].get('limitations', [])), ('Verification', receipt.get('limitations', []))):
        for limitation in limits:
            out.append('<li><strong>' + label + ':</strong> ' + _e(limitation) + '</li>')
    out.extend(['<li>First-screen evidence and bounded checks do not prove full-site behavior, semantic preservation, accessibility conformance, '
                'brand suitability, production readiness, performance, or conversion outcomes.</li>'
                '<li>Human visual, content, accessibility and legal review remains necessary. No deployment, source changes, '
                'active source contact or new verification is performed by this packet.</li></ul></section>',
                '<section class="card"><h2>How to use the handoff</h2><div class="grid"><div><h3>index.html - implementation</h3>'
                '<p>The standalone text-only hero artifact. Its SHA-256 above binds the recorded checks. It is not the source site.</p></div>'
                '<div><h3>review.html - review packet</h3><p>This self-contained, passive evidence document. '
                'Its embedded images are snapshots, not active previews. Open offline or print; no external assets, scripts, '
                'source-contact buttons or automatic fetches are included.</p></div></div>'
                '<p class="small">Keep the accompanying review.json, verification.json, PNGs and limitations with the handoff. '
                'A human review decision is a choice about this revision, not permission to deploy.</p></section>',
                '<footer>repager · Private, bounded exploration · Original site untouched</footer></main></body></html>'])
    return ''.join(out)
