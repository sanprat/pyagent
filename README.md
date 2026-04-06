# Pyagent

Pyagent is a thin deployment wrapper for running [Hermes Agent](https://hermes-agent.org/) in Docker on a VPS.

This repo does not reimplement Hermes. It packages a clean Docker Compose deployment with:

- Hermes Agent in a dedicated container
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

## Repo layout

```text
.
├── .env.example
├── .gitignore
├── docker-compose.yml
├── LICENSE
├── README.md
└── scripts/
    └── container-entrypoint.sh
```

## Prerequisites on the VPS

- Docker Engine installed
- Docker Compose plugin installed
- outbound internet access from the VPS/container
- an OpenRouter API key
- a Tavily API key
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
- `TELEGRAM_BOT_TOKEN`

## First-time Hermes initialization

Pull the image:

```bash
docker compose pull
```

Run the Hermes model/setup wizard inside the container:

```bash
docker compose run --rm pyagent hermes setup
```

During setup:

- choose `OpenRouter` as the provider
- use your OpenRouter key
- pick the model you want Hermes to use
- if Hermes asks for search tooling, provide the Tavily key

Then configure messaging:

```bash
docker compose run --rm pyagent hermes gateway setup
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
docker compose logs -f pyagent
```

Stop it:

```bash
docker compose down
```

Restart it:

```bash
docker compose restart pyagent
```

## Suggested VPS deployment flow

Keep Pyagent in its own project directory on the VPS and run it as its own Compose project. That keeps upgrades, secrets, and persistent state easier to manage.

If you later need Pyagent to talk to other services, connect them through an explicit Docker network rather than combining multiple services into one container.

## Recommended operational notes

- Keep `.env` private and never commit it.
- Back up `./data/hermes` because it contains the Hermes profile, memory, and gateway state.
- Pin `PYAGENT_IMAGE` to a specific tag once you are happy with a release.
- Start with a lightweight OpenRouter model and upgrade only if the agent quality is not enough.

## Commands to do the needful on the VPS

```bash
git clone https://github.com/sanprat/pyagent.git
cd pyagent
cp .env.example .env
nano .env
docker compose pull
docker compose run --rm pyagent hermes setup
docker compose run --rm pyagent hermes gateway setup
docker compose up -d
docker compose logs -f pyagent
```

## Notes on Hermes

This wrapper is based on Hermes Agent by Nous Research. Hermes provides Docker support, OpenRouter support, and multi-platform gateway support including Telegram, according to the official project site:

- https://hermes-agent.org/
- https://nousresearch.com/hermes-agent/
- https://hub.docker.com/r/nousresearch/hermes-agent

## License

This repository is licensed under PolyForm Noncommercial 1.0.0. See [LICENSE](LICENSE).
