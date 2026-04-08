import logging

import requests

log = logging.getLogger(__name__)

JOURNALS_QUERY = """
query FetchMoreJournals($journalsLimit: Int!, $journalsOffset: Int, $journalsWhere: SearchJournalsWhere!, $journalProceedingWhere: JournalProceedingWhere, $journalDocumentsWhere: JournalDocumentsWhere!, $journalsOrderBy: SearchJournalsOrderBy) {
  journals: searchJournals(
    limit: $journalsLimit
    offset: $journalsOffset
    where: $journalsWhere
    proceedingWhere: $journalProceedingWhere
    orderBy: $journalsOrderBy
  ) {
    nodes {
      ...JournalResult
      __typename
    }
    __typename
  }
}

fragment JournalResult on Journal {
  id
  archiveId
  journalDate
  classified
  documentDate
  title
  sequenceNumber
  caseworkers
  senders
  unpublished
  recipients
  archiveSystem {
    id
    name
    __typename
  }
  department {
    id
    name
    __typename
  }
  status {
    id
    description
    name
    __typename
  }
  subArchive {
    id
    name
    __typename
  }
  type {
    id
    name
    description
    __typename
  }
  documents(where: $journalDocumentsWhere) {
    id
    classified
    title
    order
    type {
      id
      name
      __typename
    }
    __typename
  }
  proceeding {
    id
    sequenceNumber
    type {
      id
      name
      __typename
    }
    subArchive {
      id
      name
      __typename
    }
    propertyIdentifications {
      id
      useNr
      propertyNr
      __typename
    }
    __typename
  }
  __typename
}
""".strip()

LISTS_QUERY = """
query getLists {
  lists {
    id
    externalUrl
    title
    type
    __typename
  }
}
""".strip()


def get_list_id(endpoint: str, list_title: str) -> str:
    resp = requests.post(
        endpoint,
        json={
            "operationName": "getLists",
            "variables": {},
            "query": LISTS_QUERY,
        },
    )
    resp.raise_for_status()
    data = resp.json()

    for lst in data["data"]["lists"]:
        if lst["title"] == list_title:
            return lst["id"]

    available = [lst["title"] for lst in data["data"]["lists"]]
    raise ValueError(
        f"List {list_title!r} not found. Available: {available}"
    )


def _enrich_journal(journal: dict, list_id: str, base_url: str) -> dict:
    journal["url"] = (
        f"{base_url}/postjournal-v2/{list_id}"
        f"/proceedings/{journal['proceeding']['id']}"
    )
    for doc in journal.get("documents", []):
        doc["url"] = f"{base_url}/file/{doc['id']}"
    return journal


def fetch_journals(
    endpoint: str,
    list_id: str,
    seen_ids: set[str],
    max_pages: int,
) -> list[dict]:
    """Fetch journals, stopping on seen IDs, page exhaustion, or max_pages."""
    base_url = endpoint.rsplit("/", 1)[0]  # strip /graphql
    limit = 100
    all_journals = []

    for page in range(max_pages):
        offset = page * limit
        log.info("Fetching page %d (offset %d)", page + 1, offset)

        resp = requests.post(
            endpoint,
            json={
                "operationName": "FetchMoreJournals",
                "variables": {
                    "journalDocumentsWhere": {
                        "includeUnpublished": False,
                        "listId": list_id,
                    },
                    "journalsOffset": offset,
                    "journalsLimit": limit,
                    "journalsWhere": {
                        "listId": list_id,
                        "typeIdIn": [],
                        "search": "",
                        "journalFromDate": None,
                        "journalToDate": None,
                        "subArchiveId": "",
                        "includeUnpublished": False,
                    },
                    "journalProceedingWhere": {"typeIdIn": []},
                    "journalsOrderBy": "journalDate_DESC",
                },
                "query": JOURNALS_QUERY,
            },
        )
        resp.raise_for_status()
        nodes = resp.json()["data"]["journals"]["nodes"]

        hit_seen = False
        for journal in nodes:
            _enrich_journal(journal, list_id, base_url)
            if journal["id"] in seen_ids:
                hit_seen = True
            else:
                all_journals.append(journal)

        log.info(
            "Page %d: %d journals (%d new)",
            page + 1,
            len(nodes),
            sum(1 for j in nodes if j["id"] not in seen_ids),
        )

        if len(nodes) < limit:
            log.info("Last page (fewer than %d results)", limit)
            break
        if hit_seen:
            log.info("Hit previously seen journal ID, stopping pagination")
            break

    return all_journals
