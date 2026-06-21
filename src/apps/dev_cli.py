import asyncio

from src.completions.services.completion_service import ask
from src.config.logger import get_logger
from src.infrastructure.db import async_session_factory
from src.infrastructure.db.repository import Repository
from src.retrieval.services import retrieval_service

log = get_logger(__name__)


async def _check_db() -> None:
    async with async_session_factory() as session:
        if not await Repository.has_chunks(session):
            print(
                "WARNING: The database has no chunks. Run `make ingest` first, "
                "or your questions will all be answered with 'I don't know'.\n"
            )


async def _print_db_status():
    async with async_session_factory() as session:
        count_sources, count_chunks = await Repository.get_source_and_chunk_counts(session)
    if count_chunks == 0:
        print(
            "WARNING: The database has no chunks. Run `make ingest` first, "
            "or your questions will all be answered with 'I don't know'.\n"
        )
    print(f"{count_sources} sources, {count_chunks} chunks loaded")


async def _repl() -> None:
    await _print_db_status()
    verbose = False  # flag for :verbose

    print("cs-assistant dev CLI. Type 'exit' or Ctrl-D to quit.\n")
    print("Type ':stats' or ':verbose' for cmds.\n")

    while True:
        try:
            question = input("ask> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return

        # :stats cmd
        if question.lower() in {":stats"}:
            await _print_db_status()
            continue

        # :verbose cmd
        if question.lower() in {":verbose"}:
            verbose = not verbose
            print(f"Verbose mode: {'ON' if verbose else 'OFF'}")
            continue

        # exit/quit cmd
        if question.lower() in {"exit", "quit"}:
            return
        if not question:
            continue

        try:
            answer = await ask(question)
        except Exception as e:
            print(f"\nError: {e}\n")
            continue

        # printing out chunk content (verbose mode)
        if verbose:
            retrieved_chunks = await retrieval_service.get_relevant_chunks(question)
            for chunk_item in retrieved_chunks:
                source_url = chunk_item.chunk.source_url
                similarity_score = chunk_item.score
                snippet = chunk_item.chunk.content[:250] + "[...]"
                print(f"URL: {source_url}")
                print(f"Similarity score: {similarity_score}")
                print(f"Content snippet: {snippet}")
                print("-" * 60)

        print(f"\n{answer.text}\n")
        if answer.sources:
            print("Sources:")
            for source in answer.sources:
                print(f"{source.url}")
        print()


def main() -> None:
    asyncio.run(_repl())


if __name__ == "__main__":
    main()
