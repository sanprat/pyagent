# Pyagent

Pyagent is a thin deployment wrapper for running [Hermes Agent](https://hermes-agent.org/) in Docker on a VPS.

This repo does not reimplement Hermes. It packages a clean Docker Compose deployment with:

- Hermes Agent in a dedicated container
- a local OpenAI-compatible proxy for OpenRouter model fallback
- persistent Hermes state under `./data/hermes`
- OpenRouter for LLM access
- Tavily for web search
- Telegram bot connectivity
- a repo layout that is safe to push to GitHub

## What this setup gives you

- isolated containerized deployment
- persistent memory/config across restarts
- simple `docker compose` lifecycle
- no secrets committed to git
- web UI for chat, terminal, memory, skills, and files

## Repo layout

```text
.
├── .env.example
├── .gitignore
├── docker-compose.yml
├── LICENSE
├── README.md
├── docker/
│   ├── agent/
│   │   └── Dockerfile
│   └── workspace/
│       ├── .dockerignore
│       └── Dockerfile
├── proxy/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
└── scripts/
    └── container-entrypoint.sh
```

## Prerequisites on the VPS

- Docker Engine installed
- Docker Compose plugin installed
- outbound internet access from the VPS/container
- an OpenRouter API key
- a Tavily API key
- optionally, a Brave Search API key
- a Telegram bot token from `@BotFather`

## Setup

Clone the repo on the VPS and enter it:

```bash
git clone https://github.com/sanprat/pyagent.git
cd pyagent
```

Create your environment file:

```bash
cp .env.example .env
```

Edit `.env` and fill in:

- `OPENROUTER_API_KEY`
- `TAVILY_API_KEY`
- `BRAVE_SEARCH_API_KEY` if you want a backup search provider available
- `TELEGRAM_BOT_TOKEN`
- `PYAGENT_PROXY_API_KEY`

This repo also includes standby values for OpenRouter model rotation:

- `OPENROUTER_MODEL_PRIMARY=qwen/qwen3.6-plus:free`
- `OPENROUTER_MODEL_FALLBACK_1=nvidia/nemotron-3-super-120b-a12b:free`
- `OPENROUTER_MODEL_FALLBACK_2=arcee-ai/trinity-large-preview:free`
- `OPENROUTER_MODEL_FALLBACK_3=stepfun/step-3.5-flash:free`

The proxy exposes an OpenAI-compatible endpoint for Hermes at:

- base URL: `http://openrouter-proxy:8000/v1`
- API key: whatever you set in `PYAGENT_PROXY_API_KEY`

## First-time Hermes initialization

Build the proxy and agent images:

```bash
docker compose build openrouter-proxy
docker compose build hermes-agent
```

Start the proxy first:

```bash
docker compose up -d openrouter-proxy
```

Run the Hermes model/setup wizard inside the container:

```bash
docker compose run --rm hermes-agent hermes setup
```

During setup:

- choose `Custom API` or the OpenAI-compatible custom endpoint option
- set base URL to `http://openrouter-proxy:8000/v1`
- set API key to the value of `PYAGENT_PROXY_API_KEY`
- set model to `qwen/qwen3.6-plus:free`
- if Hermes asks for search tooling, provide the Tavily key

The proxy will automatically retry fallback models in order if the primary model hits rate limits or transient upstream failures.

Then configure messaging:

```bash
docker compose run --rm hermes-agent hermes gateway setup
```

During gateway setup:

- choose `Telegram`
- paste the bot token from `@BotFather`

Because `/root/.hermes` is mounted to `./data/hermes`, that configuration survives container recreation.

## Start the agent

After setup is complete:

```bash
docker compose up -d
```

Check logs:

```bash
docker compose logs -f hermes-agent
```

Stop it:

```bash
docker compose down
```

Restart it:

```bash
docker compose restart hermes-agent
```

## Web UI (Hermes Workspace)

Pyagent now includes a web UI powered by [Hermes Workspace](https://github.com/outsourc-e/hermes-workspace).

Features: chat with SSE streaming, file browser, terminal, memory browser, skills browser, 8 themes.

Access at `http://<your-vps-ip>:3000` after setup.

### First-time setup with workspace

```bash
# 1. Build all images and start proxy + agent
docker compose build
docker compose up -d openrouter-proxy hermes-agent

# 2. Run Hermes setup (interactive)
docker compose run --rm hermes-agent hermes setup
#    - choose Custom API / OpenAI-compatible endpoint
#    - set base URL: http://openrouter-proxy:8000/v1
#    - set API key: your PYAGENT_PROXY_API_KEY value
#    - set model: google/gemma-4-31b-it:free

# 3. Configure Telegram gateway (optional)
docker compose run --rm hermes-agent hermes gateway setup

# 4. Enable HTTP API for the workspace
docker compose exec hermes-agent sh -c 'echo "API_SERVER_ENABLED=true" >> /root/.hermes/.env'

# 5. Restart agent and start workspace
docker compose restart hermes-agent
docker compose up -d

# 6. Open http://<your-vps-ip>:3000
```

> Port 3000 must be open on your VPS firewall for the web UI.

### Password protection (optional)

To require a password for the web UI, add to your `.env`:

```
HERMES_PASSWORD=your_password_here
```

## Suggested VPS deployment flow

Keep Pyagent in its own project directory on the VPS and run it as its own Compose project. That keeps upgrades, secrets, and persistent state easier to manage.

If you later need Pyagent to talk to other services, connect them through an explicit Docker network rather than combining multiple services into one container.

## Recommended operational notes

- Keep `.env` private and never commit it.
- Back up `./data/hermes` because it contains the Hermes profile, memory, and gateway state.
- Pin `PYAGENT_IMAGE` to a specific tag once you are happy with a release.
- Start with a lightweight OpenRouter model and upgrade only if the agent quality is not enough.

## OpenRouter model choices

This repo keeps four OpenRouter model IDs in `.env` and uses them directly in the local proxy:

- primary model: `qwen/qwen3.6-plus:free`
- fallback 1: `nvidia/nemotron-3-super-120b-a12b:free`
- fallback 2: `arcee-ai/trinity-large-preview:free`
- fallback 3: `stepfun/step-3.5-flash:free`

For Tavily, use a single `TAVILY_API_KEY`.

The proxy tries the configured model first and then walks the fallback chain on upstream rate limits and transient server errors. Successful primary-model calls should be nearly as fast as a direct API call because the proxy only adds a local network hop on your VPS.

Important date note:

- OpenRouter currently marks `arcee-ai/trinity-large-preview:free` as going away on April 10, 2026, so treat it as a short-lived fallback rather than a stable long-term choice.

## Search provider option

This repo also includes an optional `BRAVE_SEARCH_API_KEY` in `.env` so you can keep Brave Search available as a standby provider.

Current Brave Search pricing I verified on April 6, 2026:

- Search API pricing is listed as `$5 per 1,000 requests`
- Brave also says it includes `$5 in free monthly credits`

Important limit:

- I did not verify official Hermes documentation showing a native Brave Search provider or automatic search-provider failover.
- So for this repo, Brave should be treated as a backup option you can switch to if Tavily usage becomes a problem, not an automatic fallback.

Brave references:

- https://brave.com/search/api/
- https://api-dashboard.search.brave.com/documentation/pricing

## Commands to do the needful on the VPS

```bash
git clone https://github.com/sanprat/pyagent.git
cd pyagent
cp .env.example .env
nano .env
docker compose build
docker compose up -d openrouter-proxy hermes-agent
docker compose run --rm hermes-agent hermes setup
docker compose run --rm hermes-agent hermes gateway setup
docker compose exec hermes-agent sh -c 'echo "API_SERVER_ENABLED=true" >> /root/.hermes/.env'
docker compose restart hermes-agent
docker compose up -d
docker compose logs -f hermes-agent
```

## Notes on Hermes

This wrapper is based on Hermes Agent by Nous Research. Hermes provides Docker support, OpenRouter support, and multi-platform gateway support including Telegram, according to the official project site:

- https://hermes-agent.org/
- https://nousresearch.com/hermes-agent/
- https://hub.docker.com/r/nousresearch/hermes-agent

## License

This repository is licensed under PolyForm Noncommercial 1.0.0. See [LICENSE](LICENSE).
