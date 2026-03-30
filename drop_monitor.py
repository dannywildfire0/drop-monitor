"""
╔══════════════════════════════════════════════════════╗
║     DROP MONITOR — Target / Pokémon Center           ║
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
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

STATE: dict[str, str] = {}

# ──────────────────────────────────────────────
#  PRODUCTS TO MONITOR
# ──────────────────────────────────────────────

PRODUCTS = [

    # ═══════════════════════════════════════════
    #  TARGET — ASCENDED HEROES
    # ═══════════════════════════════════════════
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

    # ═══════════════════════════════════════════
    #  TARGET — PHANTASMAL FLAMES
    # ═══════════════════════════════════════════
    {
        "name": "Target — Phantasmal Flames Elite Trainer Box",
        "url": "https://www.target.com/p/pok-233-mon-trading-card-game-mega-evolution-8212-phantasmal-flames-elite-trainer-box/-/A-94860231",
        "site": "Target",
        "selector": "[data-test='addToCartButton']",
    },
    {
        "name": "Target — Phantasmal Flames ETB 2-Pack",
        "url": "https://www.target.com/p/pokemon-me2-phantasmal-flames-elite-trainer-boxes-2-pack/-/A-1007155435",
        "site": "Target",
        "selector": "[data-test='addToCartButton']",
    },
    {
        "name": "Target — Phantasmal Flames Booster Bundle",
        "url": "https://www.target.com/p/pok-233-mon-trading-card-game-mega-evolution-8212-phantasmal-flames-booster-bundle/-/A-94884496",
        "site": "Target",
        "selector": "[data-test='addToCartButton']",
    },
    {
        "name": "Target — Phantasmal Flames Pokémon Center ETB",
        "url": "https://www.target.com/p/pokemon-tcg-mega-evolution-phantasmal-flames-pok-mon-center-elite-trainer-box/-/A-1008343604",
        "site": "Target",
        "selector": "[data-test='addToCartButton']",
    },
    {
        "name": "Target — Phantasmal Flames Booster Display Box",
        "url": "https://www.target.com/p/-/A-95040142",
        "site": "Target",
        "selector": "[data-test='addToCartButton']",
    },
    {
        "name": "Target — Phantasmal Flames Booster Boxes 2-Pack",
        "url": "https://www.target.com/p/pokemon-me2-phantasmal-flames-booster-boxes-2-pack/-/A-1007155430",
        "site": "Target",
        "selector": "[data-test='addToCartButton']",
    },

    # ═══════════════════════════════════════════
    #  POKÉMON CENTER — PHANTASMAL FLAMES
    # ═══════════════════════════════════════════
    {
        "name": "Pokémon Center — Phantasmal Flames PC Elite Trainer Box",
        "url": "https://www.pokemoncenter.com/product/10-10186-109/pokemon-tcg-mega-evolution-phantasmal-flames-pokemon-center-elite-trainer-box",
        "site": "Pokémon Center",
        "selector": "button.add-to-cart",
    },
    {
        "name": "Pokémon Center — Phantasmal Flames Booster Bundle (6 Packs)",
        "url": "https://www.pokemoncenter.com/product/10-10191-109/pokemon-tcg-mega-evolution-phantasmal-flames-booster-bundle-6-packs",
        "site": "Pokémon Center",
        "selector": "button.add-to-cart",
    },
    {
        "name": "Pokémon Center — Phantasmal Flames Booster Display Box (36 Packs)",
        "url": "https://www.pokemoncenter.com/product/10-10190-119/pokemon-tcg-mega-evolution-phantasmal-flames-booster-display-box-36-packs",
        "site": "Pokémon Center",
        "selector": "button.add-to-cart",
    },

    # ═══════════════════════════════════════════
    #  POKÉMON CENTER — ASCENDED HEROES
    #  (add URLs here once announced)
    # ═══════════════════════════════════════════
    # {
    #     "name": "Pokémon Center — Ascended Heroes ETB",
    #     "url": "https://www.pokemoncenter.com/product/...",
    #     "site": "Pokémon Center",
    #     "selector": "button.add-to-cart",
    # },

    # ═══════════════════════════════════════════
    #  SUPREME — DISABLED (blocks bots)
    #  Re-enable manually on drop Thursdays
    # ═══════════════════════════════════════════
    # {
    #     "name": "Supreme New Drops",
    #     "url": "https://www.supremenewyork.com/shop/all",
    #     "site": "Supreme",
    #     "selector": "ul.table-photos",
    # },

]

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
#  PAGE CHECKER
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
