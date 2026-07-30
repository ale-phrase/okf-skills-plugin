#!/usr/bin/env python3
"""Small OKF v0.2 validator and bookkeeping CLI."""

from __future__ import annotations

import argparse
import codecs
import json
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlsplit

try:
    import yaml
except ImportError:  # Reported by main with an actionable message.
    yaml = None


START = "<!-- okf:auto-index:start -->"
END = "<!-- okf:auto-index:end -->"
DELIMITER = re.compile(r"(?m)^---[ \t]*(?:\r?\n|$)")
LINK = re.compile(r"(?<!!)\[[^\]]+\]\((<[^>]+>|[^)\s]+)(?:\s+[^)]*)?\)")
DATE_HEADING = re.compile(r"(?m)^## (\d{4}-\d{2}-\d{2})[ \t]*$")
FOOTNOTE = re.compile(r"\[\^([^\]]+)\]")
ACTOR = re.compile(r"^(?:human:[^\s:]+|process:[^\s:]+|[^\s/]+/[^\s/]+)$")
STATUSES = {"draft", "stable", "deprecated"}


@dataclass(order=True)
class Issue:
    severity: str
    code: str
    path: str
    message: str


def require_yaml() -> None:
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required. Install okf/requirements.txt into this Python environment."
        )


def read_utf8(path: Path) -> tuple[str, bool]:
    data = path.read_bytes()
    bom = data.startswith(codecs.BOM_UTF8)
    try:
        return data.decode("utf-8-sig"), bom
    except UnicodeDecodeError as exc:
        raise ValueError(f"not valid UTF-8: {exc}") from exc


def write_utf8(path: Path, text: str, bom: bool = False) -> None:
    path.write_bytes((codecs.BOM_UTF8 if bom else b"") + text.encode("utf-8"))


def split_frontmatter(text: str) -> tuple[str, str, int, int, int] | None:
    matches = list(DELIMITER.finditer(text, 0))
    if not matches or matches[0].start() != 0 or len(matches) < 2:
        return None
    first, second = matches[:2]
    return text[first.end() : second.start()], text[second.end() :], first.end(), second.start(), second.end()


def parse_yaml(raw: str) -> dict:
    require_yaml()
    value = yaml.safe_load(raw) if raw.strip() else {}
    if not isinstance(value, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return value


def iso_datetime(value: object) -> bool:
    if isinstance(value, datetime):
        return True
    if isinstance(value, date) or not isinstance(value, str) or "T" not in value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def iso_date(value: object) -> bool:
    if isinstance(value, datetime):
        return False
    if isinstance(value, date):
        return True
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def actor(value: object) -> bool:
    return isinstance(value, str) and bool(ACTOR.fullmatch(value.strip()))


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def add(issues: list[Issue], severity: str, code: str, path: str, message: str) -> None:
    issues.append(Issue(severity, code, path, message))


def validate_window(value: object, name: str, code: str, issues: list[Issue]) -> None:
    if not isinstance(value, dict):
        add(issues, "warning", code, name, "usage_window should be a {from, to} mapping")
        return
    start, end = value.get("from"), value.get("to")
    if not iso_date(start) or not iso_date(end):
        add(issues, "warning", code, name, "usage_window from and to should be YYYY-MM-DD dates")
    elif str(start) > str(end):
        add(issues, "warning", code, name, "usage_window from should not be after to")


def validate_actor_field(value: object, name: str, code: str, issues: list[Issue]) -> None:
    if not actor(value):
        add(
            issues,
            "warning",
            code,
            name,
            "actor should use producer/version, human:<id>, or process:<id>",
        )


def validate_optional_frontmatter(
    meta: dict, body: str, name: str, issues: list[Issue]
) -> None:
    generated = meta.get("generated")
    if generated is None:
        if "timestamp" in meta:
            if not iso_datetime(meta["timestamp"]):
                add(
                    issues,
                    "warning",
                    "concept.timestamp",
                    name,
                    "legacy timestamp should be an ISO 8601 datetime",
                )
            else:
                add(
                    issues,
                    "warning",
                    "concept.timestamp.legacy",
                    name,
                    "timestamp is a v0.1 fallback; v0.2 uses generated.at",
                )
    elif not isinstance(generated, dict):
        add(issues, "warning", "concept.generated", name, "generated should be a mapping")
    else:
        validate_actor_field(generated.get("by"), name, "concept.generated.by", issues)
        if "at" not in generated or not iso_datetime(generated["at"]):
            add(
                issues,
                "warning",
                "concept.generated.at",
                name,
                "generated.at should be an ISO 8601 datetime",
            )

    verified = meta.get("verified")
    if verified is not None:
        events = [verified] if isinstance(verified, dict) else verified
        if not isinstance(events, list) or not events:
            add(
                issues,
                "warning",
                "concept.verified",
                name,
                "verified should be a mapping or non-empty list of mappings",
            )
        else:
            for index, event in enumerate(events):
                if not isinstance(event, dict):
                    add(
                        issues,
                        "warning",
                        "concept.verified",
                        name,
                        f"verified[{index}] should be a mapping",
                    )
                    continue
                validate_actor_field(
                    event.get("by"), name, f"concept.verified[{index}].by", issues
                )
                if not iso_datetime(event.get("at")):
                    add(
                        issues,
                        "warning",
                        f"concept.verified[{index}].at",
                        name,
                        f"verified[{index}].at should be an ISO 8601 datetime",
                    )

    if "status" in meta and meta["status"] not in STATUSES:
        add(
            issues,
            "warning",
            "concept.status",
            name,
            "status should be draft, stable, or deprecated",
        )
    if "stale_after" in meta and not iso_date(meta["stale_after"]):
        add(
            issues,
            "warning",
            "concept.stale_after",
            name,
            "stale_after should be a YYYY-MM-DD date",
        )

    sources = meta.get("sources")
    source_ids: set[str] = set()
    if sources is not None:
        if not isinstance(sources, list):
            add(issues, "warning", "concept.sources", name, "sources should be a list")
        else:
            for index, source in enumerate(sources):
                if not isinstance(source, dict):
                    add(
                        issues,
                        "warning",
                        "concept.sources",
                        name,
                        f"sources[{index}] should be a mapping",
                    )
                    continue
                resource = source.get("resource")
                if not isinstance(resource, str) or not resource.strip():
                    add(
                        issues,
                        "warning",
                        f"concept.sources[{index}].resource",
                        name,
                        f"sources[{index}].resource should be a non-empty string",
                    )
                source_id = source.get("id")
                if source_id is not None:
                    if not isinstance(source_id, str) or not source_id.strip():
                        add(
                            issues,
                            "warning",
                            f"concept.sources[{index}].id",
                            name,
                            f"sources[{index}].id should be a non-empty string",
                        )
                    elif source_id in source_ids:
                        add(
                            issues,
                            "warning",
                            "concept.sources.id",
                            name,
                            f"duplicate source id: {source_id}",
                        )
                    else:
                        source_ids.add(source_id)
                if "author" in source and (
                    not isinstance(source["author"], str) or not source["author"].strip()
                ):
                    add(
                        issues,
                        "warning",
                        f"concept.sources[{index}].author",
                        name,
                        f"sources[{index}].author should be a non-empty actor string",
                    )
                if "usage_count" in source and (
                    isinstance(source["usage_count"], bool)
                    or not isinstance(source["usage_count"], (int, float))
                    or source["usage_count"] < 0
                ):
                    add(
                        issues,
                        "warning",
                        f"concept.sources[{index}].usage_count",
                        name,
                        f"sources[{index}].usage_count should be a non-negative number",
                    )
                if "last_modified" in source and not iso_date(source["last_modified"]):
                    add(
                        issues,
                        "warning",
                        f"concept.sources[{index}].last_modified",
                        name,
                        f"sources[{index}].last_modified should be a YYYY-MM-DD date",
                    )
                if "usage_window" in source:
                    validate_window(
                        source["usage_window"],
                        name,
                        f"concept.sources[{index}].usage_window",
                        issues,
                    )

    if "usage_window" in meta:
        validate_window(meta["usage_window"], name, "concept.usage_window", issues)

    footnotes = set(FOOTNOTE.findall(body))
    for label in sorted(footnotes - source_ids):
        add(
            issues,
            "warning",
            "concept.source_attribution",
            name,
            f"footnote {label!r} has no matching sources[].id",
        )
    if sources is None and re.search(r"(?mi)^#\s+Citations\s*$", body):
        add(
            issues,
            "warning",
            "concept.citations.legacy",
            name,
            "# Citations is a v0.1 fallback; v0.2 uses sources and keyed footnotes",
        )

    if meta.get("type") == "Attested Computation":
        if not isinstance(meta.get("runtime"), str) or not meta["runtime"].strip():
            add(
                issues,
                "warning",
                "concept.computation.runtime",
                name,
                "Attested Computation should declare a non-empty runtime",
            )
        parameters = meta.get("parameters")
        if parameters is not None:
            if not isinstance(parameters, list):
                add(
                    issues,
                    "warning",
                    "concept.computation.parameters",
                    name,
                    "parameters should be a list",
                )
            else:
                for index, parameter in enumerate(parameters):
                    if (
                        not isinstance(parameter, dict)
                        or not isinstance(parameter.get("name"), str)
                        or not parameter["name"].strip()
                        or not isinstance(parameter.get("type"), str)
                        or not parameter["type"].strip()
                        or not isinstance(parameter.get("required"), bool)
                    ):
                        add(
                            issues,
                            "warning",
                            f"concept.computation.parameters[{index}]",
                            name,
                            f"parameters[{index}] should contain name, type, and boolean required",
                        )
        if "computation" in meta and (
            not isinstance(meta["computation"], str) or not meta["computation"].strip()
        ):
            add(
                issues,
                "warning",
                "concept.computation.path",
                name,
                "computation should be a non-empty path string",
            )
        for field in ("executor", "attester"):
            value = meta.get(field)
            if value is None:
                continue
            if not isinstance(value, dict):
                add(
                    issues,
                    "warning",
                    f"concept.computation.{field}",
                    name,
                    f"{field} should be a mapping",
                )
                continue
            if not isinstance(value.get("resource"), str) or not value["resource"].strip():
                add(
                    issues,
                    "warning",
                    f"concept.computation.{field}.resource",
                    name,
                    f"{field}.resource should be a non-empty path string",
                )
            if field == "executor" and "receipt" in value and (
                not isinstance(value["receipt"], list)
                or not all(isinstance(item, str) and item for item in value["receipt"])
            ):
                add(
                    issues,
                    "warning",
                    "concept.computation.executor.receipt",
                    name,
                    "executor.receipt should be a list of field names",
                )
        if "computation" not in meta and not re.search(
            r"(?mi)^#\s+Computation\s*$", body
        ):
            add(
                issues,
                "warning",
                "concept.computation.body",
                name,
                "Attested Computation should provide computation or a # Computation section",
            )


def validate_concept(path: Path, root: Path, issues: list[Issue]) -> dict | None:
    name = rel(path, root)
    try:
        text, _ = read_utf8(path)
    except (OSError, ValueError) as exc:
        add(issues, "error", "concept.utf8", name, str(exc))
        return None
    parts = split_frontmatter(text)
    if parts is None:
        add(issues, "error", "concept.frontmatter", name, "missing YAML frontmatter")
        return None
    try:
        meta = parse_yaml(parts[0])
    except Exception as exc:
        add(issues, "error", "concept.frontmatter", name, str(exc))
        return None
    if not isinstance(meta.get("type"), str) or not meta["type"].strip():
        add(issues, "error", "concept.type", name, "type must be a non-empty string")
    if not isinstance(meta.get("title"), str) or not str(meta.get("title", "")).strip():
        add(issues, "warning", "concept.title", name, "recommended title is missing or empty")
    description = meta.get("description")
    if not isinstance(description, str) or not description.strip():
        add(issues, "warning", "concept.description", name, "recommended description is missing or empty")
    elif "\n" in description:
        add(issues, "warning", "concept.description", name, "description should be one line")
    if "resource" in meta and not isinstance(meta["resource"], str):
        add(issues, "warning", "concept.resource", name, "resource should be a path or URI string")
    if "tags" in meta and (
        not isinstance(meta["tags"], list) or not all(isinstance(tag, str) for tag in meta["tags"])
    ):
        add(issues, "warning", "concept.tags", name, "tags should be a YAML list of strings")
    validate_optional_frontmatter(meta, parts[1], name, issues)
    return meta


def validate_index(path: Path, root: Path, issues: list[Issue]) -> None:
    name = rel(path, root)
    try:
        text, _ = read_utf8(path)
    except (OSError, ValueError) as exc:
        add(issues, "error", "index.utf8", name, str(exc))
        return
    parts = split_frontmatter(text)
    body = text
    if parts:
        if path.parent != root:
            add(issues, "error", "index.frontmatter", name, "only the root index may have frontmatter")
        try:
            meta = parse_yaml(parts[0])
            if path.parent == root:
                version = meta.get("okf_version")
                if version is None:
                    add(issues, "warning", "index.version", name, "root index does not declare okf_version")
                elif str(version) == "0.1":
                    add(
                        issues,
                        "warning",
                        "index.version.legacy",
                        name,
                        "bundle targets superseded OKF version '0.1'",
                    )
                elif str(version) != "0.2":
                    add(
                        issues,
                        "warning",
                        "index.version",
                        name,
                        f"unsupported OKF version {version!r}; use best-effort consumption",
                    )
        except Exception as exc:
            add(issues, "error", "index.frontmatter", name, str(exc))
        body = parts[1]
    elif path.parent == root:
        add(issues, "warning", "index.version", name, "root index does not declare okf_version")
    without_comments = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    if not re.search(r"(?m)^#{1,6}\s+\S", without_comments):
        add(issues, "error", "index.structure", name, "index must contain a section heading")


def validate_log(path: Path, root: Path, issues: list[Issue]) -> None:
    name = rel(path, root)
    try:
        text, _ = read_utf8(path)
    except (OSError, ValueError) as exc:
        add(issues, "error", "log.utf8", name, str(exc))
        return
    if split_frontmatter(text):
        add(issues, "error", "log.frontmatter", name, "log files must not have frontmatter")
    if not re.search(r"(?m)^#\s+\S", text):
        add(issues, "error", "log.structure", name, "log must have a title heading")
    headings = list(DATE_HEADING.finditer(text))
    if not headings:
        add(issues, "error", "log.structure", name, "log must have at least one YYYY-MM-DD section")
        return
    try:
        dates = [date.fromisoformat(match.group(1)) for match in headings]
    except ValueError as exc:
        add(issues, "error", "log.date", name, str(exc))
        return
    if dates != sorted(dates, reverse=True):
        add(issues, "error", "log.order", name, "date sections must be newest first")
    for index, match in enumerate(headings):
        section_end = (
            headings[index + 1].start()
            if index + 1 < len(headings)
            else len(text)
        )
        if not re.search(r"(?m)^\s*[-*+]\s+\S", text[match.end() : section_end]):
            add(
                issues,
                "error",
                "log.structure",
                name,
                f"{match.group(1)} section must contain at least one list entry",
            )


def link_target(source: Path, root: Path, raw: str) -> Path | None:
    target = raw[1:-1] if raw.startswith("<") and raw.endswith(">") else raw
    target = unquote(urlsplit(target).path)
    if not target or raw.startswith("#") or urlsplit(raw).scheme or raw.startswith("//"):
        return None
    candidate = root / target.lstrip("/") if target.startswith("/") else source.parent / target
    return candidate.resolve()


def validate_links(path: Path, root: Path, issues: list[Issue]) -> None:
    name = rel(path, root)
    try:
        text, _ = read_utf8(path)
    except (OSError, ValueError):
        return
    for match in LINK.finditer(text):
        raw = match.group(1)
        target = link_target(path, root, raw)
        if target is None:
            continue
        try:
            target.relative_to(root.resolve())
        except ValueError:
            add(issues, "warning", "link.outside", name, f"link escapes the bundle: {raw}")
            continue
        if not target.exists():
            add(issues, "warning", "link.broken", name, f"target does not exist: {raw}")


def concept_dirs(root: Path) -> list[Path]:
    dirs = {root}
    for path in root.rglob("*.md"):
        if path.name not in {"index.md", "log.md"}:
            current = path.parent
            while True:
                dirs.add(current)
                if current == root:
                    break
                current = current.parent
    return sorted(dirs, key=lambda p: rel(p, root) if p != root else "")


def display_name(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").strip().title()


def escape_label(value: str) -> str:
    return value.replace("[", r"\[").replace("]", r"\]")


def index_block(directory: Path, root: Path, newline: str = "\n") -> str:
    concepts: list[tuple[str, str, str]] = []
    for path in sorted(directory.glob("*.md"), key=lambda p: p.name):
        if path.name in {"index.md", "log.md"}:
            continue
        title, description = display_name(path.stem), ""
        try:
            text, _ = read_utf8(path)
            parts = split_frontmatter(text)
            meta = parse_yaml(parts[0]) if parts else {}
            title = str(meta.get("title") or title)
            description = str(meta.get("description") or "")
        except Exception:
            pass
        concepts.append((path.name, title, description))
    children = [
        child
        for child in sorted((p for p in directory.iterdir() if p.is_dir()), key=lambda p: p.name)
        if any(p.name not in {"index.md", "log.md"} for p in child.rglob("*.md"))
    ]
    lines = [START]
    if concepts:
        lines += ["# Concepts", ""]
        for filename, title, description in concepts:
            suffix = f" - {description}" if description else ""
            lines.append(f"* [{escape_label(title)}]({filename}){suffix}")
    if children:
        if len(lines) > 1:
            lines.append("")
        lines += ["# Directories", ""]
        for child in children:
            lines.append(f"* [{escape_label(display_name(child.name))}]({child.name}/) - Browse this group.")
    lines.append(END)
    return newline.join(lines)


def index_status(root: Path, write: bool, version: str = "0.2") -> tuple[list[str], list[str]]:
    stale: list[str] = []
    refused: list[str] = []
    for directory in concept_dirs(root):
        path = directory / "index.md"
        if path.exists():
            text, bom = read_utf8(path)
            newline = "\r\n" if "\r\n" in text else "\n"
            expected = index_block(directory, root, newline)
            starts, ends = text.count(START), text.count(END)
            if starts == 1 and ends == 1 and text.index(START) < text.index(END):
                current = text[text.index(START) : text.index(END) + len(END)]
                if current != expected:
                    stale.append(rel(path, root))
                    if write:
                        text = text[: text.index(START)] + expected + text[text.index(END) + len(END) :]
                        write_utf8(path, text, bom)
            elif starts or ends:
                stale.append(rel(path, root))
                refused.append(rel(path, root))
            else:
                stale.append(rel(path, root))
                if write:
                    refused.append(rel(path, root))
        else:
            stale.append(rel(path, root))
            if write:
                newline = "\n"
                prefix = f'---\nokf_version: "{version}"\n---\n\n' if directory == root else ""
                write_utf8(path, prefix + index_block(directory, root, newline) + newline)
    return stale, refused


def validate_bundle(root: Path) -> list[Issue]:
    require_yaml()
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"bundle is not a directory: {root}")
    issues: list[Issue] = []
    for path in sorted(root.rglob("*.md")):
        if path.name == "index.md":
            validate_index(path, root, issues)
        elif path.name == "log.md":
            validate_log(path, root, issues)
        else:
            validate_concept(path, root, issues)
        validate_links(path, root, issues)
    stale, _ = index_status(root, write=False)
    for name in stale:
        path = root / name
        code = "index.missing" if not path.exists() else "index.stale"
        message = "progressive-disclosure index is missing" if not path.exists() else "index is unmanaged or out of date"
        add(issues, "warning", code, name, message)
    return sorted(issues, key=lambda issue: (issue.path, issue.severity != "error", issue.code))


def replace_top_level_field(raw: str, field: str, replacement: str) -> str:
    lines = raw.splitlines(keepends=True)
    start = next(
        (index for index, line in enumerate(lines) if line.startswith(f"{field}:")),
        None,
    )
    if start is None:
        newline = "\r\n" if "\r\n" in raw else "\n"
        return raw + ("" if raw.endswith(("\n", "\r")) else newline) + replacement
    end = start + 1
    if lines[start].split(":", 1)[1].strip() == "":
        while end < len(lines):
            line = lines[end]
            if line.strip() and not line[:1].isspace():
                break
            end += 1
    return "".join(lines[:start]) + replacement + "".join(lines[end:])


def stamp(paths: list[Path], at: str, by: Optional[str]) -> int:
    if not iso_datetime(at):
        raise ValueError("--at must be an ISO 8601 datetime containing T")
    if by is not None and not actor(by):
        raise ValueError("--by must use producer/version, human:<id>, or process:<id>")
    changed = 0
    for path in paths:
        if path.name in {"index.md", "log.md"}:
            raise ValueError(f"cannot stamp reserved file: {path}")
        text, bom = read_utf8(path)
        parts = split_frontmatter(text)
        if parts is None:
            raise ValueError(f"missing frontmatter: {path}")
        meta = parse_yaml(parts[0])
        raw, _, yaml_start, close_start, _ = parts
        newline = "\r\n" if "\r\n" in text else "\n"
        generated = meta.get("generated")
        if generated is not None and not isinstance(generated, dict):
            raise ValueError(f"generated must be a mapping: {path}")
        generated = dict(generated or {})
        producer = by or generated.get("by")
        if not actor(producer):
            raise ValueError(f"{path} has no valid generated.by; pass --by")
        generated["by"] = producer
        generated["at"] = at
        replacement = yaml.safe_dump(
            {"generated": generated},
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ).replace("\n", newline)
        new_raw = replace_top_level_field(raw, "generated", replacement)
        new_text = text[:yaml_start] + new_raw + text[close_start:]
        if new_text != text:
            write_utf8(path, new_text, bom)
            changed += 1
    return changed


def safe_scope(root: Path, scope: str) -> Path:
    target = (root / scope).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("--scope must stay inside the bundle") from exc
    if not target.is_dir():
        raise ValueError(f"scope is not a directory: {scope}")
    return target


def update_log(root: Path, scope: str, kind: str, message: str, day: str) -> bool:
    parsed_day = date.fromisoformat(day)
    if not kind.strip() or not message.strip() or "\n" in kind or "\n" in message:
        raise ValueError("kind and message must be non-empty single lines")
    path = safe_scope(root, scope) / "log.md"
    entry = f"* **{kind.strip()}**: {message.strip()}"
    if not path.exists():
        write_utf8(path, f"# Directory Update Log\n\n## {day}\n\n{entry}\n")
        return True
    text, bom = read_utf8(path)
    if split_frontmatter(text):
        raise ValueError(f"log must not have frontmatter: {path}")
    headings = list(DATE_HEADING.finditer(text))
    if not headings:
        raise ValueError(f"log has no date sections: {path}")
    dates = [date.fromisoformat(match.group(1)) for match in headings]
    if dates != sorted(dates, reverse=True):
        raise ValueError(f"log date sections are not newest first: {path}")
    for index, match in enumerate(headings):
        section_end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        if dates[index] == parsed_day:
            if entry in text[match.start() : section_end]:
                return False
            insertion = match.end()
            text = text[:insertion] + f"\n\n{entry}" + text[insertion:]
            write_utf8(path, text, bom)
            return True
    insert_at = next((match.start() for match, value in zip(headings, dates) if parsed_day > value), len(text))
    chunk = f"## {day}\n\n{entry}\n\n"
    if insert_at == len(text):
        text = text.rstrip() + "\n\n" + chunk.rstrip() + "\n"
    else:
        text = text[:insert_at] + chunk + text[insert_at:]
    write_utf8(path, text, bom)
    return True


def print_issues(issues: list[Issue], output: str) -> None:
    errors = sum(issue.severity == "error" for issue in issues)
    warnings = len(issues) - errors
    if output == "json":
        print(json.dumps({"errors": errors, "warnings": warnings, "issues": [asdict(i) for i in issues]}, indent=2))
        return
    for issue in issues:
        print(f"{issue.severity.upper():7} {issue.path}: {issue.message} [{issue.code}]")
    print(f"{errors} error(s), {warnings} warning(s)")


def self_test() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        concept = root / "metrics" / "wau.md"
        concept.parent.mkdir()
        write_utf8(
            concept,
            "---\ntype: Metric\ntitle: Weekly active users\ndescription: Distinct weekly users.\n"
            "tags: [product]\nstatus: stable\n"
            "generated: { by: human:analyst, at: 2026-07-16T12:00:00Z }\n"
            "verified: { by: process:nightly, at: 2026-07-16T12:30:00Z }\n"
            "sources:\n  - id: policy\n    resource: https://example.com/policy\n"
            "    author: team:product\n    usage_count: 10\n"
            "usage_window: { from: 2026-07-01, to: 2026-07-31 }\n"
            "producer:\n  nested: true\n---\n\n"
            "See the [root index](/index.md), [missing](/missing.md), and policy.[^policy]\n\n"
            "[^policy]: Product policy\n",
        )
        stale, refused = index_status(root, write=True)
        assert stale and not refused and (root / "index.md").exists()
        issues = validate_bundle(root)
        assert not any(i.severity == "error" for i in issues)
        assert any(i.code == "link.broken" for i in issues)
        assert stamp([concept], "2026-07-16T13:00:00Z", None) == 1
        assert stamp([concept], "2026-07-16T13:00:00Z", None) == 0
        assert "producer:\n  nested: true" in read_utf8(concept)[0]
        stamped = parse_yaml(split_frontmatter(read_utf8(concept)[0])[0])
        assert stamped["generated"]["by"] == "human:analyst"
        assert str(stamped["generated"]["at"]) == "2026-07-16T13:00:00Z"
        assert update_log(root, ".", "Update", "Ran self-test.", "2026-07-16")
        assert not update_log(root, ".", "Update", "Ran self-test.", "2026-07-16")
        assert update_log(root, ".", "Creation", "Added fixture.", "2026-07-15")
        assert not any(i.severity == "error" for i in validate_bundle(root))
        valid_computation = root / "valid-computation.md"
        write_utf8(
            valid_computation,
            "---\ntype: Attested Computation\ntitle: Revenue\n"
            "description: Revenue for one year.\nruntime: bigquery\n"
            "parameters:\n  - { name: year, type: integer, required: true }\n"
            "executor:\n  resource: references/run.md\n  receipt: [job_id, result]\n"
            "attester:\n  resource: references/check.py\n"
            "generated: { by: process:catalog, at: 2026-07-16T14:00:00Z }\n"
            "---\n\n# Computation\n\n```sql\nSELECT @year\n```\n",
        )
        valid_issues = validate_bundle(root)
        assert not any(
            i.code.startswith("concept.computation") and i.path == valid_computation.name
            for i in valid_issues
        )
        legacy = root / "legacy.md"
        write_utf8(
            legacy,
            "---\ntype: Reference\ntimestamp: 2026-07-15T12:00:00Z\n---\n\n"
            "# Citations\n\n- https://example.com\n",
        )
        try:
            stamp([legacy], "2026-07-16T15:00:00Z", None)
            raise AssertionError("legacy stamp should require --by")
        except ValueError:
            pass
        assert stamp([legacy], "2026-07-16T15:00:00Z", "human:analyst") == 1
        write_utf8(root / "bad.md", "---\ntitle: Missing type\n---\n")
        assert any(i.code == "concept.type" for i in validate_bundle(root))
        write_utf8(
            root / "computation.md",
            "---\ntype: Attested Computation\nstatus: unknown\nverified: nope\n---\n",
        )
        optional = validate_bundle(root)
        assert any(i.code == "concept.computation.runtime" for i in optional)
        assert not any(
            i.severity == "error" and i.path == "computation.md" for i in optional
        )
        index = root / "index.md"
        write_utf8(index, read_utf8(index)[0].replace(START, "").replace(END, ""))
        _, refused = index_status(root, write=True)
        assert "index.md" in refused


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate a bundle")
    validate.add_argument("bundle", type=Path)
    validate.add_argument("--format", choices=("text", "json"), default="text")
    index = commands.add_parser("index", help="check or write managed indexes")
    index.add_argument("bundle", type=Path)
    mode = index.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    index.add_argument(
        "--version",
        choices=("0.1", "0.2"),
        default="0.2",
        help="version for a newly created root index",
    )
    stamp_cmd = commands.add_parser("stamp", help="update concept generated.at metadata")
    stamp_cmd.add_argument("concept", nargs="+", type=Path)
    stamp_cmd.add_argument("--at", default=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"))
    stamp_cmd.add_argument("--by", help="producer/version, human:<id>, or process:<id>")
    log_cmd = commands.add_parser("log", help="add a scoped log entry")
    log_cmd.add_argument("bundle", type=Path)
    log_cmd.add_argument("--scope", required=True)
    log_cmd.add_argument("--kind", required=True)
    log_cmd.add_argument("--message", required=True)
    log_cmd.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat())
    commands.add_parser("self-test", help="run a small temporary-bundle check")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        require_yaml()
        if args.command == "validate":
            issues = validate_bundle(args.bundle)
            print_issues(issues, args.format)
            return 1 if any(issue.severity == "error" for issue in issues) else 0
        if args.command == "index":
            stale, refused = index_status(
                args.bundle.resolve(), write=args.write, version=args.version
            )
            for name in stale:
                action = "refused" if name in refused else ("updated" if args.write else "stale")
                print(f"{action}: {name}")
            if refused:
                print("Refused indexes have missing or malformed managed markers; preserve them manually.", file=sys.stderr)
            return 1 if (args.check and stale) or refused else 0
        if args.command == "stamp":
            print(f"updated {stamp(args.concept, args.at, args.by)} concept(s)")
            return 0
        if args.command == "log":
            print("updated" if update_log(args.bundle.resolve(), args.scope, args.kind, args.message, args.date) else "unchanged")
            return 0
        self_test()
        print("self-test passed")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
