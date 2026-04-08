from byggesak_feed.config import FeedFilters


def journal_matches(journal: dict, filters: FeedFilters) -> bool:
    title_lower = journal["title"].lower()

    # title_exclude vetoes first
    if any(word in title_lower for word in filters.title_exclude):
        return False

    # If all filter groups are empty, pass everything through
    has_any_filter = (
        filters.title_include
        or filters.property_numbers
        or filters.case_sequence_numbers
        or filters.party_names
        or filters.proceeding_journal_types
    )
    if not has_any_filter:
        return True

    # OR across all filter groups
    if any(word in title_lower for word in filters.title_include):
        return True

    prop_ids = journal.get("proceeding", {}).get("propertyIdentifications", [])
    if any(
        p["propertyNr"] in filters.property_numbers for p in prop_ids
    ):
        return True

    seq = journal.get("proceeding", {}).get("sequenceNumber", "")
    if seq in filters.case_sequence_numbers:
        return True

    parties = journal.get("senders", []) + journal.get("recipients", [])
    for party in parties:
        party_lower = party.lower()
        if any(name in party_lower for name in filters.party_names):
            return True

    proc_type = journal.get("proceeding", {}).get("type", {}).get("name", "")
    journal_type = journal.get("type", {}).get("name", "")
    for pjt in filters.proceeding_journal_types:
        if proc_type == pjt.proceeding_type and journal_type == pjt.journal_type:
            return True

    return False
