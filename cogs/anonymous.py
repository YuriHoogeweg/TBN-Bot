import random
from disnake import ApplicationCommandInteraction, Member
from disnake.ext import commands
from config import Configuration
import logging
from logging.handlers import RotatingFileHandler
import os
from collections import deque
from datetime import datetime, timezone
import disnake
from disnake.ext import commands

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
        self.recent = deque(maxlen=5)

    # @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="send_anonymous_dm", description="Have the bot send a DM to someone.")
    # async def send_anonymous_dm(self, 
    #                             to_member: Member, 
    #                             direct_message: str = commands.Param(description="The anonymous message to send to the user"), 
    #                             interaction: ApplicationCommandInteraction = None):
    #     try:
    #         self.logger.info(
    #             "\n\tTYPE=DM"
    #             "\n\tFROM=%s (%s)"
    #             "\n\tTO=%s (%s)"
    #             "\n\tMESSAGE=%r",
    #             interaction.user.id,
    #             interaction.user.name,
    #             to_member.id,
    #             to_member.name,
    #             direct_message
    #         )
            
    #         now = datetime.now(timezone.utc)
    #         self.recent.append({
    #             "ts": now,
    #             "type": "DM",
    #             "from_id": interaction.user.id,
    #             "from_name": interaction.user.name,
    #             "target_id": to_member.id,
    #             "target_name": to_member.name,
    #             "where_id": None,
    #             "where_name": None,
    #             "message": direct_message,
    #         })

    #         await to_member.send(
    #             f"You have received an anonymous message:\n\n{direct_message}"
    #         )
    #         await interaction.response.send_message(
    #             "Your anonymous message has been sent!",
    #             ephemeral=True
    #         )

    #     except Exception:
    #         self.logger.exception(
    #             "Failed to send anonymous message FROM=%s TO=%s",
    #             interaction.user.id,
    #             to_member.id
    #         )
    #         await interaction.response.send_message(
    #             "Failed to send the anonymous message.",
    #             ephemeral=True
    #         )
    
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
            now = datetime.now(timezone.utc)
            channel = interaction.channel
            self.recent.append({
                "ts": now,
                "type": "CHANNEL",
                "from_id": interaction.user.id,
                "from_name": interaction.user.name,
                "target_id": None,
                "target_name": None,
                "where_id": channel.id if channel else None,
                "where_name": getattr(channel, "name", None),
                "message": message,
            })
            
            eligible_members = [
                m for m in getattr(channel, "members", [])
                if m.status != disnake.Status.offline and not m.bot
            ]

            random_member = random.choice(eligible_members) if eligible_members else None
            if random_member:
                footer_name = random_member.display_name
            else:
                footer_name = "a server member"
                
            embed = disnake.Embed(
                title="📢 Anonymous message",
                description=message,
                color=disnake.Color.dark_grey(),
            )
            embed.set_footer(
                text=f"Sent anonymously via the server bot by {footer_name} • Abuse may be investigated"
            )

            await interaction.channel.send(embed=embed,
                                           allowed_mentions=disnake.AllowedMentions(users=False))

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
            
    @commands.slash_command(
        guild_ids=[Configuration.instance().GUILD_ID],
        name="anon_last5",
        description="Show the last 5 anonymous messages (admin only).",
    )
    async def anon_last5(self, interaction: ApplicationCommandInteraction):
        if not self.recent:
            return await interaction.response.send_message(
                "No anonymous messages recorded since the bot started.",
                ephemeral=True
            )

        embed = disnake.Embed(
            title="Last 5 Anonymous Messages",
            description="Most recent first. Times are UTC.",
        )

        for i, entry in enumerate(reversed(self.recent), start=1):
            ts = entry["ts"].strftime("%Y-%m-%d %H:%M:%S")
            from_part = f'{entry["from_name"]} ({entry["from_id"]})'
            if entry["type"] == "DM":
                where_part = f'DM → {entry["target_name"]} ({entry["target_id"]})'
            else:
                where_part = f'#{entry["where_name"]} ({entry["where_id"]})'

            # keep fields from getting too huge
            msg = entry["message"]
            if len(msg) > 900:
                msg = msg[:900] + "…"

            embed.add_field(
                name=f"{i}) {entry['type']} | {ts}",
                value=f"**From:** {from_part}\n**To:** {where_part}\n**Message:**\n{msg}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)
