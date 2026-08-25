#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EN = ROOT / "kubejs/assets/aoa/lang/en_us.json"
RU = ROOT / "kubejs/assets/aoa/lang/ru_ru.json"
BOOK_ROOT = ROOT / "kubejs/data/aoa/modonomicon/books"

BOOKS = (
    "dark_ages_manual",
    "medieval_codex",
    "renaissance_compendium",
    "industrial_codex",
    "gilded_ledger",
    "atomic_dossier",
    "otherworldly_codex",
    "ascension_codex",
)

EXPECTED_KEYS = 932

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
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
COMMON_ENGLISH_WORD_RE = re.compile(
    r"\b(?:the|and|or|to|from|with|without|should|this|that|where|what|why|how|"
    r"first|later|early|normal|player|players|quest|quests|book|chapter|route|"
    r"world|pack|stage|progression|survival|treasure|locked|unlock|unlocked|"
    r"build|craft|place|use|find|defeat|complete|requires|required|before|after)\b",
    re.IGNORECASE,
)

BAD_TRANSLATIONS = (
    "водяная кожа",
    "плавильный завод",
    "гейт",
    "стресс Create",
)

ALLOWED_ENGLISH_ONLY_VALUES = {
    "Ancient Remnant",
    "Baal",
    "Big Chad Guys",
    "Chartered Arcana",
    "Chaos Guardian",
    "Draconic Additions",
    "EOTS",
    "Eye of the Storm",
    "Foliaath",
    "Frostmaw",
    "Fusion Crafting",
    "Geburah",
    "Gomoria",
    "Gomoria, the Fleshmonger Monk",
    "Grottol",
    "Ashlord, the Infernal Dragon",
    "Baal, the Motionless Calamity",
    "Ignis",
    "Infinity Ingot",
    "Maledictus",
    "Malkuth",
    "Meshuggeneh",
    "Morphegor",
    "Morphegor, the Splitting Tyrant",
    "Naga",
    "Nerakyss, the Kraken",
    "Obsidilith",
    "Gargamaw, the Grotesque Consumer",
    "Helvar, the Underworld Knight",
    "Skor, the Yeti",
    "Sirok, the Sandworm",
    "The Dead God",
    "The Harbinger",
    "The Leviathan",
    "The Slider",
    "The Ultimate Block",
    "The Vigil",
    "The Watcher",
    "Tremorzilla",
    "Umvuthi, the Sunbird",
    "Valamon",
    "Valamon, the Corpse Butcher",
}

WHITELIST_ENGLISH_FRAGMENTS = (
    "AE2",
    "Abhorrent",
    "Acropolis",
    "Advanced Auto Crafting Table",
    "Advanced Crafting Table",
    "Aether",
    "Altar of Abyss",
    "Applied Energistics 2",
    "Arc Furnace",
    "Ars Nouveau",
    "Astral Dimension",
    "Athame",
    "Atomic Disassembler",
    "Avaritia",
    "Awakened",
    "Awakened Draconium",
    "Baal",
    "Ballistix",
    "Basin",
    "Beyond the Veil",
    "Black Chalk",
    "Blaze Burner",
    "Block Factory's Bosses",
    "Boss Respawner",
    "Bosses of Mass Destruction",
    "Coke Oven",
    "Cold Sweat",
    "Copper Smithing Hammer",
    "Coral Golems",
    "Crafting Core",
    "Create",
    "Critical Assembly",
    "Crystal Matrix",
    "Deep Dark",
    "Digital Miner",
    "Draconic Additions",
    "Draconic Cores",
    "Draconic Energy Controller",
    "Draconic Evolution",
    "Draconic Fusion Crafting Injector",
    "Draconic Guardian",
    "Draconic Reactor",
    "Draconic Reactor Core",
    "Dragon Heart",
    "Dragon Tower",
    "Eternal Singularity",
    "Eternal Starlight",
    "Extended Crafting",
    "Extreme Crafting",
    "Extreme Crafting Table",
    "Extreme Table",
    "FDBosses",
    "Flux Crafter",
    "Forlorn Hollows",
    "Forbidden Arcanus",
    "Fusion Crafting",
    "Guardian Crystals",
    "Hand Crank",
    "Hephaestus Forge",
    "Icebox",
    "Immersive Engineering",
    "Infernal Dragon",
    "Infinity Catalyst",
    "Infinity Ingot",
    "Kraken",
    "Kraken Ship",
    "Kraken Spawner",
    "Kraken Tooth",
    "Kraken Trident",
    "L_Ender's Cataclysm",
    "Launch Window",
    "Limbo",
    "Liquid Chaos",
    "Macabre",
    "Mahou Tsukai",
    "Malum",
    "Mechanical Mixer",
    "Mechanical Press",
    "Mekanism",
    "MineColonies",
    "Modern Industrialization",
    "Molten Salt Reactor",
    "Neo Vitae",
    "Nether Gauntlet",
    "Neutronium Collector",
    "Neutronium Compressor",
    "Occultism",
    "Oritech",
    "Otherside",
    "Overgeared",
    "Pedestals",
    "Perturbation",
    "PneumaticCraft",
    "Productive Metalworks",
    "Reactor Core",
    "Reactor Energy Injector",
    "Reactor Stabilizer",
    "Reactor Stabilizers",
    "Resonarium",
    "Scylla",
    "Shadows",
    "Smithing Anvil",
    "Soul Blacksmith",
    "Spectrum",
    "Stabilizers",
    "Sunken City",
    "Tabula Rasa",
    "Terracotta Bowl",
    "The Pit",
    "Theurgy",
    "Tidal Claws",
    "Ultimate Crafting Table",
    "Umvuthi, the Sunbird",
    "Undergarden",
    "Waterskin",
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be a JSON object")
    return data


def walk_refs(value: Any, refs: set[str]) -> None:
    if isinstance(value, dict):
        for child in value.values():
            walk_refs(child, refs)
    elif isinstance(value, list):
        for child in value:
            walk_refs(child, refs)
    elif isinstance(value, str) and value.startswith("book.aoa."):
        refs.add(value)


def collect_book_refs() -> tuple[dict[str, set[str]], dict[str, int]]:
    by_book: dict[str, set[str]] = defaultdict(set)
    counts = {"categories": 0, "entries": 0, "pages": 0, "text_pages": 0}

    for book in BOOKS:
        book_dir = BOOK_ROOT / book
        for path in book_dir.rglob("*.json"):
            data = load_json(path)
            rel = path.relative_to(book_dir).as_posix()
            if rel.startswith("categories/"):
                counts["categories"] += 1
            if rel.startswith("entries/"):
                counts["entries"] += 1
                pages = data.get("pages", [])
                if isinstance(pages, list):
                    counts["pages"] += len(pages)
                    counts["text_pages"] += sum(
                        1 for page in pages
                        if isinstance(page, dict) and page.get("type") == "modonomicon:text"
                    )
            refs: set[str] = set()
            walk_refs(data, refs)
            by_book[book].update(refs)

    return by_book, counts


def counter(pattern: re.Pattern[str], text: str) -> Counter[str]:
    return Counter(pattern.findall(text))


def strip_whitelist(text: str) -> str:
    stripped = text
    for phrase in sorted(WHITELIST_ENGLISH_FRAGMENTS, key=len, reverse=True):
        stripped = stripped.replace(phrase, "")
    stripped = re.sub(r"\b[a-z0-9_]+:[a-z0-9_./-]+\b", "", stripped)
    stripped = re.sub(r"\b[a-z]+_[a-z0-9_]+\b", "", stripped)
    return stripped


def is_allowed_english_only(value: str) -> bool:
    if value in ALLOWED_ENGLISH_ONLY_VALUES:
        return True
    if re.fullmatch(r"[A-Z0-9][A-Za-z0-9'’.,: /&+-]+", value):
        words = set(re.findall(r"[A-Za-z]+", value.lower()))
        common = {
            "the", "and", "or", "to", "from", "with", "where", "what", "why",
            "how", "build", "craft", "find", "use", "defeat", "complete",
        }
        return not bool(words & common)
    return False


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        en = load_json(EN)
        ru = load_json(RU)
        refs_by_book, structure_counts = collect_book_refs()
    except Exception as exc:  # noqa: BLE001 - CLI validator reports plain failures.
        print(f"ERROR: {exc}")
        return 1

    if len(en) != EXPECTED_KEYS:
        errors.append(f"EN key count is {len(en)}, expected {EXPECTED_KEYS}")
    if len(ru) != EXPECTED_KEYS:
        errors.append(f"RU key count is {len(ru)}, expected {EXPECTED_KEYS}")

    en_keys = set(en)
    ru_keys = set(ru)
    if en_keys != ru_keys:
        errors.append(
            "key set differs: "
            f"missing={sorted(en_keys - ru_keys)[:20]} "
            f"extra={sorted(ru_keys - en_keys)[:20]}"
        )

    all_refs = set().union(*refs_by_book.values())
    missing_en_refs = sorted(all_refs - en_keys)
    missing_ru_refs = sorted(all_refs - ru_keys)
    if missing_en_refs:
        errors.append(f"missing EN Modonomicon refs: {missing_en_refs[:50]}")
    if missing_ru_refs:
        errors.append(f"missing RU Modonomicon refs: {missing_ru_refs[:50]}")

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

    for key in sorted(all_refs & ru_keys):
        value = ru[key]
        if not isinstance(value, str):
            continue
        if MIXED_GLUE_RE.search(value):
            errors.append(f"{key}: possible Cyrillic/Latin glued word")
        if SPACE_BEFORE_PUNCT_RE.search(value):
            errors.append(f"{key}: space before punctuation")
        if DOUBLE_SPACE_RE.search(value):
            errors.append(f"{key}: double spaces")
        lowered = value.casefold()
        for phrase in BAD_TRANSLATIONS:
            if phrase.casefold() in lowered:
                errors.append(f"{key}: blacklisted machine translation: {phrase}")
        if not CYRILLIC_RE.search(value) and not is_allowed_english_only(value):
            errors.append(f"{key}: fully English value not whitelisted: {value!r}")
    print(f"EN keys: {len(en)}")
    print(f"RU keys: {len(ru)}")
    print(f"Keys match: {en_keys == ru_keys}")
    print(f"AOA Modonomicon book refs: {len(all_refs)}")
    for book in BOOKS:
        print(f"- {book}: {len(refs_by_book[book])} refs")
    print(f"Categories: {structure_counts['categories']}")
    print(f"Entries: {structure_counts['entries']}")
    print(f"Pages: {structure_counts['pages']}")
    print(f"Text pages: {structure_counts['text_pages']}")
    print(f"Missing EN refs: {len(missing_en_refs)}")
    print(f"Missing RU refs: {len(missing_ru_refs)}")

    if warnings:
        print(f"Warnings: {len(warnings)}")
        for warning in warnings[:100]:
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
