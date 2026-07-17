import asyncio
import json
from pathlib import Path

# import httpx
from .check_links_helper import (
    send_discord,
    check,
    log,
    BROKEN_STATUS_CODES,
    WARNING_STATUS_CODES,
    OKAY_STATUS_CODES,
)

# from . import check_links_helper

# log = check_links_helper.log

# REPO_ROOT works only if this script is in /scripts
REPO_ROOT = Path(__file__).resolve().parents[1]
URL_LIST_PATH_1 = REPO_ROOT / "data" / "webpages" / "test_list.json"
URL_LIST_PATH_2 = REPO_ROOT / "data" / "webpages" / "list.json"


def main():
    # webhook for the discord channel
    # webhook = os.environ["DISCORD_WEBHOOK_URL"]
    # # user id of the user we want to ping
    # user_id = os.environ["USER_ID"]
    # summary_path = os.environ["GITHUB_STEP_SUMMARY"]
    # run_url = os.environ["RUN_URL"]
    # event_name = os.environ.get("EVENT_NAME", "")
    webhook = "https://discord.com/api/webhooks/1527025316776644718/WkpJPomRhTaIyz7qf9BIoC6E_X8sisPqarsGDrevWAnqI_wMtcusXVJFGvzTGJzNbVpg"
    user_id = "1523427702571536500"
    # hardcoded event_name
    event_name = "schedule"

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

    if okay_links and event_name in ("schedule", "workflow_dispatch"):
        log.info("Sending Discord webhook with %d OK lines", len(okay_links))
        okay_links.insert(0, f"<@{user_id}>, these links are broken! ⚠️")
        # okay_links.append(f"<{run_url}|Here is the WORKFLOW!>")
        send_discord(webhook, okay_links)

    # with open(summary_path, "a", encoding="utf-8") as f:
    #     f.write(f"Broken: {broken_links}")
    #     f.write(f"Unverifiable: {warning_links}")
    #     f.write(f"OK: {okay_links}")
    #
    #     if broken_links:
    #         sys.exit(1)


if __name__ == "__main__":
    main()
