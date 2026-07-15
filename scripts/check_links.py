import asyncio
import json
import logging
import os
import random
import sys
import urllib.error
import urllib.request
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# REPO_ROOT works only if this script is in /scripts
REPO_ROOT = Path(__file__).resolve().parents[1]
URL_LIST_PATH_1 = REPO_ROOT / "data" / "webpages" / "test_list.json"
URL_LIST_PATH_2 = REPO_ROOT / "data" / "webpages" / "list.json"

BROKEN_STATUS_CODES = {404, 410}
WARNING_STATUS_CODES = {429, 403} | set(range(500, 600))
OKAY_STATUS_CODES = set(range(200, 300))

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}


def main():
    # webhook for the discord channel
    webhook = os.environ["DISCORD_WEBHOOK_URL"]
    # user id of the user we want to ping
    user_id = os.environ["USER_ID"]
    summary_path = os.environ["GITHUB_STEP_SUMMARY"]
    run_url = os.environ["RUN_URL"]
    event_name = os.environ.get("EVENT_NAME", "")

    urls = []
    broken_links = []
    # Unverifiable links <--> Warning links
    warning_links = []
    okay_links = []

    for path in (URL_LIST_PATH_1, URL_LIST_PATH_2):
        with open(path) as f:
            urls.extend(json.load(f))

    payload = asyncio.run(check(urls))

    for key, value in payload.items():
        match value:
            case _ if value in BROKEN_STATUS_CODES:
                broken_links.append(f"❌ **status code: {value}** | {key}")
            case _ if value in WARNING_STATUS_CODES:
                warning_links.append(f"🟨 **status code: {value}** | {key}")
            case _ if value in OKAY_STATUS_CODES:
                okay_links.append(f"🟩 **status code: {value}** | {key}")

    # for broken_links, this is the main shit
    # if broken_links and event_name == "schedule":
    #     broken_links.insert(0, f"<@{user_id}>, these links are broken! ⚠️")
    #     broken_links.append(f"<{run_url}|Here is the WORKFLOW!>")
    #     send_discord(webhook, broken_links)

    # to test the workflow, we will use the okay_links
    log.info("event_name=%s", event_name)
    log.info(
        "broken_links=%d unverifiable_links=%d okay_links=%d",
        len(broken_links),
        len(warning_links),
        len(okay_links),
    )

    print(f"event_name={event_name}")
    print(
        f"broken_links={len(broken_links)}"
        + "warning_links={len(warning_links)} okay_links={len(okay_links)}"
    )

    log.info("about to try discord send (diagnostic)")
    send_discord(webhook, ["test message ✅", f"event_name={event_name}"])

    if okay_links and event_name in ("schedule", "workflow_dispatch"):
        log.info("Sending Discord webhook with %d OK lines", len(okay_links))
        okay_links.insert(0, f"<@{user_id}>, these links are broken! ⚠️")
        okay_links.append(f"<{run_url}|Here is the WORKFLOW!>")
        send_discord(webhook, okay_links)

    with open(summary_path, "a", encoding="utf-8") as f:
        f.write(f"Broken: {broken_links}")
        f.write(f"Unverifiable: {warning_links}")
        f.write(f"OK: {okay_links}")

        if broken_links:
            sys.exit(1)
    # dict[str, int]
    # # for loop to go through
    # # 1. Broken (fail): 404, 410, Connection refused
    # # 2. Unverifiable (warn): 429, 5xx, 403
    # # 3. OK (N/A): 2xx
    #
    #
    #
    # payload.insert(0, f"<@{user_id}>, these links are returning a 404! Check these links.")
    #
    # if failed_urls:
    #     send_discord(webhook, payload)


# sends relevant info to webhook
def send_discord(webhook_url: str, content: list[str]):
    payload = {"content": "\n".join(content)}
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "link-checker/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            log.info("Discord status:", status=resp.status)
            log.info(resp.read().decode("utf-8", errors="ignore"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        log.error("Discord HTTPError:", error=e.code, response_body=body)
        raise


# run using asyncio.run(check(urls))
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
