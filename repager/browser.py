"""Fresh local Chromium bridge. No downloads, inherited secrets, or fallback data.

Source network is mediated by a numeric-address-pinning local proxy. This is
application-level defense, not an OS network sandbox. No-sandbox mode requires
an explicit trusted constructor argument and is unsuitable for hostile pages
without separate OS/container isolation.
"""
from __future__ import annotations

import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
from urllib.parse import urlsplit

MAX_INPUT_LENGTH = 2048
from .limits import MAX_HTML_BYTES


def is_public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
        if not address.is_global or address.is_multicast or address.is_reserved:
            return False
        if isinstance(address, ipaddress.IPv4Address):
            return address not in ipaddress.ip_network('192.0.0.0/24')
        return (address in ipaddress.ip_network('2000::/3')
                and address not in ipaddress.ip_network('2001::/23')
                and address not in ipaddress.ip_network('2002::/16')
                and address not in ipaddress.ip_network('3fff::/20'))
    except ValueError:
        return False


def _parse_url(value: str) -> str:
    if (not isinstance(value, str) or not value
            or len(value.encode('utf-8')) > MAX_INPUT_LENGTH
            or re.search(r'[\x00-\x20\x7f\\]', value)
            or re.search(r'%(?:0[0-9a-f]|1[0-9a-f]|7f)', value, re.I)):
        raise ValueError('unsafe URL')
    match = re.match(r'^(https?)://([^/?#]+)(?:[/?#]|$)', value, re.I)
    if not match or re.search(r'[@%]', match[2]):
        raise ValueError('unsafe URL authority')
    parts = urlsplit(value)
    host = parts.hostname
    authority = re.fullmatch(r'(\[[^\]]+\]|[^:]+)(?::(\d+))?', match[2])
    if not host or not authority or (authority[2] and authority[2] != ('443' if parts.scheme == 'https' else '80')):
        raise ValueError('nonstandard port or malformed host')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        # Reject browser-normalized numeric forms before consulting a resolver.
        if (re.fullmatch(r'[0-9.]+', host) or re.search(r'(^|\.)0x[0-9a-f]+($|\.)', host, re.I)
                or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,62}', host, re.I)):
            raise ValueError('invalid hostname')
    else:
        if not is_public_ip(str(address)):
            raise ValueError('nonpublic IP')
    return host


def validate_public_host(url: str) -> str:
    host = _parse_url(url)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        records = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        if not records or any(not is_public_ip(str(record[4][0])) for record in records):
            raise ValueError('host resolves to nonpublic addresses')
    return host


def is_valid_http_url(url: str) -> bool:
    try:
        validate_public_host(url)
        return True
    except (ValueError, OSError, UnicodeError):
        return False


def _worker_process_groups(pid: int) -> set[int]:
    """Include detached Chromium groups before terminating the worker (Linux).

    Playwright creates a new browser process group. Killing only Node's group
    is insufficient. Inspect PPIDs, not command lines or process environments.
    """
    groups = {pid}
    records = {}
    procfs = Path('/proc')
    if procfs.is_dir():
        for entry in procfs.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
                records[int(entry.name)] = (int(fields[1]), int(fields[2]))
            except (OSError, ValueError, IndexError):
                continue
        descendants = {pid}
        while True:
            found = {child for child, (parent, _) in records.items() if parent in descendants}
            if found <= descendants:
                break
            descendants |= found
        groups |= {records[child][1] for child in descendants if child in records}
    return groups - {os.getpgrp()}


def _signal_groups(groups: set[int], sig: int) -> None:
    for group in groups:
        try:
            os.killpg(group, sig)
        except ProcessLookupError:
            pass


class BrowserAdapter:
    def __init__(self, executable_path: str | None = None, timeout: int = 90,
                 allow_no_sandbox: bool = False, temp_dir: str | None = None):
        if executable_path is not None and not isinstance(executable_path, str):
            raise TypeError('executable_path must be a trusted path string')
        if type(timeout) is not int or timeout <= 0:
            raise TypeError('timeout must be a positive integer')
        if type(allow_no_sandbox) is not bool:
            raise TypeError('allow_no_sandbox must be a trusted boolean')
        self.executable_path = executable_path
        self.timeout = timeout
        self.allow_no_sandbox = allow_no_sandbox
        if temp_dir is not None and (not isinstance(temp_dir, str) or not Path(temp_dir).is_absolute() or len(os.fsencode(temp_dir)) > 50):
            raise ValueError('browser_temp_dir must be an absolute trusted path of at most 50 bytes for Chromium Unix sockets')
        self.temp_dir = temp_dir
        self._node = shutil.which('node') or '/usr/bin/node'
        self._worker = Path(__file__).resolve().parent / 'browser' / 'worker.mjs'

    def _spawn_worker(self, action: str, payload: dict) -> dict:
        # Deliberately no NODE_OPTIONS, proxies, API keys, or auth environment.
        allowed = ('PATH', 'HOME', 'TMPDIR', 'LD_LIBRARY_PATH', 'SYSTEMROOT')
        env = {key: os.environ[key] for key in allowed if key in os.environ}
        if self.temp_dir is not None:
            scratch = Path(self.temp_dir)
            if scratch.is_symlink():
                raise ValueError('browser_temp_dir must not be a symlink')
            scratch.mkdir(parents=True, exist_ok=True, mode=0o700)
            env['TMPDIR'] = self.temp_dir
        if len(os.fsencode(env.get('TMPDIR', ''))) > 50:
            raise RuntimeError('Chromium Unix socket path would be too long. Configure repager browser_temp_dir to a short trusted scratch directory (at most 50 bytes).')
        proc = subprocess.Popen([self._node, str(self._worker)], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env, start_new_session=True)
        try:
            stdout, _ = proc.communicate(json.dumps(payload).encode(), timeout=self.timeout)
        except subprocess.TimeoutExpired:
            groups = _worker_process_groups(proc.pid)
            _signal_groups(groups, signal.SIGTERM)
            try:
                proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            finally:
                _signal_groups(groups, signal.SIGKILL)
                proc.communicate()
            raise TimeoutError(f'browser worker timed out after {self.timeout}s') from None
        if proc.returncode:
            # Worker diagnostics are fixed codes only; don't expose source URLs/HTML.
            raise RuntimeError(f'browser worker failed ({proc.returncode}); capture/verification unavailable')
        if len(stdout) > 8 * 1024 * 1024:
            raise RuntimeError('browser worker response exceeds limit')
        try:
            result = json.loads(stdout)
        except (ValueError, UnicodeError) as exc:
            raise RuntimeError('browser worker returned invalid JSON') from exc
        if not isinstance(result, dict):
            raise RuntimeError('browser worker response must be an object')
        return result

    def _run(self, action, output_dir, **values):
        output = Path(output_dir).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        # Caller owns this trusted directory. Never follow a preexisting screenshot symlink.
        for name in ('desktop', 'mobile'):
            target = output / f'{"source" if action == "capture" else "preview"}-{name}.png'
            if target.is_symlink():
                raise ValueError('screenshot target must not be a symlink')
        payload = dict(action=action, output_dir=str(output), executable_path=self.executable_path,
                       timeout=self.timeout, allow_no_sandbox=self.allow_no_sandbox, **values)
        return self._spawn_worker(action, payload)

    def capture(self, url: str, output_dir: Path) -> dict:
        _parse_url(url)  # DNS policy executes only inside the killable, timed worker/proxy
        return self._run('capture', output_dir, url=url)

    def verify(self, html: str, expected_cta: str, output_dir: Path, *, expected_copy=None) -> dict:
        if not isinstance(html, str) or not html or len(html.encode('utf-8')) > MAX_HTML_BYTES:
            raise ValueError('html must be nonempty and at most 128 KiB')
        _parse_url(expected_cta)  # syntax only: previews never need DNS/network
        return self._run('verify', output_dir, html=html, expected_cta=expected_cta,
                         expected_copy=expected_copy)