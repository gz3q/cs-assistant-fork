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

---

## Using it

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
  apps/           Entry points: dev_cli.py (working REPL), discord_bot.py
                  and api.py (stubs — logic lives in the services, not here)
  completions/    System prompt and completion_service.ask() — the function
                  that ties retrieval + LLM together
  config/         pydantic-settings (Settings), structlog setup, Celery config
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

The pipeline runs fully locally during development:

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
