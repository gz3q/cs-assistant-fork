import asyncio

from src.completions.services.completion_service import ask
from src.config.logger import get_logger
from src.infrastructure.db import async_session_factory
from src.infrastructure.db.repository import Repository

log = get_logger(__name__)


async def _check_db() -> None:
    async with async_session_factory() as session:
        if not await Repository.has_chunks(session):
            print(
                "WARNING: The database has no chunks. Run `make ingest` first, "
                "or your questions will all be answered with 'I don't know'.\n"
            )


async def _repl() -> None:
    await _check_db()
    print("cs-assistant dev CLI. Type 'exit' or Ctrl-D to quit.\n")
    while True:
        try:
            question = input("ask> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return
        if question.lower() in {"exit", "quit"}:
            return
        if not question:
            continue

        try:
            answer = await ask(question)
        except Exception as e:
            print(f"\nError: {e}\n")
            continue

        print(f"\n{answer.text}\n")
        if answer.sources:
            print("Sources:")
            for source in answer.sources:
                print(f"  - {source.url}")
        print()


def main() -> None:
    asyncio.run(_repl())


if __name__ == "__main__":
    main()
