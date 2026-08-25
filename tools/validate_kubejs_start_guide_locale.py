#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EN = ROOT / "kubejs/assets/kubejs/lang/en_us.json"
RU = ROOT / "kubejs/assets/kubejs/lang/ru_ru.json"
BOOK_ROOT = ROOT / "kubejs/data/kubejs/modonomicon/books/minecraft_start_guide"

BOOK_PREFIX = "book.kubejs.minecraft_start_guide"

PLACEHOLDER_RE = re.compile(
    r"%(?:\d+\$)?[#+\- 0,(]*\d*(?:\.\d+)?[bcdeEufFgGosxXaA%]|"
    r"%[A-Za-z0-9_]+%|"
    r"\{\d+\}|"
    r"\$\{[^}]+\}"
)
RESOURCE_RE = re.compile(r"(?<![A-Za-z0-9_#])#?[a-z0-9_.-]+:[a-z0-9_./-]+")
FORMAT_RE = re.compile(r"§[0-9A-FK-ORa-fk-or]|&[0-9A-FK-ORa-fk-or]")
MODONOMICON_MARKUP_RE = re.compile(r"\$\([^)]*\)")
ESCAPE_RE = re.compile(r"\\(?:[btnfr\"\\]|u[0-9a-fA-F]{4}|.)")
MIXED_GLUE_RE = re.compile(r"[A-Za-z][А-Яа-яЁё]|[А-Яа-яЁё][A-Za-z]")
SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+[.,:;!?]")
DOUBLE_SPACE_RE = re.compile(r" {2,}")

BAD_TRANSLATIONS = (
    "водяная кожа",
    "плавильный завод",
)

VANILLA_ENGLISH_TERMS = (
    "Flint",
    "Campfire",
    "Furnace",
    "Smoker",
    "Leather Armor",
    "Iron",
    "Coal",
    "Crafting Table",
)

WHITELIST_ENGLISH = (
    "Ascension of Ages",
    "Create",
    "Cold Sweat",
    "Thirst Was Taken",
    "Ecliptic Seasons",
    "Farmer's Delight",
    "Aquaculture",
    "Overgeared",
    "Clavis",
    "MineColonies",
    "Immersive Engineering",
    "Oritech",
    "Mekanism",
    "Applied Energistics 2",
    "Spectrum",
    "Neo Vitae",
    "Malum",
    "Theurgy",
    "Occultism",
    "Forbidden Arcanus",
    "Mahou Tsukai",
    "Draconic Evolution",
    "End Remastered",
    "Deeper Darker",
    "Mowzie's Mobs",
    "The Aether",
    "The Undergarden",
    "Nutritional Balance",
    "Waterskin",
    "Icebox",
    "Smeltery",
    "Boiler",
    "Terracotta Bowl",
    "Smithing Anvil",
    "Copper Smithing Hammer",
    "Hand Crank",
    "Millstone",
    "Mechanical Press",
    "Mechanical Mixer",
    "Basin",
    "Blaze Burner",
    "Rocks",
    "Goat Fur",
    "Chameleon Molt",
    "Thermometer",
    "Calendar",
    "Sleeping Bag",
    "Waystones",
    "Entering the Iron Era",
    "The First Mill",
    "Slice and Dice",
    "Cooking for Blockheads",
)

COMMON_ENGLISH_WORD_RE = re.compile(
    r"\b(?:the|and|or|to|from|with|without|should|this|that|where|what|why|how|"
    r"first|later|early|normal|player|players|quest|quests|book|chapter|route|"
    r"world|pack|stage|progression|survival|treasure|locked|unlock|unlocked)\b",
    re.IGNORECASE,
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be a JSON object")
    return data


def collect_book_refs() -> set[str]:
    refs: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str) and value.startswith(BOOK_PREFIX):
            refs.add(value)

    for path in BOOK_ROOT.rglob("*.json"):
        walk(load_json(path))
    return refs


def counter(pattern: re.Pattern[str], text: str) -> Counter[str]:
    return Counter(pattern.findall(text))


def strip_whitelist(text: str) -> str:
    stripped = text
    for phrase in sorted(WHITELIST_ENGLISH, key=len, reverse=True):
        stripped = stripped.replace(phrase, "")
    return stripped


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        en = load_json(EN)
        ru = load_json(RU)
    except Exception as exc:  # noqa: BLE001 - CLI validator should report parse errors plainly.
        print(f"ERROR: {exc}")
        return 1

    en_keys = set(en)
    ru_keys = set(ru)
    if en_keys != ru_keys:
        errors.append(
            "key set differs: "
            f"missing={sorted(en_keys - ru_keys)[:20]} "
            f"extra={sorted(ru_keys - en_keys)[:20]}"
        )

    book_refs = collect_book_refs()
    missing_book_refs = sorted(book_refs - ru_keys)
    if missing_book_refs:
        errors.append(f"missing Modonomicon book keys: {missing_book_refs[:20]}")

    checks = (
        ("placeholders", PLACEHOLDER_RE),
        ("resource IDs", RESOURCE_RE),
        ("formatting codes", FORMAT_RE),
        ("Modonomicon markup", MODONOMICON_MARKUP_RE),
        ("escape sequences", ESCAPE_RE),
    )

    for key in sorted(en_keys & ru_keys):
        en_value = en[key]
        ru_value = ru[key]
        if not isinstance(en_value, str) or not isinstance(ru_value, str):
            errors.append(f"{key}: values must be strings in both locales")
            continue
        if not ru_value:
            errors.append(f"{key}: empty Russian value")
        if en_value.count("\n") != ru_value.count("\n"):
            errors.append(f"{key}: newline count changed")
        for label, pattern in checks:
            if counter(pattern, en_value) != counter(pattern, ru_value):
                errors.append(f"{key}: {label} changed")
        if MIXED_GLUE_RE.search(ru_value):
            errors.append(f"{key}: possible Cyrillic/Latin glued word")
        if SPACE_BEFORE_PUNCT_RE.search(ru_value):
            errors.append(f"{key}: space before punctuation")
        if DOUBLE_SPACE_RE.search(ru_value):
            errors.append(f"{key}: double spaces")
        lowered = ru_value.casefold()
        for phrase in BAD_TRANSLATIONS:
            if phrase in lowered:
                errors.append(f"{key}: blacklisted machine translation: {phrase}")
        for term in VANILLA_ENGLISH_TERMS:
            if re.search(rf"\b{re.escape(term)}\b", ru_value):
                errors.append(f"{key}: vanilla Minecraft term left in English: {term}")

        unwhitelisted = strip_whitelist(ru_value)
        if COMMON_ENGLISH_WORD_RE.search(unwhitelisted):
            warnings.append(f"{key}: possible unwhitelisted English fragment")

    print(f"EN keys: {len(en)}")
    print(f"RU keys: {len(ru)}")
    print(f"Keys match: {en_keys == ru_keys}")
    print(f"Modonomicon book refs: {len(book_refs)}")
    print(f"Missing book refs: {len(missing_book_refs)}")

    if warnings:
        print(f"Warnings: {len(warnings)}")
        for warning in warnings[:50]:
            print(f"- {warning}")

    if errors:
        print(f"Validation failed with {len(errors)} issue(s):")
        for error in errors[:200]:
            print(f"- {error}")
        if len(errors) > 200:
            print(f"- ... {len(errors) - 200} more")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
