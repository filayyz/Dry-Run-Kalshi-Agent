## Kalshi Dry-Run Trading Agent

This project runs a **dry-run trading loop** against Kalshi election markets. It:
- Fetches a subset of open markets from Kalshi.
- Sends them to a Groq-hosted model (`qwen-qwq-32b`) for analysis.
- Logs **recommended trades** (YES/NO/PASS) **without placing real orders**.

Live trading is **not implemented yet**. The `DRY_RUN` flag in `kalshi_agent.py` is set to `True` and should stay that way until you explicitly add and test order placement.

### Project status

- **Current mode**: Dry run only (no real trades).
- **Risk controls**: Basic confidence filter and logging; no capital/risk limits implemented yet.
- **Security**: Secrets are expected in a local `.env` file that is **not committed** to version control.

### Setup

1. **Create and activate a virtual environment (recommended)**

```bash
python -m venv venv
source venv/bin/activate  # on macOS/Linux
# .\venv\Scripts\activate  # on Windows (PowerShell)
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Create your `.env` file (do not commit it)**

Create a file named `.env` in the project root with content like:

```bash
GROQ_API_KEY=your_groq_api_key_here
# Optional: override the default Groq model
# Check https://console.groq.com/ for the latest supported Qwen models
GROQ_MODEL=qwen-2-72b
KALSHI_API_KEY_ID=your_kalshi_key_id_here
KALSHI_PRIVATE_KEY_PATH=./kalshi_private_key.pem
# Optional: Discord webhook for notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_id/your_webhook_token
```

> Keep real keys and private key files out of git and any public repo. The provided `.gitignore` is configured to ignore `.env` and `kalshi_private_key.pem`.

### Running the agent (dry run)

From the project root, with your virtual environment activated:

```bash
python kalshi_agent.py
```

The agent will:
- Log startup configuration (model, dry-run status).
- In a loop:
  - Fetch up to `MAX_MARKETS` markets from the Kalshi elections API.
  - Ask the model for JSON-formatted trade recommendations.
  - Log potential trades as `[DRY RUN]` entries.

You can adjust the polling interval by changing `interval_seconds` in the `run_agent` call inside `kalshi_agent.py`. By default it is 300 seconds (5 minutes).

If `DISCORD_WEBHOOK_URL` is set in your `.env`, the agent will also:
- Send a startup message when it begins running.
- Send a Discord message for each dry-run trade decision that passes the confidence filter.

### Configuration notes

- `DRY_RUN` is currently **hard-coded to `True`** in `kalshi_agent.py`. Do not change this to `False` until:
  - You have implemented authenticated Kalshi order placement.
  - You have added proper risk controls (position limits, loss limits, etc.).
- The agent requires a valid `GROQ_API_KEY` in your environment; if it is missing, the script will fail fast rather than attempting to run without access to the model.
- The Groq model used by the agent is controlled by the `GROQ_MODEL` environment variable; if not set, it defaults to `qwen-2-72b`. You can change this to any currently supported Groq Qwen model.

### Going beyond dry run (future work)

Before enabling live trading, consider adding:
- Authenticated Kalshi order placement using `KALSHI_API_KEY_ID` and `KALSHI_PRIVATE_KEY_PATH`.
- Position sizing and risk limits (per-market and global).
- Robust JSON validation and error handling for model responses.
- Metrics/monitoring and alerting for failures or unusual behavior.

