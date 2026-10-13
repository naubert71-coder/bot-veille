"""Collecte des entrées RSS (flux classiques, PubMed, Google Alerts)."""
import re
from datetime import datetime, timedelta, timezone

import feedparser


def _normalize_title(title: str) -> str:
    """Clé de dédoublonnage : minuscules, sans ponctuation ni espaces multiples."""
    t = re.sub(r"[^a-z0-9 ]", "", title.lower())
    return re.sub(r"\s+", " ", t).strip()


def _pubmed_url(query_hash: str) -> str:
    return (
        f"https://pubmed.ncbi.nlm.nih.gov/rss/search/{query_hash}/"
        f"?limit=100&utm_campaign=pubmed-2"
    )


def _entry_to_text(title: str, link: str, summary: str, source: str, max_summary: int = 500) -> str:
    summary = (summary or "").strip()
    if len(summary) > max_summary:
        summary = summary[:max_summary].rsplit(" ", 1)[0] + "…"
    return (
        f"Source : {source}\n"
        f"Titre : {title}\n"
        f"Lien : {link}\n"
        f"Résumé : {summary}"
    )


def collect_sources(config: dict) -> list[str]:
    """Retourne la liste des textes d'entrées récentes, dédupliquées."""
    sources = config.get("sources", {})
    window_hours = config.get("output", {}).get("window_hours", 24)
    dedupe = config.get("triage", {}).get("dedupe", True)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

    # Rassemble toutes les URLs à parser, quel que soit le type de source.
    feed_urls: list[str] = []
    for item in sources.get("rss", []):
        feed_urls.append(item["url"])
    for url in sources.get("google_alerts", []):
        feed_urls.append(url)
    if sources.get("pubmed_query"):
        feed_urls.append(_pubmed_url(sources["pubmed_query"]))

    recent: list[str] = []
    seen_links: set[str] = set()
    seen_titles: set[str] = set()

    for feed_url in feed_urls:
        parsed = feedparser.parse(feed_url)

        if getattr(parsed, "bozo", 0):
            print(
                f"Avertissement : flux illisible ({feed_url}) — "
                f"{parsed.get('bozo_exception', 'raison inconnue')}"
            )
            continue

        source_name = parsed.feed.get("title", feed_url)

        for entry in parsed.entries:
            published = None
            if entry.get("published_parsed"):
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif entry.get("updated_parsed"):
                published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

            if not (published and published >= cutoff):
                continue

            title = entry.get("title", "Sans titre")
            summary = entry.get(
                "summary", entry.get("description", "Aucun résumé disponible.")
            )
            link = entry.get("link", "#")

            if dedupe:
                title_key = _normalize_title(title)
                if link in seen_links or (title_key and title_key in seen_titles):
                    continue
                seen_links.add(link)
                if title_key:
                    seen_titles.add(title_key)

            recent.append(_entry_to_text(title, link, summary, source_name))

    print(f"Collecte : {len(recent)} entrées récentes retenues.")
    return recent
