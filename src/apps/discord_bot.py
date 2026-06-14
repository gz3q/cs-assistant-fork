import sys

import discord
from discord import app_commands

from src.completions.services.completion_service import ask
from src.config import settings
from src.config.logger import get_logger

log = get_logger(__name__)


class CsAssistantBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self) -> None:
        guild = discord.Object(id=settings.discord_guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        log.info("discord_ready", self_user=self.user, guild=settings.discord_guild_id)


client = CsAssistantBot()


@client.tree.command(name="ask", description="Receive advice for Carleton CS")
@app_commands.describe(question="Your question")
async def ask_command(interaction: discord.Interaction, question: str) -> None:
    await interaction.response.defer()
    log.info("discord_ask_received", interaction_id=interaction.id, question=question)

    try:
        answer = await ask(question=question)
    except Exception as e:
        await interaction.followup.send(
            "❌ I couldn't process this request, please try again later."
        )
        log.error("discord_ask_failed", interaction_id=interaction.id, error=str(e))
        return

    content = answer.text
    if answer.sources:
        content += "\n\n**Sources:**\n" + "\n".join(f"• {source.url}" for source in answer.sources)

    await interaction.followup.send(content)
    log.info("discord_ask_completed", interaction_id=interaction.id)


if __name__ == "__main__":
    if settings.discord_bot_token is None or settings.discord_guild_id is None:
        print("Discord config is incomplete or nonexistent", file=sys.stderr)
        sys.exit(1)

    client.run(settings.discord_bot_token)
