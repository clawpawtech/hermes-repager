"""Package an existing real MP4 into a private, network-free watch page.

This does not record or fabricate footage, transcode, authenticate, publish or
start a server. Serve the result only through an authenticated file surface.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
from pathlib import Path


def watch_page(video: bytes, *, workflow="full") -> str:
    if not 16 <= len(video) <= 40 * 1024 * 1024 or video[4:8] != b'ftyp':
        raise ValueError('Expected an existing MP4 between 16 bytes and 40 MiB')
    if workflow not in ('full', 'resume'): raise ValueError('Unknown workflow label')
    narrative = ('Resume an existing approved capture, retain earlier check evidence and a reason, create a local revision without inference, inspect history, then check and export. This run makes no new source capture or model call.'
                 if workflow == 'resume' else 'Capture a real page, approve exact copy and CTA, generate through Hermes, reject stale handoff, then check and export the current revision.')
    encoded = base64.b64encode(video).decode('ascii')
    digest = hashlib.sha256(video).hexdigest()
    assets = Path(__file__).resolve().parents[1] / 'dashboard' / 'brand'
    icon = 'data:image/svg+xml;base64,' + base64.b64encode((assets / 'favicon.svg').read_bytes()).decode('ascii')
    wordmark = (assets / 'wordmark.svg').read_text()
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; media-src data:; base-uri 'none'; form-action 'none'">
<link rel="icon" type="image/svg+xml" href="{icon}"><title>repager - private workflow demo</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#171816;color:#f3f0e7;font:17px/1.6 system-ui,sans-serif}}main{{max-width:1000px;margin:auto;padding:24px 16px}}.brand{{width:140px}}.brand svg{{display:block;width:100%;height:auto}}h1{{font-size:clamp(28px,5vw,42px);line-height:1.15}}video{{display:block;width:100%;height:auto;background:#000;border:1px solid #555}}p{{max-width:70ch}}code{{font-size:12px;overflow-wrap:anywhere}}small{{color:#c9c5ba}}a{{color:#ffab60}}</style></head>
<body><main><div class="brand">{wordmark}</div><h1>One change. Keep the evidence.</h1>
<p>Real repager workflow inside native Hermes dashboard. Tap Play below. No audio track.</p>
<video controls playsinline preload="metadata" aria-label="Real repager native dashboard workflow"><source type="video/mp4" src="data:video/mp4;base64,{encoded}">This browser cannot play the MP4. Use the separate authenticated download link in the chat.</video>
<p>{narrative}</p>
<p><small>Text-only hero proposal, not a full-site rebuild. No conversion uplift or complete accessibility claim. Container browser tests explicitly disabled Chromium's OS sandbox. This page embeds the real video bytes, makes no external requests and contains no scripts.</small></p>
<p><small>MP4 SHA-256: <code>{digest}</code></small></p>
</main></body></html>'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--workflow', choices=('full','resume'), default='full')
    args=parser.parse_args()
    if args.video.is_symlink() or not args.video.is_file():
        raise ValueError('Input must be a regular local MP4, not a symlink')
    if args.video.stat().st_size>40*1024*1024:
        raise ValueError('MP4 exceeds 40 MiB')
    html=watch_page(args.video.read_bytes(), workflow=args.workflow)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        stream.write(html)
    print(f'Private watch page written: {args.output} (no publication or auth changes)')

if __name__=='__main__':
    main()
