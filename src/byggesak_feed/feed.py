import html
import logging
from pathlib import Path

from feedgen.feed import FeedGenerator

log = logging.getLogger(__name__)


def _build_entry_html(journal: dict) -> str:
    parts = []

    proc = journal.get("proceeding", {})
    proc_type = proc.get("type", {}).get("name", "")
    if proc_type:
        parts.append(f"<p><b>Sakstype:</b> {html.escape(proc_type)}</p>")

    journal_type_desc = journal.get("type", {}).get("description", "")
    if journal_type_desc:
        parts.append(f"<p><b>Journaltype:</b> {html.escape(journal_type_desc)}</p>")

    senders = journal.get("senders", [])
    if senders:
        parts.append(
            "<p><b>Avsender:</b> "
            + ", ".join(html.escape(s) for s in senders)
            + "</p>"
        )

    recipients = journal.get("recipients", [])
    if recipients:
        parts.append(
            "<p><b>Mottaker:</b> "
            + ", ".join(html.escape(r) for r in recipients)
            + "</p>"
        )

    props = proc.get("propertyIdentifications", [])
    if props:
        prop_strs = [
            f"{p['propertyNr']}/{p['useNr']}" for p in props
        ]
        parts.append(
            "<p><b>Eiendom:</b> " + ", ".join(prop_strs) + "</p>"
        )

    docs = journal.get("documents", [])
    if docs:
        parts.append("<p><b>Dokumenter:</b></p><ul>")
        for doc in docs:
            title = html.escape(doc.get("title", "Uten tittel"))
            url = html.escape(doc.get("url", ""))
            if url:
                parts.append(f'<li><a href="{url}">{title}</a></li>')
            else:
                parts.append(f"<li>{title}</li>")
        parts.append("</ul>")

    return "\n".join(parts)


def generate_feed(
    feed_title: str,
    entries: list[dict],
    output_path: Path,
) -> None:
    fg = FeedGenerator()
    fg.id(f"urn:byggesak-feed:{output_path.stem}")
    fg.title(feed_title)
    fg.link(href="https://asker-bygg.innsynsportal.no", rel="alternate")
    fg.logo(
        "https://asker-bygg.innsynsportal.no/postjournal-v2/postbyggassets/favicon.ico"
    )
    fg.subtitle(f"Byggesak-feed: {feed_title}")
    fg.language("no")

    for journal in entries:
        fe = fg.add_entry()
        fe.id(f"urn:byggesak-journal:{journal['id']}")

        seq = journal.get("proceeding", {}).get("sequenceNumber", "")
        title = journal.get("title", "")
        fe.title(f"{seq} - {title}" if seq else title)

        url = journal.get("url", "")
        if url:
            fe.link(href=url)

        journal_date = journal.get("journalDate", "")
        if journal_date:
            fe.published(journal_date)
            fe.updated(journal_date)

        fe.content(_build_entry_html(journal), type="html")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fg.atom_file(str(output_path), pretty=True)
    log.info("Wrote %d entries to %s", len(entries), output_path)
