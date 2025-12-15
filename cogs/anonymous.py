from disnake import ApplicationCommandInteraction, Member
from disnake.ext import commands
from config import Configuration
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_anonymous_logger():
    logger = logging.getLogger("anonymous_messages")

    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    os.makedirs("logs", exist_ok=True)

    handler = RotatingFileHandler(
        "logs/anonymous_messages.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )

    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger


class Anonymous(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = setup_anonymous_logger()

    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="send_anonymous_dm", description="Have the bot send a DM to someone.")
    async def send_anonymous_dm(self, 
                                to_member: Member, 
                                direct_message: str = commands.Param(description="The anonymous message to send to the user"), 
                                interaction: ApplicationCommandInteraction = None):
        try:
            self.logger.info(
                "\n\tTYPE=DM"
                "\n\tFROM=%s (%s)"
                "\n\tTO=%s (%s)"
                "\n\tMESSAGE=%r",
                interaction.user.id,
                interaction.user.name,
                to_member.id,
                to_member.name,
                direct_message
            )

            await to_member.send(
                f"You have received an anonymous message:\n\n{direct_message}"
            )
            await interaction.response.send_message(
                "Your anonymous message has been sent!",
                ephemeral=True
            )

        except Exception:
            self.logger.exception(
                "Failed to send anonymous message FROM=%s TO=%s",
                interaction.user.id,
                to_member.id
            )
            await interaction.response.send_message(
                "Failed to send the anonymous message.",
                ephemeral=True
            )
    
    @commands.slash_command(
        guild_ids=[Configuration.instance().GUILD_ID],
        name="send_anonymous_channel_message",
        description="Post an anonymous message in this channel."
    )
    async def send_anonymous_channel_message(
        self,
        message: str = commands.Param(description="The anonymous message to send to this channel"),
        interaction: ApplicationCommandInteraction = None
    ):
        try:
            channel = interaction.channel

            self.logger.info(
                "\n\tTYPE=CHANNEL"
                "\n\tFROM=%s (%s)"
                "\n\tCHANNEL=%s (%s)"
                "\n\tMESSAGE=%r",
                interaction.user.id,
                interaction.user.name,
                channel.id,
                getattr(channel, "name", "DM"),
                message
            )

            await channel.send(
                f"📢 **Anonymous message:**\n\n{message}"
            )

            await interaction.response.send_message(
                "Your anonymous message has been posted.",
                ephemeral=True
            )

        except Exception:
            self.logger.exception(
                "Failed to send anonymous channel message FROM=%s CHANNEL=%s",
                interaction.user.id,
                interaction.channel.id if interaction.channel else "unknown",
            )
            await interaction.response.send_message(
                "Failed to post the anonymous message.",
                ephemeral=True
            )