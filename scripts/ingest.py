import asyncio
import json
from pathlib import Path

from src.config import settings
from src.config.logger import get_logger
from src.ingestion.services.ingestion_service import ingest_url

log = get_logger(__name__)

# Defaults to the full curated list. Override via .env to ingest a smaller subset
# for faster local iteration: INGEST_URL_LIST=data/webpages/test_list.json
URL_LIST_PATH = Path(settings.ingest_url_list)


async def main() -> None:
    with open(URL_LIST_PATH) as f:
        urls = json.load(f)

    log.info("ingest_run_started", n_urls=len(urls))

    for url in urls:
        try:
            await ingest_url(url)
        except Exception as e:
            log.error("ingest_url_failed", url=url, error=str(e))
            continue

    log.info("ingest_run_complete")


if __name__ == "__main__":
    asyncio.run(main())
