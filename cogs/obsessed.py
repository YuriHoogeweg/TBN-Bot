import aiohttp
import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

from database.tbnbotdatabase import ObsessedPlayer, database_session
from utils.opendota import OPENDOTA_BASE, get_json
from utils.steam import convert_to_steam32


class ConfirmClearView(disnake.ui.View):
    def __init__(self, db_session, user_id: int):
        super().__init__(timeout=30)
        self.db_session = db_session
        self.user_id = user_id

    async def interaction_check(self, interaction: disnake.MessageInteraction) -> bool:
        if interaction.author.id != self.user_id:
            await interaction.response.send_message("This isn't your confirmation.", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="Confirm clear", style=disnake.ButtonStyle.danger)
    async def confirm(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        deleted = (
            self.db_session.query(ObsessedPlayer)
            .filter(ObsessedPlayer.discord_user_id == self.user_id)
            .delete()
        )
        self.db_session.commit()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"Cleared **{deleted}** entries from your obsessed list.",
            view=self,
        )
        self.stop()

    @disnake.ui.button(label="Cancel", style=disnake.ButtonStyle.secondary)
    async def cancel(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="Cancelled.", view=self)
        self.stop()


class ObsessedCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_session = database_session()

    @commands.slash_command(
        description="Add a Dota player to your personal obsessed list.",
    )
    async def add_obsessed(
        self,
        interaction: ApplicationCommandInteraction,
        steam_id: str,
        description: str = commands.Param(default=None, description="Optional note about this player"),
        name: str = commands.Param(default=None, description="Optional display name (fetched from OpenDota if omitted)"),
    ):
        """
        Add a Dota player to your personal obsessed list.
        Parameters
        ----------
        steam_id: Steam32 or Steam64 player ID (visible in your Dotabuff/OpenDota URL).
        description: Optional note for yourself about this player.
        name: Optional display name. If omitted, fetched from OpenDota.
        """
        await interaction.response.defer(ephemeral=True)

        try:
            steam32 = convert_to_steam32(int(steam_id))
        except (ValueError, TypeError):
            await interaction.edit_original_response(content=f"`{steam_id}` is not a valid Steam ID.")
            return

        resolved_name = name
        if resolved_name is None:
            try:
                async with aiohttp.ClientSession() as session:
                    profile = await get_json(session, f"{OPENDOTA_BASE}/players/{steam32}")
                resolved_name = (profile or {}).get("profile", {}).get("personaname")
            except Exception:
                resolved_name = None
            if not resolved_name:
                resolved_name = f"Player {steam32}"

        existing = (
            self.db_session.query(ObsessedPlayer)
            .filter(
                ObsessedPlayer.discord_user_id == interaction.author.id,
                ObsessedPlayer.steam32_id == steam32,
            )
            .first()
        )

        if existing:
            if description is not None:
                existing.description = description
            if name is not None or existing.name is None:
                existing.name = resolved_name
            self.db_session.commit()
            await interaction.edit_original_response(
                content=f"Updated **{existing.name}** in your obsessed list."
            )
        else:
            entry = ObsessedPlayer(
                discord_user_id=interaction.author.id,
                steam32_id=steam32,
                name=resolved_name,
                description=description,
            )
            self.db_session.add(entry)
            self.db_session.commit()
            await interaction.edit_original_response(
                content=f"Added **{resolved_name}** to your obsessed list."
            )

    @commands.slash_command(
        description="Remove a player from your obsessed list.",
    )
    async def remove_obsessed(
        self,
        interaction: ApplicationCommandInteraction,
        steam_id: str,
    ):
        """
        Remove a player from your obsessed list.
        Parameters
        ----------
        steam_id: Steam32 or Steam64 player ID.
        """
        try:
            steam32 = convert_to_steam32(int(steam_id))
        except (ValueError, TypeError):
            await interaction.response.send_message(f"`{steam_id}` is not a valid Steam ID.", ephemeral=True)
            return

        entry = (
            self.db_session.query(ObsessedPlayer)
            .filter(
                ObsessedPlayer.discord_user_id == interaction.author.id,
                ObsessedPlayer.steam32_id == steam32,
            )
            .first()
        )

        if not entry:
            await interaction.response.send_message(
                f"No entry for Steam32 `{steam32}` in your obsessed list.",
                ephemeral=True,
            )
            return

        removed_name = entry.name
        self.db_session.delete(entry)
        self.db_session.commit()
        await interaction.response.send_message(
            f"Removed **{removed_name}** from your obsessed list.",
            ephemeral=True,
        )

    @commands.slash_command(
        description="Clear your entire obsessed list (requires confirmation).",
    )
    async def clear_obsessed(self, interaction: ApplicationCommandInteraction):
        """Clear your entire obsessed list (requires confirmation)."""
        count = (
            self.db_session.query(ObsessedPlayer)
            .filter(ObsessedPlayer.discord_user_id == interaction.author.id)
            .count()
        )

        if count == 0:
            await interaction.response.send_message("Your obsessed list is already empty.", ephemeral=True)
            return

        view = ConfirmClearView(self.db_session, interaction.author.id)
        await interaction.response.send_message(
            f"Are you sure you want to clear all **{count}** entries from your obsessed list?",
            view=view,
            ephemeral=True,
        )

    @commands.slash_command(
        description="Show your personal obsessed list of Dota players.",
    )
    async def obsessed(
        self,
        interaction: ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(default=None, description="Whose list to show (defaults to you)"),
    ):
        """
        Show an obsessed list of Dota players.
        Parameters
        ----------
        member: Whose list to view. Defaults to your own.
        """
        target = member or interaction.author
        entries = (
            self.db_session.query(ObsessedPlayer)
            .filter(ObsessedPlayer.discord_user_id == target.id)
            .order_by(ObsessedPlayer.id.asc())
            .all()
        )

        if not entries:
            if target.id == interaction.author.id:
                msg = "Your obsessed list is empty. Use `/add_obsessed` to add a player."
            else:
                msg = f"{target.display_name} has no obsessed list yet."
            await interaction.response.send_message(msg, ephemeral=True)
            return

        lines = []
        for e in entries:
            name_link = f"**[{e.name}](https://dotabuff.com/players/{e.steam32_id})**"
            if e.description:
                lines.append(f"{name_link} — {e.description}")
            else:
                lines.append(name_link)
        embed = disnake.Embed(
            title=f"{target.display_name}'s obsessed list",
            description="\n".join(lines),
            color=disnake.Color.dark_red(),
        )
        await interaction.response.send_message(embed=embed)
