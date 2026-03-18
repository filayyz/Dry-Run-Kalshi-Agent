import os
import json
import time
import logging
from datetime import datetime
from typing import Optional

import requests
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("KalshiAgent")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_WEBHOOK_URL: Optional[str] = os.getenv("DISCORD_WEBHOOK_URL")

# Default to a current Qwen model on Groq; can be overridden via env
MODEL = os.getenv("GROQ_MODEL", "qwen-2-72b")
MAX_MARKETS = 10
MIN_CONFIDENCE = 0.65
MAX_POSITION_CENTS = 500
DRY_RUN = True  # keep this True while the agent is in dry-run mode

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set. Please configure it in your environment or .env file.")

groq_client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = "You are an expert prediction market trader on Kalshi. Analyze markets and decide whether to trade YES, NO, or PASS. Prices are in cents (1-99). Only recommend a trade if you have strong conviction above 65% confidence. Respond ONLY with valid JSON and nothing else. Response format: {markets: [{ticker: string, action: YES or NO or PASS, confidence: 0.0-1.0, estimated_probability: 0.0-1.0, reasoning: string, recommended_price_cents: 1-99}]}"


def notify_discord(message: str) -> None:
    """
    Send a simple text message to Discord using a webhook.
    Fails quietly if DISCORD_WEBHOOK_URL is not configured or the request errors.
    """
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        payload = {"content": message}
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        if resp.status_code >= 400:
            log.warning(f"Discord notification failed with status {resp.status_code}: {resp.text}")
    except Exception as e:
        log.warning(f"Discord notification error: {e}")

def get_kalshi_markets():
    import requests
    try:
        headers = {"accept": "application/json"}
        resp = requests.get(
            "https://api.elections.kalshi.com/trade-api/v2/markets",
            headers=headers,
            params={"status": "open", "limit": MAX_MARKETS}
        )
        data = resp.json()
        markets = []
        for m in data.get("markets", []):
            markets.append({
                "ticker": m.get("ticker"),
                "title": m.get("title"),
                "yes_bid": m.get("yes_bid"),
                "yes_ask": m.get("yes_ask"),
                "no_bid": m.get("no_bid"),
                "no_ask": m.get("no_ask"),
                "volume": m.get("volume"),
                "close_time": str(m.get("close_time")),
            })
        log.info(f"Fetched {len(markets)} markets")
        return markets
    except Exception as e:
        log.error(f"Failed to fetch markets: {e}")
        return []

def analyze_markets(markets):
    if not markets:
        return []
    user_message = f"Today is {datetime.now().strftime('%Y-%m-%d')}. Analyze these Kalshi prediction markets and return trading decisions as JSON:\n{json.dumps(markets, indent=2)}"
    try:
        log.info("Sending markets to Qwen via Groq...")
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=2048,
        )
        raw = response.choices[0].message.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        return parsed.get("markets", [])
    except Exception as e:
        log.error(f"AI error: {e}")
        notify_discord(f"Kalshi agent AI error: {e}")
        return []

def execute_trade(decision):
    ticker = decision.get("ticker")
    action = decision.get("action")
    confidence = decision.get("confidence", 0)
    price = decision.get("recommended_price_cents", 50)
    reasoning = decision.get("reasoning", "")

    if action == "PASS":
        log.info(f"[PASS] {ticker}")
        return

    if confidence < MIN_CONFIDENCE:
        log.info(f"[SKIP] {ticker} - confidence {confidence:.0%} too low")
        return

    if DRY_RUN:
        msg = f"[DRY RUN] {action} on {ticker} @ {price}c | confidence {confidence:.0%} | {reasoning}"
        log.info(msg)
        notify_discord(msg)
    else:
        log.info(f"[LIVE] Would place real order here - integrate Kalshi auth to enable")
        notify_discord(f"[LIVE] Would place real order for {ticker} ({action} @ {price}c, {confidence:.0%} conf) - trading not yet implemented")

def run_agent(interval_seconds=300):
    log.info("Kalshi Trading Agent starting...")
    log.info(f"Model: {MODEL} | Dry run: {DRY_RUN}")
    if DISCORD_WEBHOOK_URL:
        notify_discord(f"Kalshi agent started. Model={MODEL}, dry_run={DRY_RUN}, max_markets={MAX_MARKETS}")
    else:
        log.info("DISCORD_WEBHOOK_URL not set; Discord notifications are disabled.")
    while True:
        log.info(f"Cycle starting at {datetime.now().strftime('%H:%M:%S')}")
        markets = get_kalshi_markets()
        decisions = analyze_markets(markets)
        for decision in decisions:
            execute_trade(decision)
        log.info(f"Cycle complete. Sleeping {interval_seconds}s...")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    run_agent()