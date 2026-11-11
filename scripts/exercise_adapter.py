"""Explicit real-browser evidence run. No models or automatic fixture fallback.

Pillow is required only for integration screenshot inspection. Default sandbox
stays on; --allow-no-sandbox is a trusted, explicit diagnostic opt-in.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from repager.browser import BrowserAdapter
from repager.renderer import render_section


def local_renderer_fixture():
    """Clearly synthetic source, not substituted for any failed live capture."""
    style = {'color': 'rgb(0, 0, 0)', 'background_color': 'rgb(255, 255, 255)',
             'font_size': '18px', 'font_family': 'sans-serif'}
    elements = []
    for index, (tag, text, href) in enumerate([
        ('h1', 'Local renderer integration fixture', None),
        ('p', 'A bounded local fixture, not captured source. ' + '& ' * 650, None),
        ('a', 'Keep reading', 'https://example.com/keep/'),
    ]):
        elements.append(dict(id=f'desktop-{index}', tag=tag, text=text, href=href,
                             rect=dict(x=0, y=index*50, width=300, height=40), style=style))
    source = dict(url='https://example.com/', title='LOCAL FIXTURE: not live source',
                  captured_at=datetime.now(timezone.utc).isoformat(), palette=['#ffffff', '#000000'],
                  limitations=['Synthetic source used solely to exercise the trusted renderer.'],
                  viewports=[dict(name='desktop', width=1440, height=900,
                                  screenshot='source-desktop.png', overflow=False, elements=elements)])
    spec = dict(headline_id='desktop-0', body_ids=['desktop-1'], cta_id='desktop-2',
                layout='stack', alignment='left', spacing='compact', background='#ffffff',
                foreground='#000000', accent='#000000', button_text='#ffffff')
    return render_section(spec, source)


def inspect_images(directory, report):
    from PIL import Image
    images = []
    for view in report['viewports']:
        file = directory / view['screenshot']
        with Image.open(file) as image:
            image.load()
            if image.size != (view['width'], view['height']):
                raise AssertionError(f'wrong screenshot dimensions: {file}')
            images.append(dict(path=str(file), width=image.width, height=image.height,
                               bytes=file.stat().st_size, format=image.format))
    return images


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='Explicit trusted destination for captured evidence')
    parser.add_argument('--executable-path', default=os.environ.get('REPAGER_CHROMIUM_PATH'),
                        help='Trusted Chromium path; defaults to REPAGER_CHROMIUM_PATH or Playwright browser')
    parser.add_argument('--allow-no-sandbox', action='store_true')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    adapter = BrowserAdapter(args.executable_path, timeout=90, allow_no_sandbox=args.allow_no_sandbox)
    summary = {'no_sandbox_opt_in': args.allow_no_sandbox, 'captures': [], 'previews': [], 'errors': []}
    for name, url in [('example', 'https://example.com'), ('iana', 'https://www.iana.org/help/example-domains')]:
        target = output / name
        try:
            report = adapter.capture(url, target)
            (target / 'source.json').write_text(json.dumps(report, indent=2))
            summary['captures'].append(dict(url=url, title=report['title'], images=inspect_images(target, report),
                                            elements=[len(v['elements']) for v in report['viewports']], palette=report['palette']))
        except Exception as exc:
            summary['errors'].append(dict(action='capture', url=url, error=str(exc)))
    html = local_renderer_fixture()
    if len(html.encode()) < 5000:
        raise AssertionError('renderer fixture must actually exceed 5 KB')
    hostile = ('<!doctype html><meta name="viewport" content="width=device-width"><body>'
               '<script>window.__repagerHostile=1;fetch("http://127.0.0.1/secret");'
               'new WebSocket("ws://127.0.0.1/");document.body.innerHTML="PWNED"</script>'
               '<img src="http://127.0.0.1/secret"><iframe src="https://example.com/"></iframe>'
               '<a href="https://example.com/keep/">Keep</a>')
    for name, content in [('local-renderer-fixture', html), ('malicious-local-fixture', hostile)]:
        target = output / name
        target.mkdir(parents=True, exist_ok=True)
        (target / 'fixture.html').write_text(content)
        try:
            report = adapter.verify(content, 'https://example.com/keep/', target)
            (target / 'verification.json').write_text(json.dumps(report, indent=2))
            summary['previews'].append(dict(label=name, html_bytes=len(content.encode()),
                                            checks=report['checks'], images=inspect_images(target, report)))
        except Exception as exc:
            summary['errors'].append(dict(action='verify', label=name, error=str(exc)))
    (output / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    if summary['errors']:
        return 1
    # Fixture results can legitimately fail visual checks; isolation must not.
    for preview in summary['previews']:
        for check in preview['checks']:
            if (check['id'].endswith('scripts-disabled') or check['id']=='preview-no-network') and check['status']!='pass':
                return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())