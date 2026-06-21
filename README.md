# cs-assistant

A RAG-based assistant for Carleton University CS students. It answers questions
about the CS program by searching a curated set of Carleton web pages, citing
its sources in every answer, and politely refusing rather than guessing when it
can't find a grounded answer.

---

## Prerequisites

Install these before the setup steps below.

**uv** (package + Python version manager)
https://docs.astral.sh/uv/getting-started/installation/
uv will install Python 3.12 automatically if you don't have it.

**Docker**
- Mac / Windows: https://docs.docker.com/desktop/
- Linux servers: https://docs.docker.com/engine/install/

**Ollama** (local model runner)
https://ollama.com/download

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/CarletonComputerScienceSociety/cs-assistant.git
cd cs-assistant
```

### 2. Pull the Ollama models

Models are listed at https://ollama.com/library. Pull both before running
anything else — the embedding model is required for `make ingest` and the chat
model is required for `make cli`.

```bash
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

Ollama must be running in the background (`ollama serve`, or the desktop app
keeps it running automatically).

### 3. Copy the environment file

```bash
cp .env.example .env
```

The defaults in `.env.example` match the Docker services below and work
out-of-the-box on most machines. Review these values:

| Variable | Default | When to change |
|---|---|---|
| `DATABASE_URL` | `...@localhost:5445/cs_assistant` | If you change Postgres port |
| `OLLAMA_CHAT_MODEL` | `llama3.2:3b` | Switch to `llama3.2:1b` if inference is slow on your machine|
| `TOP_K` | `3` | Raise after you have more pages ingested |

**If local inference is slow or requests are timing out:** switch to the
smaller model in `.env`:

```
OLLAMA_CHAT_MODEL=llama3.2:1b
```

Then pull it: `ollama pull llama3.2:1b`. `TOP_K=3` is already set low for
this reason — leave it there.

### 4. Install dependencies

```bash
make setup
```

This runs `uv sync`, which installs all runtime and dev dependencies into a
local virtual environment. You do not need to activate it; all `make` commands
prefix their commands with `uv run`.

### 5. Enable git pre-commit hooks

```bash
uv run pre-commit install
```

This is a one-time step per clone. The hook configuration is committed
(`.pre-commit-config.yaml`), but the actual git hook is local. After this,
ruff and black run automatically on every `git commit`.

If a hook auto-fixes files, the commit is aborted and the fixes are left
unstaged. Just `git add` the changed files and commit again — this is expected
behaviour, not an error.

### 6. Start Docker services

```bash
docker compose up -d
```

This starts:
- **postgres** — `pgvector/pgvector:pg17` on port **5445** (not 5432, to avoid
  clashing with a local Postgres install)
- **redis** — `redis/redis-stack-server` on port **6370** (not 6379, same
  reason)

The postgres init script also creates the `cs_assistant_test` database used by
the test suite.

Check services are up:

```bash
docker compose ps
```

### 7. Run migrations

```bash
make migrate
```

This runs Alembic against `DATABASE_URL`, enabling the `pgvector` extension and
creating the `sources` and `chunks` tables. You must run this before ingesting.

### 8. Ingest the curated pages

```bash
make ingest
```

Scrapes, chunks, embeds, and stores all URLs listed in
`data/webpages/list.json`. You'll see structured log output for each URL.
Re-running is safe — unchanged content is skipped.

### 9. Ask a question

```bash
make cli
```

Opens a REPL. Type a question and press Enter. Ctrl-D or `exit` to quit.

```
ask> what electives should I take for a software engineering focus?
```

You should see an answer followed by a `Sources:` block listing the URLs used.

### 10. (Optional) Run the Discord bot

The bot exposes the same Q&A flow as `make cli` through a `/ask` slash command,
so it needs the full backend already working: Docker up, `make migrate` and
`make ingest` run, and Ollama serving. The CLI is enough for most development —
this step is only needed if you're working on the bot itself.

You'll need your own throwaway Discord server and bot to develop against:

1. In the [Discord Developer Portal](https://discord.com/developers/applications),
   create an application, then under **Bot** click **Reset Token** and copy the
   token. No privileged intents are required — `/ask` uses default intents.
2. Under **OAuth2 → URL Generator**, select the `bot` and `applications.commands`
   scopes, open the generated URL, and invite the bot to a server you own.
3. Enable **Settings → Advanced → Developer Mode**, then right-click your server
   icon → **Copy Server ID**.
4. Add both values to your `.env`:

   ```
   DISCORD_BOT_TOKEN=your_token_here
   DISCORD_GUILD_ID=your_server_id_here
   ```

5. Start the bot:

   ```bash
   make discord
   ```

`/ask` is synced to your server on startup, so it appears immediately. Invoking
it defers the reply (Discord's 3-second ack), then sends the answer and its
sources as a follow-up once `ask()` finishes — expect the same 1–3 minute local
latency as the CLI. If the token or server ID is missing, the bot exits at
startup with a message.

---

## Using it

While inside the interactive CLI (`ask>`), you can use the following commands to control the session and view metadata:
| Command | Description |
| :--- | :--- |
| `:stats` | Quick check on how many sources and chunks are loaded in the DB. |
| `:verbose` | Toggles verbose mode. On every query, it'll dump the retrieved chunks (URLs, match scores, and snippets) right before the response. |
| `exit` or `quit` | Safely terminates the interactive session and returns to your terminal shell. (You can also use `Ctrl-D`). |

A grounded answer looks like this:

```
For a software engineering focus, the CCSS recommends...

Sources:
  - https://ccss.carleton.ca/resources/articles/which-electives-should-i-take/
```

If you ask something outside the bot's knowledge base (a greeting, a question
about a different university, anything not in the ingested pages), the model
follows its system prompt and declines to answer rather than fabricating a
response. If the database is empty (you haven't run `make ingest` yet), the CLI
will warn you and every question will return:

```
I don't have any information about that in my sources.
```

The citation and abstain behaviour is intentional — it is the whole point of
the grounding approach.

---

## Make commands

Every command runs through `uv run`, so you never need to activate the venv.

| Command | What it does |
|---|---|
| `make setup` | `uv sync` — install all runtime + dev dependencies |
| `make migrate` | Apply Alembic migrations (enable pgvector, create tables) |
| `make ingest` | Scrape, chunk, embed, and store every URL in `list.json` |
| `make cli` | Open the question REPL against the ingested data |
| `make discord` | Run the Discord bot (`/ask` slash command) — see setup step 10 |
| `make lint` | Run ruff (lint only, no changes) |
| `make format` | Run black (rewrites files in place) |
| `make test` | Run the pytest suite (requires Docker running) |

## Running checks locally

Run these before pushing to match what CI will check:

```bash
# Lint (ruff)
make lint

# Format (black — rewrites files in place)
make format

# Full pre-commit pass — same as what CI runs in the lint job
uv run pre-commit run --all-files

# Tests
make test
```

The test suite requires Docker to be running (it hits the `cs_assistant_test`
Postgres database). Tests use savepoint-based rollback, so each test is
isolated and the schema is never dropped between runs.

---

## Project structure

```
src/
  apps/           Entry points: dev_cli.py (working REPL) and discord_bot.py
                  (stub — logic lives in the services, not here)
  completions/    System prompt and completion_service.ask() — the function
                  that ties retrieval + LLM together
  config/         pydantic-settings (Settings), logging setup, Celery config
  domain/         Shared types: Chunk, RetrievedChunk, Source, Answer
  infrastructure/
    db/           SQLAlchemy models, Alembic migrations (versions/), repository
    llm.py        Ollama HTTP client — embed() and chat()
  ingestion/      html_scraper.py, ingestion_service.ingest_url(),
                  ingest_task.py (Celery stub)
  retrieval/      embedding_service.py, retrieval_service.get_relevant_chunks()

scripts/
  ingest.py       One-off runner: reads data/webpages/list.json → ingest_url()

data/
  webpages/
    list.json     The curated URL list — add pages here to expand the knowledge base

tests/            Mirrors src/ layout. DB-layer tests today; ingestion/retrieval
                  tests are a known gap.
docker/
  postgres-init/  SQL run at container start — creates the cs_assistant_test DB
```

---

## Tech stack

- **Python 3.12+**, managed with [uv](https://docs.astral.sh/uv/)
- **Ollama** — local LLM inference (chat + embeddings, no API key needed)
- **PostgreSQL 17 + pgvector** — vector store, run via Docker
- **SQLAlchemy (async) + asyncpg** — database access layer
- **Alembic** — schema migrations (raw SQL, no ORM-generated DDL)
- **Redis** — task queue backing (Dockerized; not yet wired to a worker)
- **langchain-text-splitters** — recursive character chunker
- **httpx + trafilatura** — HTTP scraping and text extraction
- **ruff + black** — linting and formatting
- **pytest + pytest-asyncio** — test suite

---

## How it works

The pipeline runs fully locally during development. Ingestion happens offline
(populating the vector store); querying happens per question and reuses the same
embedding model so questions and chunks live in the same vector space.

1. **Ingest** — a curated list of URLs (`data/webpages/list.json`) is scraped
   with httpx + trafilatura, split into ~1500-character chunks with 200-character
   overlap, embedded via Ollama (`nomic-embed-text`), and stored in Postgres
   with pgvector. Re-running is idempotent: chunks are identified by a SHA-256
   content hash, so unchanged content is skipped.

2. **Retrieve** — on a question, the question is embedded with the same model,
   and the top-k most similar chunks are fetched from Postgres using cosine
   distance.

3. **Complete** — the retrieved chunks are formatted into a context block and
   sent to an Ollama chat model (`llama3.2:3b`). The system prompt instructs the
   model to answer using only the provided sources and to say so when it can't.
   Every answer includes the source URLs used.

Hosted production deployment is a future goal. Today everything runs on your
machine.

---

## Notes for contributors

A few things worth keeping in mind:

- **Make sure to install the pre-commit hook after cloning** (`uv run pre-commit install`).
  Without it, ruff and black won't run on
  commit, and CI will fail on formatting you could have caught locally.
- **Auto-fixes abort the commit on purpose.** When a hook reformats a file, the
  commit stops and the changes are left unstaged. Re-`git add` the files and
  commit again — this is expected, not a failure.
- **Don't change `src/domain/types.py` without discussing it first.** The shared
  domain types (`Chunk`, `RetrievedChunk`, `Source`, `Answer`) are a contract
  that every layer depends on — the repository, retrieval, and completions all
  convert at that boundary. Open an issue before touching it so the change can be
  coordinated across layers.

## Troubleshooting / known constraints

**Inference is slow or requests time out.**
Switch `OLLAMA_CHAT_MODEL` to `llama3.2:1b` in `.env` and pull it
(`ollama pull llama3.2:1b`). `TOP_K=3` is already set low for this reason.

**CLI warns "database has no chunks".**
You need to run `make ingest` before `make cli`. If you have run ingest and
still see the warning, confirm Docker is running and that `make migrate` has
been applied.

**Queries take 1–3 minutes locally on CPU, or time out at 5 minutes.**
This is a dev-machine constraint, not a production concern. The hosted
deployment will use a GPU-capable server. Follow steps listed in setup instructions to use a smaller model locally.

**Some content may be missing in the scraped output.**
The scraper uses static HTML extraction (trafilatura). Pages that load content
via JavaScript or hide it in other ways (such as Carleton's slideme accordion widget) may return
incomplete text. A more thorough scraper is a tracked enhancement.
