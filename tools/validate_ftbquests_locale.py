#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTS_ROOT = ROOT / "config/ftbquests/quests"
EN = QUESTS_ROOT / "lang/en_us.snbt"
RU = QUESTS_ROOT / "lang/ru_ru.snbt"
CHAPTERS = QUESTS_ROOT / "chapters"
CHAPTER_GROUPS = QUESTS_ROOT / "chapter_groups.snbt"

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
MIXED_GLUE_RE = re.compile(r"[A-Za-z][А-Яа-яЁё]|[А-Яа-яЁё][A-Za-z]")
DOUBLE_SPACE_RE = re.compile(r" {2,}")
SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+[.,:;!?]")
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
LATIN_RE = re.compile(r"[A-Za-z]")

BLACKLIST = (
    "водяная кожа",
    "плавильный завод",
    "стресс",
    "гейт",
    "Восхождение",
    "Позолоченная эпоха",
)

CRITICAL_BLACKLIST = {
    "водяная кожа",
    "плавильный завод",
}

WHITELIST_ENGLISH_TERMS = (
    "Create",
    "Mekanism",
    "Waterskin",
    "Icebox",
    "Smeltery",
    "Draconic Evolution",
    "Avaritia",
    "Extended Crafting",
)

ENGLISH_ALLOWED_VALUES = {
    "Ascension of Ages",
    "Advanced Auto Table",
    "Advanced Coil",
    "Advanced Fluid Hatches",
    "Advanced Frame",
    "Advanced Machine Core",
    "Apprentice Blood Orb",
    "Book of Binding: Empty",
    "Book of Binding: Foliot",
    "Book of Calling: Janitor",
    "Book of Calling: Transporter",
    "Heart of the Deep",
    "Orb of Prophecy",
    "The Gatekeeper",
    "The Harbinger",
    "The Timekeeper",
}

ENGLISH_TITLE_SUSPECT_RE = re.compile(
    r"\b(?:the|and|to|of|deeper|table|apex|dream|heart|timekeeper)\b",
    re.IGNORECASE,
)
COMMON_ENGLISH_SENTENCE_RE = re.compile(
    r"\b(?:the|and|or|to|from|with|without|should|this|that|where|what|why|how|"
    r"first|later|early|normal|player|players|quest|quests|book|chapter|route|"
    r"world|pack|stage|progression|survival|treasure|locked|unlock|unlocked|"
    r"build|craft|place|use|find|defeat|complete|requires|required|before|after|"
    r"keep|make|hold|bring|assemble|upgrade|then|into|through|between)\b",
    re.IGNORECASE,
)
VY_RE = re.compile(
    r"\b(?:вы|Вы|вам|Вам|ваш\w*|Ваш\w*|сделайте|создайте|постройте|найдите|"
    r"возьмите|держите|используйте|установите|поставьте|добавьте|заполните|"
    r"заморозите|подключите|соберите|обновите|проведите|отслеживайте|проверьте|"
    r"объедините|переверните|погрузите|докажите|разверните|закройте|оденьтесь|"
    r"вооружите|замените|собирайте|позволяйте|добавляйте|пополняйте|нарисуйте|"
    r"разведайте|накормите|сложите|ожидайте|назовите)\b",
    re.IGNORECASE,
)
TY_RE = re.compile(r"\b(?:ты|тебе|тебя|твой\w*|твоя|твои|твою|тобой)\b", re.IGNORECASE)
MACHINE_MARKER_RE = re.compile(
    r"\bэлементы\b|\bэлемент\b|\bтолпы\b|\bгрудн|\bмоди\b|пожимают руки|"
    r"трубопроводной мощности|пожарн|желт(?:ый|ого) пирог|прием пожарных|"
    r"буквальный предмет|кормовые машины|штукатурк|разработчик Create|мафиозн|"
    r"организации|рисовать вещи|хорошо очищенные|дорожным тросом|трасс[ае] Create|"
    r"Боги - это колеса|пугала|страшилки|Построй Tool|Строительный инструмент.*Tool",
    re.IGNORECASE,
)
FORMAT_JOIN_RE = re.compile(
    r"&r&b|EngineeringCrusher|NauTec&b|Mekanism&r&b|PneumaticCraft&r&b|"
    r"Create Addition&r&b|Create&r&b|PneumaticCraft&r&6|Nuclear Science&r&b"
)


class LocaleError(Exception):
    pass


@dataclass(frozen=True)
class Entry:
    key: str
    raw: str
    strings: tuple[str, ...]
    line: int
    is_array: bool
    formats: tuple[str, ...]
    placeholders: tuple[str, ...]
    resources: tuple[str, ...]
    escapes: tuple[str, ...]
    json_components: tuple[str, ...]

    @property
    def text(self) -> str:
        return " / ".join(self.strings)


@dataclass(frozen=True)
class Issue:
    severity: str
    key: str
    line: int
    message: str
    value: str


def decode_string(token: str, path: Path, line: int) -> str:
    try:
        return ast.literal_eval(token)
    except Exception as exc:  # noqa: BLE001 - report file and line in CLI output.
        raise LocaleError(f"{path}:{line}: invalid quoted string {token!r}: {exc}") from exc


def collect_entry(lines: list[str], start: int, path: Path) -> tuple[int, str, str, list[str]]:
    match = ENTRY_RE.match(lines[start])
    if not match:
        raise LocaleError(f"{path}:{start + 1}: not a localization entry")

    key, rest = match.group(1), match.group(2)
    value_lines = [lines[start]]

    if rest.lstrip().startswith("[") and "]" not in rest:
        i = start + 1
        while i < len(lines):
            value_lines.append(lines[i])
            if lines[i].strip() == "]":
                return i + 1, key, "\n".join(value_lines), value_lines
            i += 1
        raise LocaleError(f"{path}:{start + 1}: unterminated array for {key}")

    return start + 1, key, lines[start], value_lines


def parse_locale(path: Path) -> dict[str, Entry]:
    lines = path.read_text(encoding="utf-8").splitlines()
    entries: dict[str, Entry] = {}
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped or stripped in ("{", "}"):
            i += 1
            continue
        if not ENTRY_RE.match(lines[i]):
            raise LocaleError(f"{path}:{i + 1}: unexpected SNBT line: {lines[i]}")

        next_i, key, raw, value_lines = collect_entry(lines, i, path)
        if key in entries:
            raise LocaleError(f"{path}:{i + 1}: duplicate key {key}")

        strings = tuple(decode_string(token, path, i + 1) for token in STRING_RE.findall(raw))
        entries[key] = Entry(
            key=key,
            raw=raw,
            strings=strings,
            line=i + 1,
            is_array="[" in value_lines[0],
            formats=tuple(FORMAT_RE.findall(raw)),
            placeholders=tuple(PLACEHOLDER_RE.findall(raw)),
            resources=tuple(RESOURCE_RE.findall(raw)),
            escapes=tuple(ESCAPE_RE.findall(raw)),
            json_components=tuple(JSON_COMPONENT_RE.findall(raw)),
        )
        i = next_i

    return entries


def collect_structure() -> tuple[dict[str, str], dict[str, str], Counter[str], int]:
    group_titles: dict[str, str] = {}
    group_ids = re.findall(r'\{ id: "([0-9A-F]+)" \}', CHAPTER_GROUPS.read_text(encoding="utf-8"))
    for group_id in group_ids:
        group_titles[group_id] = group_id

    id_to_group: dict[str, str] = {group_id: group_id for group_id in group_ids}
    chapter_counts: Counter[str] = Counter()
    quest_count = 0

    for path in sorted(CHAPTERS.glob("*.snbt")):
        text = path.read_text(encoding="utf-8")
        chapter_id_match = re.search(r'^\tid: "([0-9A-F]+)"', text, re.MULTILINE)
        group_match = re.search(r'^\tgroup: "([0-9A-F]+)"', text, re.MULTILINE)
        if not chapter_id_match or not group_match:
            continue

        chapter_id = chapter_id_match.group(1)
        group_id = group_match.group(1)
        chapter_counts[group_id] += 1
        id_to_group[chapter_id] = group_id

        for object_id in re.findall(r'\bid: "([0-9A-F]{16})"', text):
            id_to_group[object_id] = group_id

        quest_count += len(re.findall(r"^\t\t\{\s*$", text, re.MULTILINE))

    return group_titles, id_to_group, chapter_counts, quest_count


def clean_formatting(value: str) -> str:
    return FORMAT_RE.sub("", value).strip()


def strip_whitelist(value: str) -> str:
    stripped = FORMAT_RE.sub("", value)
    for term in sorted(WHITELIST_ENGLISH_TERMS, key=len, reverse=True):
        stripped = re.sub(rf"\b{re.escape(term)}\b", "", stripped)
    for allowed in sorted(ENGLISH_ALLOWED_VALUES, key=len, reverse=True):
        stripped = stripped.replace(allowed, "")
    stripped = RESOURCE_RE.sub("", stripped)
    return stripped


def epoch_for_key(key: str, id_to_group: dict[str, str], group_names: dict[str, str]) -> str:
    parts = key.split(".")
    if len(parts) < 2:
        return "unknown"
    group_id = id_to_group.get(parts[1])
    if not group_id:
        return "unknown"
    return group_names.get(group_id, group_id)


def add_issue(
    issues: list[Issue],
    severity: str,
    entry: Entry,
    message: str,
) -> None:
    issues.append(Issue(severity, entry.key, entry.line, message, entry.text[:500]))


def add_key_issue(
    issues: list[Issue],
    severity: str,
    key: str,
    line: int,
    message: str,
    value: str = "",
) -> None:
    issues.append(Issue(severity, key, line, message, value[:500]))


def compare_counter(
    issues: list[Issue],
    label: str,
    en_entry: Entry,
    ru_entry: Entry,
    severity: str = "CRITICAL",
) -> None:
    if Counter(getattr(en_entry, label)) != Counter(getattr(ru_entry, label)):
        add_issue(
            issues,
            severity,
            ru_entry,
            f"{label.replace('_', ' ')} changed",
        )


def is_full_english(value: str) -> bool:
    cleaned = clean_formatting(value)
    if cleaned in ENGLISH_ALLOWED_VALUES:
        return False
    if not LATIN_RE.search(cleaned) or CYRILLIC_RE.search(cleaned):
        return False
    return bool(COMMON_ENGLISH_SENTENCE_RE.search(cleaned))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit FTB Quests Russian localization.")
    parser.add_argument("--all", action="store_true", help="print every issue instead of capping lists")
    parser.add_argument("--limit", type=int, default=80, help="issues to print per severity without --all")
    args = parser.parse_args()

    try:
        en = parse_locale(EN)
        ru = parse_locale(RU)
    except LocaleError as exc:
        print(f"ERROR: {exc}")
        return 1

    group_ids, id_to_group, chapter_counts, quest_count = collect_structure()
    group_names = {
        group_id: clean_formatting(ru.get(f"chapter_group.{group_id}.title", Entry("", "", (), 0, False, (), (), (), (), ())).text)
        for group_id in group_ids
    }

    issues: list[Issue] = []
    en_keys = set(en)
    ru_keys = set(ru)

    if en_keys != ru_keys:
        for key in sorted(en_keys - ru_keys):
            add_key_issue(issues, "CRITICAL", key, 0, "missing RU key")
        for key in sorted(ru_keys - en_keys):
            add_key_issue(issues, "CRITICAL", key, ru[key].line, "extra RU key", ru[key].text)

    for key in sorted(en_keys & ru_keys):
        en_entry = en[key]
        ru_entry = ru[key]

        if en_entry.is_array != ru_entry.is_array:
            add_issue(issues, "CRITICAL", ru_entry, "value kind changed: array/scalar mismatch")
        if len(en_entry.strings) != len(ru_entry.strings):
            add_issue(issues, "CRITICAL", ru_entry, "quoted string count changed")
        if any(value == "" for value in ru_entry.strings):
            add_issue(issues, "CRITICAL", ru_entry, "empty Russian string")
        if en_entry.raw.count(r"\n") != ru_entry.raw.count(r"\n"):
            add_issue(issues, "CRITICAL", ru_entry, r"\n count changed")

        compare_counter(issues, "formats", en_entry, ru_entry)
        compare_counter(issues, "placeholders", en_entry, ru_entry)
        compare_counter(issues, "resources", en_entry, ru_entry)
        compare_counter(issues, "escapes", en_entry, ru_entry)
        compare_counter(issues, "json_components", en_entry, ru_entry)

        glue_candidate = strip_whitelist(ru_entry.text)
        if MIXED_GLUE_RE.search(glue_candidate):
            add_issue(issues, "MEDIUM", ru_entry, "possible Cyrillic/Latin glued word")
        if DOUBLE_SPACE_RE.search(ru_entry.text):
            add_issue(issues, "LOW", ru_entry, "double spaces")
        if SPACE_BEFORE_PUNCT_RE.search(ru_entry.text):
            add_issue(issues, "LOW", ru_entry, "space before punctuation")

        lowered = ru_entry.text.casefold()
        for term in BLACKLIST:
            if term.casefold() not in lowered:
                continue
            severity = "CRITICAL" if term in CRITICAL_BLACKLIST else "MEDIUM"
            message = f"blacklisted term: {term}"
            if term == "Восхождение" and "Ascension" not in en_entry.text:
                severity = "LOW"
                message = "possible inconsistent Ascension term: Восхождение"
            add_issue(issues, severity, ru_entry, message)

        if VY_RE.search(ru_entry.text):
            severity = "MEDIUM" if TY_RE.search(ru_entry.text) else "LOW"
            add_issue(issues, severity, ru_entry, "possible вы-form or plural imperative")

        if MACHINE_MARKER_RE.search(ru_entry.text):
            add_issue(issues, "MEDIUM", ru_entry, "possible machine-translation marker")

        if FORMAT_JOIN_RE.search(ru_entry.raw):
            add_issue(issues, "LOW", ru_entry, "formatting code adjacent to item/mod name")

        if is_full_english(ru_entry.text):
            suffix = key.split(".")[-1]
            severity = "MEDIUM" if suffix == "title" else "CRITICAL"
            add_issue(issues, severity, ru_entry, "possible untranslated English value")

    by_severity: dict[str, list[Issue]] = {
        "CRITICAL": [],
        "MEDIUM": [],
        "LOW": [],
    }
    for issue in issues:
        by_severity[issue.severity].append(issue)

    prefix_counts = Counter(key.split(".")[0] for key in ru)
    suffix_counts = Counter(key.split(".")[-1] for key in ru)
    locale_by_epoch: Counter[str] = Counter()
    for key in ru:
        locale_by_epoch[epoch_for_key(key, id_to_group, group_names)] += 1

    print("FTB Quests locale audit")
    print(f"EN entries: {len(en)}")
    print(f"RU entries: {len(ru)}")
    print(f"Keys match: {en_keys == ru_keys}")
    print(f"Chapter groups: {len(group_ids)}")
    print(f"Chapters: {sum(chapter_counts.values())}")
    print(f"Quests: {quest_count}")
    print(f"Quest titles: {sum(1 for key in ru if key.startswith('quest.') and key.endswith('.title'))}")
    print(f"Quest subtitles: {suffix_counts['quest_subtitle']}")
    print(f"Quest descriptions: {suffix_counts['quest_desc']}")
    print(f"Task titles: {prefix_counts['task']}")
    print(f"Reward titles: {prefix_counts['reward']}")
    print()
    print("Locale entries by top-level prefix:")
    for name, count in sorted(prefix_counts.items()):
        print(f"- {name}: {count}")
    print()
    print("Chapters by group:")
    for group_id in group_ids:
        group_name = group_names.get(group_id, group_id)
        print(f"- {group_name}: {chapter_counts[group_id]} chapters, {locale_by_epoch[group_name]} locale entries")
    print()
    print("Allowed English terms:")
    for term in WHITELIST_ENGLISH_TERMS:
        print(f"- {term}")
    print()

    for severity in ("CRITICAL", "MEDIUM", "LOW"):
        items = by_severity[severity]
        print(f"{severity}: {len(items)}")
        limit = len(items) if args.all else args.limit
        for issue in items[:limit]:
            epoch = epoch_for_key(issue.key, id_to_group, group_names)
            print(f"- line {issue.line}: {issue.key} [{epoch}] - {issue.message}")
            if issue.value:
                print(f"  RU: {issue.value}")
        if len(items) > limit:
            print(f"- ... {len(items) - limit} more; rerun with --all to print every issue")
        print()

    if by_severity["CRITICAL"]:
        print("Validation failed: critical localization issues found.")
        return 1

    print("Validation passed: no critical localization issues found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
