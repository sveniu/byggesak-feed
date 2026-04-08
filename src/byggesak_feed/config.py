from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ProceedingJournalType:
    proceeding_type: str
    journal_type: str


@dataclass
class FeedFilters:
    title_include: list[str] = field(default_factory=list)
    title_exclude: list[str] = field(default_factory=list)
    property_numbers: list[int] = field(default_factory=list)
    case_sequence_numbers: list[str] = field(default_factory=list)
    party_names: list[str] = field(default_factory=list)
    proceeding_journal_types: list[ProceedingJournalType] = field(
        default_factory=list
    )


@dataclass
class FeedConfig:
    id: str
    title: str
    output: str
    filters: FeedFilters
    max_entries: int = 200


@dataclass
class Config:
    endpoint: str
    list_title: str
    state_file: str
    max_pages: int
    feeds: list[FeedConfig]


def load_config(path: Path) -> Config:
    with open(path) as f:
        raw = yaml.safe_load(f)

    feeds = []
    for fc in raw["feeds"]:
        raw_filters = fc.get("filters", {})
        pjt = [
            ProceedingJournalType(
                proceeding_type=p["proceeding_type"],
                journal_type=p["journal_type"],
            )
            for p in raw_filters.get("proceeding_journal_types", [])
        ]
        filters = FeedFilters(
            title_include=[
                w.lower() for w in raw_filters.get("title_include", [])
            ],
            title_exclude=[
                w.lower() for w in raw_filters.get("title_exclude", [])
            ],
            property_numbers=raw_filters.get("property_numbers", []),
            case_sequence_numbers=raw_filters.get(
                "case_sequence_numbers", []
            ),
            party_names=[
                n.lower() for n in raw_filters.get("party_names", [])
            ],
            proceeding_journal_types=pjt,
        )
        feeds.append(
            FeedConfig(
                id=fc["id"],
                title=fc["title"],
                output=fc["output"],
                filters=filters,
                max_entries=fc.get("max_entries", 200),
            )
        )

    return Config(
        endpoint=raw["endpoint"],
        list_title=raw["list_title"],
        state_file=raw.get("state_file", "state.json"),
        max_pages=raw.get("max_pages", 50),
        feeds=feeds,
    )
