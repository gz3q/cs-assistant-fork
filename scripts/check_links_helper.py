import asyncio
import json
import logging
import random
import urllib.error
import urllib.request

import httpx

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

BROKEN_STATUS_CODES = {404, 410}
WARNING_STATUS_CODES = {429, 403} | set(range(500, 600))
OKAY_STATUS_CODES = set(range(200, 300))

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}


# sends relevant info to webhook
def send_discord(webhook_url: str, content: list[str]):
    # Discord has a 2000 char limit - limiting content to <2000 chars
    # right now, if the content payload is >2000 chars, we can't send all the urls
    MAX_CONTENT = 2000

    joined = "\n".join(content)

    if not isinstance(joined, str):
        joined = str(joined)

    if len(joined) > MAX_CONTENT:
        final_str = "\nCheck the summary logs for more info!"
        joined = joined[: MAX_CONTENT - 3 - len(final_str)] + "..." + final_str

    # avoiding encoding issues if any
    joined = joined.encode("utf-8", errors="replace").decode("utf-8")

    payload = {"content": joined}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    log.info(
        "Discord POST bytes=%d content_chars=%d content_preview=%r",
        len(data),
        len(joined),
        joined[:120],
    )

    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "link-checker/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            log.info("Discord success status=%s body_len=%d", resp.status, len(body))
            if body:
                log.info("Discord body: %s", body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        log.error(
            "Discord HTTPError status=%s code=%s response_body=%s",
            getattr(e, "status", None),
            e.code,
            body,
        )
        raise
    except Exception as e:
        log.exception("Discord request failed with unexpected exception: %s", e)
        raise


# runs using asyncio.run(check(urls))
# concurrently runs and checks the status code, puts in a dict and returns
async def check(urls: list[str]) -> dict[str, int | None]:
    timeout = httpx.Timeout(10.0)
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers=DEFAULT_HEADERS,
    ) as client:
        tasks = [fetch_status_with_retries(url, client) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return dict(zip(urls, results))


# run with: asyncio.run(check_one(url))
async def fetch_status_with_retries(
    url: str,
    client: httpx.AsyncClient,
    *,
    retries: int = 2,  # total attempts = 1 + retries
    base_backoff_s: float = 0.5,
) -> int | None:
    attempt = 0
    while True:
        try:
            res = await client.get(url)
            status = res.status_code

            if status not in WARNING_STATUS_CODES:
                return status

            if attempt >= retries:
                return status

        except httpx.HTTPError:
            if attempt >= retries:
                return None

        # backoff
        backoff = base_backoff_s * (2**attempt)  # 0.5, 1.0, 2.0, ...
        backoff = backoff + random.uniform(0, 0.1)
        await asyncio.sleep(backoff)
        attempt += 1
