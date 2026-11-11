"""repager core data models and validation.

JSON-serialisable dicts (snake_case) only; no third-party dependencies.
Public surface used by the rest of the core:

* ``SourceSnapshot``   - shape written by :mod:`repager.browser`
* ``Finding``          - single evidence-backed observation
* ``SectionSpec``      - bounded, schema-enforced section layout (exact
  captured text is bound from the source by element *id*, never invented)
* ``Revision``         - immutable generated artifact
* ``Verification``     - revision-bound browser verification result
* ``ReviewRecord``     - the persisted review document

Validation functions return cleaned dicts or raise ``ValueError`` on
malformed input (oversized strings, bad enums, bad hex, path-like ids, ...).
"""

from __future__ import annotations

import re
import math
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "now_iso",
    "ALLOWED_NEUTRAL_COLORS",
    "validate_text",
    "validate_nonempty",
    "validate_bool",
    "validate_hex",
    "validate_enum",
    "validate_int",
    "validate_list",
    "validate_source",
    "validate_finding",

    "validate_verification",
    "validate_review",
    "validate_section_spec",
    "SECTION_SPEC_FULL_SCHEMA",
    "SECTION_SPEC_MODEL_SCHEMA",
]

#: Neutral colours always allowed even when the source palette is small.
ALLOWED_NEUTRAL_COLORS = frozenset({"#000000", "#ffffff"})

#: Hex colour: #RRGGBB
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_URL_SCHEME = re.compile(r"^https?://", re.IGNORECASE)
_CTA_FORBIDDEN_PREFIXES = ("javascript:", "mailto:", "vbscript:", "data:", "blob:")
_REVIEW_ID = re.compile(r"[0-9a-f]{32}\Z")

#: Alignment options.
_ALIGNMENTS = ("left", "center")

#: Review statuses, kept in a closed set by design.
_VALID_STATUSES = ("capturing", "reviewed", "approved", "generated", "verified", "failed")
_FINDING_KINDS = ("measurement", "judgment")
_LAYOUTS = ("stack", "split", "editorial", "spotlight")
_ALIGNMENTS = _ALIGNMENTS
_SPACINGS = ("compact", "comfortable")
_CHECK_STATUSES = ("pass", "fail", "unknown")


# --------------------------------------------------------------------------
# small validators
# --------------------------------------------------------------------------
def now_iso() -> str:
    """Current UTC time, ISO-8601 with timezone, e.g. 2026-11-06T12:00:00+00:00."""
    return datetime.now(timezone.utc).isoformat()


def validate_text(value: Any, label: str = "value", max_len: int = 2000) -> str:
    """Normalise a trimmed, length-bounded string."""
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    value = value.strip()
    if len(value) > max_len:
        raise ValueError(f"{label} exceeds {max_len} characters")
    return value


def validate_nonempty(value: Any, label: str = "value", max_len: int = 2000) -> str:
    """Normalise a trimmed, non-empty, length-bounded string."""
    v = validate_text(value, label, max_len)
    if v == "":
        raise ValueError(f"{label} must not be empty")
    return v


def validate_bool(value: Any, label: str = "value") -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value


def validate_hex(value: Any, label: str = "value") -> str:
    """Normalise a #RRGGBB colour to lowercase."""
    v = validate_text(value, label, 50)
    if not _HEX_COLOR.match(v):
        raise ValueError(f"{label} must be a 6-hex colour (#RRGGBB)")
    return v.lower()


def validate_enum(value: Any, label: str, enum: Sequence[str]) -> str:
    v = validate_text(value, label, 100)
    if v not in enum:
        raise ValueError(f"{label} must be one of {sorted(enum)}")
    return v


def validate_int(value: Any, label: str, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{label} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{label} must be <= {maximum}")
    return value


def validate_list(
    value: Any,
    label: str,
    item_validator: Callable[[Any, str], Any],
    max_items: int = 200,
    min_items: int = 0,
) -> List[Any]:
    """Validate every element of a list, returning a cleaned copy."""

    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    if len(value) > max_items:
        raise ValueError(f"{label} exceeds {max_items} items")
    if len(value) < min_items:
        raise ValueError(f"{label} must have at least {min_items} item(s)")
    out: List[Any] = []
    for i, item in enumerate(value):
        try:
            out.append(item_validator(item, f"{label}[{i}]"))
        except ValueError as exc:
            raise ValueError(f"{label}[{i}]: {exc}") from exc
    return out


# --------------------------------------------------------------------------
# source snapshot (produced by the browser adapter)
# --------------------------------------------------------------------------
_ALLOWED_ELEMENT_TAGS = (
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "a", "span", "div", "li",
    "strong", "em", "br", "img", "code", "pre", "blockquote", "button",
    "section", "article", "header", "footer", "nav",
)


def _validate_rect(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    result = {}
    for key in ('x', 'y', 'width', 'height'):
        number = value.get(key)
        if (isinstance(number, bool) or not isinstance(number, (int, float))
                or not math.isfinite(number) or abs(number) > 10000000
                or (key in ('width', 'height') and number < 0)):
            raise ValueError(f'{label}.{key} must be a finite DOM measurement')
        result[key] = number
    return result


def _validate_style(value: Any, label: str) -> Dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    out: Dict[str, str] = {}
    for key in ("color", "background_color", "font_size", "font_family"):
        if key in value:
            out[key] = validate_text(value[key], f"{label}.{key}", 300)
    return out


def _validate_element(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    eid = validate_nonempty(value.get("id"), f"{label}.id", 200)
    tag = validate_text(value.get("tag"), f"{label}.tag", 32).lower()
    if tag not in _ALLOWED_ELEMENT_TAGS:
        raise ValueError(f"{label}.tag is not a defined headline/content tag: {tag!r}")
    text = validate_text(value.get("text"), f"{label}.text", 4000)
    text = value['text']  # Captured copy is verbatim, including whitespace.
    href: Optional[str] = value.get("href")
    if href is not None:
        validate_text(href, f"{label}.href", 2048)
        # Keep unsupported destinations as evidence; only CTA selection permits HTTP(S).
    rect = _validate_rect(value.get("rect"), f"{label}.rect")
    style = _validate_style(value.get("style"), f"{label}.style")
    result = {"id": eid, "tag": tag, "text": text, "href": href, "rect": rect, "style": style}
    if "region" in value:
        result['region'] = validate_enum(value['region'], f'{label}.region', ('nav', 'hero', 'content'))
    if value.get('container_id') is not None:
        result['container_id'] = validate_nonempty(value['container_id'], f'{label}.container_id', 200)
    return result


def _validate_viewport(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    name = validate_enum(value.get("name"), f"{label}.name", ("desktop", "mobile"))
    width = validate_int(value.get("width"), f"{label}.width", minimum=1, maximum=4000)
    height = validate_int(value.get("height"), f"{label}.height", minimum=1, maximum=4000)
    screenshot = validate_nonempty(value.get("screenshot"), f"{label}.screenshot", 200)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.png', screenshot):
        raise ValueError(f"{label}.screenshot must be a bare basename, not a path")
    overflow = validate_bool(value.get("overflow"), f"{label}.overflow")
    elements = validate_list(value.get("elements", []), f"{label}.elements", _validate_element, 300)
    extra = {}
    if 'overflow_elements' in value:
        def offender(item, field):
            if not isinstance(item, dict):
                raise ValueError(f'{field} must be an object')
            return {'id': validate_nonempty(item.get('id'), field + '.id', 200),
                    'tag': validate_enum(item.get('tag'), field + '.tag', _ALLOWED_ELEMENT_TAGS),
                    'text': validate_text(item.get('text'), field + '.text', 400),
                    'rect': _validate_rect(item.get('rect'), field + '.rect'),
                    'in_hero': validate_bool(item.get('in_hero'), field + '.in_hero')}
        extra['overflow_elements'] = validate_list(value['overflow_elements'], label + '.overflow_elements', offender, 12)
    return {
        "name": name,
        "width": width,
        "height": height,
        "screenshot": screenshot,
        "overflow": overflow,
        "elements": elements,
        **extra,
    }


def validate_source(obj: Any) -> Dict[str, Any]:
    """Validate a browser-captured source snapshot; returns a cleaned dict."""
    if not isinstance(obj, dict):
        raise ValueError("source must be an object")
    url = validate_nonempty(obj.get("url"), "source.url", 2000)
    if not _URL_SCHEME.match(url):
        raise ValueError("source.url must be an absolute https:// URL")
    title = validate_text(obj.get("title"), "source.title", 4000)
    captured_at = obj.get("captured_at")
    if not isinstance(captured_at, str) or not captured_at.strip():
        raise ValueError("source.captured_at must be a non-empty ISO timestamp")
    viewports = validate_list(obj.get("viewports"), "source.viewports", _validate_viewport, 8)
    names = [v['name'] for v in viewports]
    ids = [e['id'] for v in viewports for e in v['elements']]
    if len(set(names)) != len(names) or len(set(ids)) != len(ids):
        raise ValueError('source has duplicate viewport names or element ids')
    palette = validate_list(obj.get("palette"), "source.palette", validate_hex, max_items=16, min_items=0)
    limitations = validate_list(
        obj.get("limitations"), "source.limitations", validate_text, max_items=50, min_items=0
    )
    return {
        "url": url,
        "title": title,
        "captured_at": captured_at,
        "viewports": viewports,
        "palette": palette,
        "limitations": limitations,
    }


# --------------------------------------------------------------------------
# findings
# --------------------------------------------------------------------------
def validate_finding(value: Any, index: str = "finding") -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{index} must be an object")
    return {
        "id": validate_nonempty(value.get("id"), f"{index}.id", 200),
        "title": validate_text(value.get("title"), f"{index}.title", 500),
        "observation": validate_text(value.get("observation"), f"{index}.observation", 4000),
        "recommendation": validate_text(value.get("recommendation"), f"{index}.recommendation", 500),
        "evidence_ids": validate_list(
            value.get("evidence_ids"), f"{index}.evidence_ids", validate_text, max_items=20
        ),
        "kind": validate_enum(value.get("kind"), f"{index}.kind", _FINDING_KINDS),
    }


# --------------------------------------------------------------------------
# revisions
# --------------------------------------------------------------------------
def _validate_revision(value: Any, index: str = "revision") -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{index} must be an object")
    number = validate_int(value.get("number"), f"{index}.number", minimum=1)
    filename = validate_nonempty(value.get("html_file"), f"{index}.html_file", 500)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.html', filename):
        raise ValueError('revision.html_file must be a controlled HTML basename')
    if not re.fullmatch(r'[0-9a-f]{64}', str(value.get('artifact_hash', ''))):
        raise ValueError('revision.artifact_hash must be SHA256 hex')
    validate_text(value.get("instruction"), f"{index}.instruction", 2000)
    section = value.get("section")
    if section is not None:
        validate_section_spec(section)
    if value.get("model") is not None:
        validate_text(value.get("model"), f"{index}.model", 200)
    if value.get("provider") is not None:
        validate_text(value.get("provider"), f"{index}.provider", 200)
    extra = {}
    if 'origin' in value:
        extra['origin'] = validate_enum(value['origin'], index + '.origin', ('host-model', 'local-remix'))
    if 'parent_revision' in value:
        extra['parent_revision'] = validate_int(value['parent_revision'], index + '.parent_revision', 1, 50)
    if 'safety_adjustments' in value:
        extra['safety_adjustments'] = validate_list(value['safety_adjustments'], index + '.safety_adjustments', validate_text, 4)
    if 'contract_snapshot' in value:
        if not isinstance(value['contract_snapshot'], dict):
            raise ValueError('revision.contract_snapshot must be an object')
        extra['contract_snapshot'] = value['contract_snapshot']
    return {
        **extra,
        "number": number,
        "created_at": value.get("created_at") or now_iso(),
        "artifact_hash": value.get("artifact_hash") or "",
        "html_file": value["html_file"],
        "section": section if section is not None else {},
        "instruction": value.get("instruction", ""),
        "model": value.get("model"),
        "provider": value.get("provider"),
        "contract_hash": value.get('contract_hash'),
        "signature": value.get('signature'),
    }


# --------------------------------------------------------------------------
# verification
# --------------------------------------------------------------------------
def _validate_check(value: Any, index: str = "check") -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{index} must be an object")
    status = value.get("status")
    if status not in _CHECK_STATUSES:
        raise ValueError(f"{index}.status must be one of {sorted(_CHECK_STATUSES)}")
    result: Dict[str, Any] = {
        "id": validate_nonempty(value.get("id"), f"{index}.id", 100),
        "label": validate_text(value.get("label"), f"{index}.label", 500),
        "status": status,
        "detail": validate_text(value.get("detail"), f"{index}.detail", 2000),
    }
    for key in ('attempted_requests', 'denied_requests'):
        if key in value:
            result[key] = validate_int(value[key], f'{index}.{key}', minimum=0)
    return result


def _validate_preview_viewport(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f'{label} must be an object')
    result = _validate_viewport(dict(value, overflow=value.get('overflow', False), elements=[]), label)
    result.pop('elements')
    if 'overflow' not in value:
        result.pop('overflow')
    return result


def validate_verification(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("verification must be an object")
    revision = validate_int(value.get("revision"), "verification.revision", minimum=1)
    artifact_hash = value.get("artifact_hash")
    if not isinstance(artifact_hash, str) or not re.fullmatch(r'[0-9a-f]{64}', artifact_hash):
        raise ValueError("verification.artifact_hash must be a 64-char sha256 hex")
    checks = validate_list(value.get("checks"), "verification.checks", _validate_check, max_items=100, min_items=1)
    if len({c['id'] for c in checks}) != len(checks):
        raise ValueError('verification check ids must be unique')
    viewports = validate_list(value.get("viewports"), "verification.viewports", _validate_preview_viewport, max_items=8)
    limitations = validate_list(
        value.get("limitations"), "verification.limitations", validate_text, max_items=50
    )
    return {
        **({"protocol": validate_int(value["protocol"], "verification.protocol", 1, 2)} if "protocol" in value else {}),
        "revision": revision,
        "artifact_hash": artifact_hash,
        "checked_at": value.get("checked_at") or now_iso(),
        "contract_hash": value.get('contract_hash'),
        "source_hash": value.get('source_hash'),
        "image_hashes": value.get('image_hashes', {}),
        "signature": value.get('signature'),
        "checks": checks,
        "viewports": viewports,
        "limitations": limitations,
    }


# --------------------------------------------------------------------------
# section spec (template for the LLM structured output)
# --------------------------------------------------------------------------
_ALIGNMENTS = ("left", "center")

SECTION_SPEC_FULL_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "description": "Bounded repager section layout: text content is bound from the source snapshot by element id; "
                   "layout/theme values must be chosen from the source palette plus neutral black/white.",
    "properties": {
        "headline_id": {"type": "string", "minLength": 1},
        "body_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8},
        "cta_id": {"type": "string", "minLength": 1},
        "layout": {"type": "string", "enum": list(_LAYOUTS)},
        "alignment": {"type": "string", "enum": list(_ALIGNMENTS)},
        "spacing": {"type": "string", "enum": list(_SPACINGS)},
        "background": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
        "foreground": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
        "accent": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
        "button_text": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
        "evidence_ids": {"type": "array", "items": {"type": "string"}, "minItems": 0, "maxItems": 20},
    },
    "required": ["headline_id", "body_ids", "cta_id", "layout", "alignment", "spacing",
                 "background", "foreground", "accent", "button_text"],
    "additionalProperties": False,
}

SECTION_SPEC_MODEL_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "description": "Layout/theme settings chosen by the model. The model chooses evidence ids and bound layout "
                   "settings only; exact copy text is bound from the source snapshot by id and may never be "
                   "invented. Button destination (cta_id) and text are bound by the approved contract.",
    "properties": {
        "layout": {"type": "string", "enum": list(_LAYOUTS)},
        "alignment": {"type": "string", "enum": list(_ALIGNMENTS)},
        "spacing": {"type": "string", "enum": list(_SPACINGS)},
        "background": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
        "foreground": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
        "accent": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
        "button_text": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
        "evidence_ids": {"type": "array", "items": {"type": "string"}, "minItems": 0, "maxItems": 20},
    },
    "required": ["layout", "alignment", "spacing", "background", "foreground", "accent", "button_text"],
    "additionalProperties": False,
}


def validate_section_spec(obj: Any, *, allow_partial: bool = False) -> Dict[str, Any]:
    """Validate a section spec; when ``allow_partial`` is true only the keys the
    model may choose are validated (headline/body/cta ids are bound by the
    service from the source snapshot)."""
    if not isinstance(obj, dict):
        raise ValueError("section spec must be an object")
    schema = SECTION_SPEC_MODEL_SCHEMA if allow_partial else SECTION_SPEC_FULL_SCHEMA
    missing = set(schema['required']) - obj.keys()
    extra = obj.keys() - schema['properties'].keys()
    if missing:
        raise ValueError(f'section spec missing required keys: {sorted(missing)}')
    if extra:
        raise ValueError(f'section spec additional properties forbidden: {sorted(extra)}')
    if allow_partial:
        layout = validate_enum(obj.get("layout"), "section.layout", _LAYOUTS)
        alignment = validate_enum(obj.get("alignment"), "section.alignment", _ALIGNMENTS)
        spacing = validate_enum(obj.get("spacing"), "section.spacing", _SPACINGS)
        background = validate_hex(obj.get("background"), "section.background")
        foreground = validate_hex(obj.get("foreground"), "section.foreground")
        accent = validate_hex(obj.get("accent"), "section.accent")
        button_text = validate_hex(obj.get("button_text"), "section.button_text")
        evidence_ids = validate_list(obj.get("evidence_ids", []), "section.evidence_ids", validate_nonempty, max_items=20)
        return {
            "layout": layout,
            "alignment": alignment,
            "spacing": spacing,
            "background": background,
            "foreground": foreground,
            "accent": accent,
            "button_text": button_text,
            "evidence_ids": evidence_ids,
        }
    headline_id = validate_nonempty(obj.get("headline_id"), "section.headline_id", 200)
    body_ids = validate_list(obj.get("body_ids"), "section.body_ids", validate_nonempty, max_items=8, min_items=1)
    cta_id = validate_nonempty(obj.get("cta_id"), "section.cta_id", 200)
    layout = validate_enum(obj.get("layout"), "section.layout", _LAYOUTS)
    alignment = validate_enum(obj.get("alignment"), "section.alignment", _ALIGNMENTS)
    spacing = validate_enum(obj.get("spacing"), "section.spacing", _SPACINGS)
    background = validate_hex(obj.get("background"), "section.background")
    foreground = validate_hex(obj.get("foreground"), "section.foreground")
    accent = validate_hex(obj.get("accent"), "section.accent")
    button_text = validate_hex(obj.get("button_text"), "section.button_text")
    evidence_ids = validate_list(obj.get("evidence_ids", []), "section.evidence_ids", validate_nonempty, max_items=20)
    missing = [k for k in SECTION_SPEC_FULL_SCHEMA["required"] if k not in obj]
    if missing:
        raise ValueError(f"section spec is missing required keys: {sorted(missing)}")
    return {
        "headline_id": headline_id,
        "body_ids": body_ids,
        "cta_id": cta_id,
        "layout": layout,
        "alignment": alignment,
        "spacing": spacing,
        "background": background,
        "foreground": foreground,
        "accent": accent,
        "button_text": button_text,
        "evidence_ids": evidence_ids,
    }


# --------------------------------------------------------------------------
# review record
# --------------------------------------------------------------------------
def validate_review(obj: Any) -> Dict[str, Any]:
    """Validate and normalise a full review record (canonical shape for storage)."""
    if not isinstance(obj, dict):
        raise ValueError("review must be an object")
    rid = obj.get("id")
    if not isinstance(rid, str) or not _REVIEW_ID.match(rid):
        raise ValueError("review.id must be a 32-hex UUID")
    status = obj.get("status")
    if status not in _VALID_STATUSES:
        raise ValueError(f"review.status must be one of {sorted(_VALID_STATUSES)}")
    validate_text(obj.get("audience"), "review.audience", 400)
    validate_text(obj.get("goal"), "review.goal", 400)
    source = obj.get("source")
    if source is not None:
        source = validate_source(source)
    findings = validate_list(obj.get("findings"), "review.findings", validate_finding, max_items=40, min_items=0)
    ids = [f["id"] for f in findings]
    if len(set(ids)) != len(ids):
        raise ValueError("review.findings contains duplicate ids")
    contract = obj.get("contract")
    if contract is not None:
        if not isinstance(contract, dict):
            raise ValueError("review.contract must be an object")
        if not isinstance(contract.get("finding_id"), str) or not contract["finding_id"]:
            raise ValueError("review.contract.finding_id is required")
        validate_bool(contract.get("preserve_copy"), "review.contract.preserve_copy")
        validate_bool(contract.get("preserve_destination"), "review.contract.preserve_destination")
        if not isinstance(contract.get("approved_at"), str) or not contract["approved_at"]:
            raise ValueError("review.contract.approved_at is required")
        if contract.get("cta_id") is not None:
            validate_nonempty(contract["cta_id"], "review.contract.cta_id")
    revisions = validate_list(obj.get("revisions"), "review.revisions", _validate_revision, max_items=50)
    for i, rev in enumerate(revisions, start=1):
        if rev["number"] != i:
            raise ValueError("review.revisions must be numbered sequentially from 1")
    verification = obj.get("verification")
    if verification is not None:
        verification = validate_verification(verification)
    if obj.get("error") is not None and not isinstance(obj["error"], str):
        raise ValueError("review.error must be a string")
    extra = {}
    if 'integrity_version' in obj:
        extra['integrity_version'] = validate_int(obj['integrity_version'], 'review.integrity_version', 1, 1)
    if 'review_events' in obj:
        events = obj['review_events']
        if not isinstance(events, list) or len(events) > 500:
            raise ValueError('review.review_events must contain at most 500 entries')
        for sequence, event in enumerate(events, 1):
            if not isinstance(event, dict) or event.get('sequence') != sequence or type(event.get('sequence')) is not int:
                raise ValueError('review event sequence must be contiguous')
            validate_enum(event.get('kind'), 'event.kind', ('verification', 'decision'))
            validate_nonempty(event.get('recorded_at'), 'event.recorded_at', 100)
            if event.get('review_id') != rid or not isinstance(event.get('payload'), dict):
                raise ValueError('review event identity/payload is invalid')
            if not re.fullmatch(r'[0-9a-f]{64}', str(event.get('signature', ''))):
                raise ValueError('review event signature must be SHA256 hex')
            # Preserve sealed payload bytes/optional legacy fields exactly.
            if event['kind'] == 'verification': validate_verification(event['payload'])
        extra['review_events'] = events
    if 'decision' in obj:
        d = obj['decision']
        if d is not None:
            if not isinstance(d, dict):
                raise ValueError('review.decision must be an object')
            validate_int(d.get('revision'), 'decision.revision', 1, 50)
            validate_enum(d.get('verdict'), 'decision.verdict', ('prefer', 'reject', 'undecided'))
            validate_nonempty(d.get('reason'), 'decision.reason', 500)
            for key in ('artifact_hash', 'contract_hash', 'signature'):
                if not re.fullmatch(r'[0-9a-f]{64}', str(d.get(key, ''))):
                    raise ValueError(f'decision.{key} must be SHA256 hex')
        extra['decision'] = d
    return {
        **extra,
        "id": rid,
        "version": validate_int(obj.get('version', 1), 'review.version', minimum=1),
        "status": status,
        "created_at": obj.get("created_at") or now_iso(),
        "updated_at": obj.get("updated_at") or now_iso(),
        "audience": obj["audience"],
        "goal": obj["goal"],
        "source": source,
        "source_integrity": obj.get('source_integrity'),
        "findings": findings,
        "contract": contract,
        "revisions": revisions,
        "verification": verification,
        "error": obj.get("error"),
    }
