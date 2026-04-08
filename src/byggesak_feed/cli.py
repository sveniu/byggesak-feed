import argparse
import logging
import sys
from pathlib import Path

from byggesak_feed.client import fetch_journals, get_list_id
from byggesak_feed.config import load_config
from byggesak_feed.feed import generate_feed
from byggesak_feed.filters import journal_matches
from byggesak_feed.state import load_state, save_state

log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch building cases and generate Atom feeds",
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    cfg = load_config(args.config)
    state_path = Path(cfg.state_file)
    state = load_state(state_path)

    seen_ids = set(state.get("seen_journal_ids", []))
    log.info("Loaded %d seen journal IDs from state", len(seen_ids))

    # Resolve list ID
    list_id = get_list_id(cfg.endpoint, cfg.list_title)
    log.info("List %r has ID %s", cfg.list_title, list_id)

    # Fetch new journals
    new_journals = fetch_journals(
        cfg.endpoint, list_id, seen_ids, cfg.max_pages
    )
    log.info("Fetched %d new journals", len(new_journals))

    # Add new IDs to seen set
    for j in new_journals:
        seen_ids.add(j["id"])
    state["seen_journal_ids"] = sorted(seen_ids)

    # Process each feed
    feed_states = state.get("feeds", {})
    for fc in cfg.feeds:
        matching = [j for j in new_journals if journal_matches(j, fc.filters)]
        log.info(
            "Feed %r: %d new matching journals", fc.id, len(matching)
        )

        # Merge with cached entries (new first, then old)
        cached = feed_states.get(fc.id, {}).get("entries", [])
        all_entries = matching + cached
        all_entries = all_entries[: fc.max_entries]

        # Update state cache
        feed_states.setdefault(fc.id, {})["entries"] = all_entries

        # Generate feed
        generate_feed(fc.title, all_entries, Path(fc.output))

    state["feeds"] = feed_states
    save_state(state_path, state)

    total_new = sum(
        len([j for j in new_journals if journal_matches(j, fc.filters)])
        for fc in cfg.feeds
    )
    log.info("Done. %d new matching entries across all feeds.", total_new)
