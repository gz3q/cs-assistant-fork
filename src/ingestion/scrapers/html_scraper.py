import httpx
import trafilatura

from src.config.logger import get_logger

log = get_logger(__name__)


def scrape(url: str) -> tuple[str, str | None]:
    """Fetch a URL and extract clean text + title.

    Returns (text, title). Title may be None if not found. Text may be empty
    if trafilatura couldn't extract anything; the caller should check and skip.
    """
    log.info("scrape_started", url=url)
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()

    # Known limitations (tracked as a separate ticket):
    #  - Misses content inside aria-hidden="true" accordions (common on FAQ pages)
    #  - Link formatting is markdown-style and may need cleanup downstream
    # Improving extraction quality is a tuning ticket, not a blocker for development.
    text = (
        trafilatura.extract(
            response.text,
            favor_recall=True,
            include_links=True,
            include_tables=True,
            include_formatting=False,
            include_comments=False,
            deduplicate=True,
            output_format="txt",
        )
        or ""
    )

    metadata = trafilatura.extract_metadata(response.text)
    title = metadata.title if metadata else None

    log.info("scrape_complete", url=url, chars=len(text), title=title)
    return text, title
