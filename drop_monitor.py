"""
╔══════════════════════════════════════════════════════╗
║        DROP MONITOR — Supreme / Target               ║
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
# ──────────────────────────────────────────────

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
CHECK_INTERVAL = 30  # seconds between checks

# ──────────────────────────────────────────────
#  LOGGING
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("drop_monitor")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1",
    "Accept-Language": "en-US,en;q=0.9",
}
    "Accept-Language": "en-US,en;q=0.9",
}

STATE: dict[str, str] = {}

# ──────────────────────────────────────────────
#  TARGET PRODUCTS
# ──────────────────────────────────────────────

TARGET_PRODUCTS = [
    {
        "name": "Target — Ascended Heroes Elite Trainer Box",
        "url": "https://www.target.com/p/2025-pok-me2-5-elite-trainer-box/-/A-95082118",
        "site": "Target",
        "selector": "[data-test='addToCartButton']",
    },
    {
        "name": "Target — Ascended Heroes ETB 2-Pack",
        "url": "https://www.target.com/p/pokemon-me2-5-ascended-heroes-elite-trainer-box-2-pack/-/A-1009790687",
        "site": "Target",
        "selector": "[data-test='addToCartButton']",
    },
    {
        "name": "Target — Ascended Heroes First Partners Deluxe Pin Collection",
        "url": "https://www.target.com/p/pok-233-mon-trading-card-game-mega-evolution-ascended-heroes-first-partners-deluxe-pin-collection/-/A-95093989",
        "site": "Target",
        "selector": "[data-test='addToCartButton']",
    },
    {
        "name": "Target — Ascended Heroes Collection Larry",
        "url": "https://www.target.com/p/-/A-95173525",
        "site": "Target",
        "selector": "[data-test='addToCartButton']",
    },
]

# ── POKÉMON CENTER — DISABLED FOR NOW ─────────
# To re-enable, uncomment and add to check loop
# POKEMON_CENTER_PRODUCTS = [
#     {
#         "name": "Pokémon Center — Ascended Heroes ETB",
#         "url": "https://www.pokemoncenter.com/product/10-10315-108/...",
#         "site": "Pokémon Center",
#         "selector": "button.add-to-cart",
#     },
# ]

# ──────────────────────────────────────────────
#  DISCORD
# ──────────────────────────────────────────────

def send_discord(name: str, url: str, site: str) -> None:
    if not DISCORD_WEBHOOK_URL:
        log.error("DISCORD_WEBHOOK_URL is not set!")
        return

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    embed = {
        "embeds": [
            {
                "title": f"🚨 RESTOCK / DROP — {site}",
                "description": f"**{name}**\n{url}",
                "color": {
                    "Supreme":        0xED1C24,
                    "Pokémon Center": 0xFFCB05,
                    "Target":         0xCC0000,
                }.get(site, 0x00FF99),
                "footer": {"text": f"Drop Monitor • {ts}"},
                "url": url,
            }
        ]
    }
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=embed, timeout=10)
        if r.status_code in (200, 204):
            log.info(f"✅ Discord alert sent: {name}")
        else:
            log.error(f"Discord error {r.status_code}: {r.text}")
    except Exception as exc:
        log.error(f"Discord request failed: {exc}")


# ──────────────────────────────────────────────
#  SUPREME — JSON FEED (bypass bot detection)
#  Supreme exposes a product feed at /shop.json
#  We hash the list of product names/IDs so any
#  new item triggers an alert immediately.
# ──────────────────────────────────────────────

SUPREME_FEED_URL = "https://www.supremenewyork.com/mobile_stock.json"
SUPREME_STATE_KEY = "supreme_feed"

def check_supreme() -> None:
    try:
        resp = requests.get(SUPREME_FEED_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Build a fingerprint from all current product IDs + names
        products = data.get("products_and_categories", {})
        all_items = []
        for category, items in products.items():
            for item in items:
                all_items.append(f"{item.get('id')}:{item.get('name')}")

        all_items.sort()
        fp = hashlib.md5("|".join(all_items).encode()).hexdigest()
        prev = STATE.get(SUPREME_STATE_KEY)

        if prev is None:
            STATE[SUPREME_STATE_KEY] = fp
            log.info(f"📌 Baseline saved: Supreme feed ({len(all_items)} items)")
            return

        if fp != prev:
            log.info("🔥 CHANGE DETECTED: Supreme drop!")
            STATE[SUPREME_STATE_KEY] = fp
            send_discord(
                name="New Supreme Drop Detected — check the shop!",
                url="https://www.supremenewyork.com/shop/all",
                site="Supreme"
            )
        else:
            log.debug("No change: Supreme feed")

    except Exception as exc:
        log.warning(f"Supreme feed error: {exc}")


# ──────────────────────────────────────────────
#  TARGET — standard page scraping
# ──────────────────────────────────────────────

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


def check_product(product: dict) -> None:
    url = product["url"]
    html = fetch_element(url, product["selector"])
    if html is None:
        return

    fp = hashlib.md5(html.encode()).hexdigest()
    prev = STATE.get(url)

    if prev is None:
        STATE[url] = fp
        log.info(f"📌 Baseline saved: {product['name']}")
        return

    if fp != prev:
        log.info(f"🔥 CHANGE DETECTED: {product['name']}")
        STATE[url] = fp
        send_discord(product["name"], product["url"], product["site"])
    else:
        log.debug(f"No change: {product['name']}")


# ──────────────────────────────────────────────
#  MAIN LOOP
# ──────────────────────────────────────────────

def main() -> None:
    log.info("═" * 55)
    log.info("  DROP MONITOR STARTED")
    log.info(f"  Watching Supreme + {len(TARGET_PRODUCTS)} Target product(s) every {CHECK_INTERVAL}s")
    log.info("═" * 55)

    if not DISCORD_WEBHOOK_URL:
        log.warning("⚠️  DISCORD_WEBHOOK_URL not set — add it in Railway → Variables!")

    while True:
        check_supreme()
        for product in TARGET_PRODUCTS:
            check_product(product)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
