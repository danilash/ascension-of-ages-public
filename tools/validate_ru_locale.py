#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EN = ROOT / "config/ftbquests/quests/lang/en_us.snbt"
RU = ROOT / "config/ftbquests/quests/lang/ru_ru.snbt"

ENTRY_RE = re.compile(r"^\s*([^\s\[\]{}:]+):\s*(.*)$")
STRING_RE = re.compile(r'"(?:\\.|[^"\\])*"')
FORMAT_RE = re.compile(r"&[0-9A-FK-ORa-fk-or]")
PLACEHOLDER_RE = re.compile(
    r"%(?:\d+\$)?[#+\- 0,(]*\d*(?:\.\d+)?[bcdeEufFgGosxXaA%]|"
    r"%[A-Za-z0-9_]+%|"
    r"\{\d+\}|"
    r"\$\{[^}]+\}"
)
RESOURCE_RE = re.compile(r"(?<![A-Za-z0-9_#])#?[a-z0-9_.-]+:[a-z0-9_./-]+")
ESCAPE_RE = re.compile(r'\\(?:[btnfr"\\]|u[0-9a-fA-F]{4}|.)')
JSON_COMPONENT_RE = re.compile(r'\{\s*\\"text\\"\s*:|\\"clickEvent\\"|\\"change_page\\"')


class LocaleError(Exception):
    pass


def collect_entry(lines: list[str], start: int) -> tuple[int, str, str, list[str]]:
    line = lines[start]
    match = ENTRY_RE.match(line)
    if not match:
        raise LocaleError(f"line {start + 1}: not a localization entry")

    key, rest = match.group(1), match.group(2)
    value_lines = [line]

    if rest.lstrip().startswith("[") and "]" not in rest:
        i = start + 1
        while i < len(lines):
            value_lines.append(lines[i])
            if lines[i].strip() == "]":
                return i + 1, key, "\n".join(value_lines), value_lines
            i += 1
        raise LocaleError(f"{key}: unterminated array")

    return start + 1, key, line, value_lines


def parse(path: Path) -> dict[str, dict[str, object]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    entries: dict[str, dict[str, object]] = {}
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped or stripped in ("{", "}"):
            i += 1
            continue
        if not ENTRY_RE.match(lines[i]):
            raise LocaleError(f"{path}: unexpected SNBT line {i + 1}: {lines[i]}")

        next_i, key, raw, value_lines = collect_entry(lines, i)
        if key in entries:
            raise LocaleError(f"{path}: duplicate key {key}")
        strings = STRING_RE.findall(raw)
        entries[key] = {
            "raw": raw,
            "lines": value_lines,
            "strings": strings,
            "is_array": "[" in value_lines[0],
            "format": FORMAT_RE.findall(raw),
            "placeholders": PLACEHOLDER_RE.findall(raw),
            "resources": RESOURCE_RE.findall(raw),
            "escapes": ESCAPE_RE.findall(raw),
            "json_components": JSON_COMPONENT_RE.findall(raw),
        }
        i = next_i
    return entries


def compare_counters(label: str, key: str, en_values: list[str], ru_values: list[str], errors: list[str]) -> None:
    if Counter(en_values) != Counter(ru_values):
        errors.append(
            f"{key}: {label} changed: EN {dict(Counter(en_values))} != RU {dict(Counter(ru_values))}"
        )


def main() -> int:
    try:
        en = parse(EN)
        ru = parse(RU)
    except LocaleError as exc:
        print(f"ERROR: {exc}")
        return 1

    errors: list[str] = []
    en_keys = set(en)
    ru_keys = set(ru)
    if en_keys != ru_keys:
        missing = sorted(en_keys - ru_keys)
        extra = sorted(ru_keys - en_keys)
        errors.append(f"key set differs: missing={missing[:20]} extra={extra[:20]}")

    for key in sorted(en_keys & ru_keys):
        e = en[key]
        r = ru[key]
        if e["is_array"] != r["is_array"]:
            errors.append(f"{key}: value kind changed")
        if len(e["strings"]) != len(r["strings"]):
            errors.append(f"{key}: string literal count changed")
        if any(not s for s in r["strings"]):
            errors.append(f"{key}: empty string literal in RU")

        compare_counters("Minecraft formatting codes", key, e["format"], r["format"], errors)
        compare_counters("placeholders", key, e["placeholders"], r["placeholders"], errors)
        compare_counters("resource IDs", key, e["resources"], r["resources"], errors)
        compare_counters("escape sequences", key, e["escapes"], r["escapes"], errors)
        compare_counters("JSON component markers", key, e["json_components"], r["json_components"], errors)

    print(f"EN entries: {len(en)}")
    print(f"RU entries: {len(ru)}")
    print(f"Keys match: {en_keys == ru_keys}")

    if errors:
        print(f"Validation failed with {len(errors)} issue(s):")
        for issue in errors[:200]:
            print(f"- {issue}")
        if len(errors) > 200:
            print(f"- ... {len(errors) - 200} more")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
