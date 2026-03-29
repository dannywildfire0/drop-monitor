"""
╔══════════════════════════════════════════════════════╗
║        DROP MONITOR — Supreme / PokéCenter / Target  ║
╚══════════════════════════════════════════════════════╝
"""

import os
import time
import hashlib
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ──────────────────────────────────────────────
#  CONFIG
#  DISCORD_WEBHOOK_URL is loaded from your Railway
#  environment variable — don't paste it here!
# ──────────────────────────────────────────────

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
CHECK_INTERVAL = 30  # seconds between checks

# ──────────────────────────────────────────────
#  PRODUCTS TO MONITOR
#  Replace the URLs with the actual pages you want.
# ──────────────────────────────────────────────

PRODUCTS = [
    # ── SUPREME ───────────────────────────────
    {
        "name": "Supreme New Drops (shop page)",
        "url": "https://www.supremenewyork.com/shop/all",
        "site": "Supreme",
        "selector": "ul.table-photos",
    },

    # ── POKÉMON CENTER ────────────────────────
    {
        "name": "Pokémon Center — Example Product",
        "url": "https://www.pokemoncenter.com/en-us/product/REPLACE_WITH_PRODUCT_SLUG",
        "site": "Pokémon Center",
        "selector": "button.add-to-cart",
    },

    # ── TARGET ────────────────────────────────
    {
        "name": "Target — Example Product",
        "url": "https://www.target.com/p/REPLACE_WITH_TARGET_PRODUCT",
        "site": "Target",
        "selector": "[data-test='addToCartButton']",
    },

    # ── ADD MORE HERE ──────────────────────────
    # {
    #     "name": "My Product",
    #     "url": "https://...",
    #     "site": "Shopify",
    #     "selector": ".product-form__submit",
    # },
]

# ──────────────────────────────────────────────
#  LOGGING — prints status to Railway's log view
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("drop_monitor")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

STATE: dict[str, str] = {}


def fetch_element(url: str, selector: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        el = soup.select_one(selector)
        return str(el) if el else resp.text[:2000]
    except Exception as exc:
        log.warning(f"Fetch error for {url}: {exc}")
        return None


def fingerprint(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def send_discord(product: dict) -> None:
    if not DISCORD_WEBHOOK_URL:
        log.error("DISCORD_WEBHOOK_URL is not set! Add it in Railway → Variables.")
        return

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    embed = {
        "embeds": [
            {
                "title": f"🚨 RESTOCK / DROP — {product['site']}",
                "description": f"**{product['name']}**\n{product['url']}",
                "color": {
                    "Supreme":        0xED1C24,
                    "Pokémon Center": 0xFFCB05,
                    "Target":         0xCC0000,
                }.get(product["site"], 0x00FF99),
                "footer": {"text": f"Drop Monitor • {ts}"},
                "url": product["url"],
            }
        ]
    }
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=embed, timeout=10)
        if r.status_code in (200, 204):
            log.info(f"✅ Discord alert sent: {product['name']}")
        else:
            log.error(f"Discord error {r.status_code}: {r.text}")
    except Exception as exc:
        log.error(f"Discord request failed: {exc}")


def check_product(product: dict) -> None:
    url = product["url"]
    html = fetch_element(url, product["selector"])
    if html is None:
        return

    fp = fingerprint(html)
    prev = STATE.get(url)

    if prev is None:
        STATE[url] = fp
        log.info(f"📌 Baseline saved: {product['name']}")
        return

    if fp != prev:
        log.info(f"🔥 CHANGE DETECTED: {product['name']}")
        STATE[url] = fp
        send_discord(product)
    else:
        log.debug(f"No change: {product['name']}")


def main() -> None:
    log.info("═" * 55)
    log.info("  DROP MONITOR STARTED")
    log.info(f"  Watching {len(PRODUCTS)} product(s) every {CHECK_INTERVAL}s")
    log.info("═" * 55)

    if not DISCORD_WEBHOOK_URL:
        log.warning("⚠️  DISCORD_WEBHOOK_URL not set — add it in Railway → Variables!")

    while True:
        for product in PRODUCTS:
            check_product(product)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
