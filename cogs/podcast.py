from disnake import Member, ApplicationCommandInteraction
import disnake
from disnake.ext import commands
from config import Configuration

class PodcastCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="podcast_reset", description="Remove all podcast participants")
    async def podcast_reset(self, inter: ApplicationCommandInteraction):
        role = inter.guild.get_role(Configuration.instance().PODCAST_PARTICIPANT_ROLE_ID)

        # Remove existing podcast participants
        for member in role.members:
            if member.id != inter.author.id:
                await member.remove_roles(role)

        await inter.response.send_message("Removed all other podcast participants.", ephemeral=True,
                                          components=[disnake.ui.Button(style=disnake.ButtonStyle.green, label="Hide podcast channel", custom_id="podcast_hide")])

    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="podcast_addparticipants", description="Add podcast participants")
    async def podcast_addparticipants(self, inter: ApplicationCommandInteraction, participant1: Member, participant2: Member = None, participant3: Member = None, participant4: Member = None):
        all_participants = [participant1,
                            participant2, participant3, participant4]
        all_participants = [participant for participant in all_participants if participant is not None]

        role = inter.guild.get_role(Configuration.instance().PODCAST_PARTICIPANT_ROLE_ID)

        for member in all_participants:
            await member.add_roles(role)

        await inter.response.send_message(f"Added the following podcast participant(s):\n{chr(10).join([x.mention for x in all_participants])}\nDon't forget to enable streamer mode before you start :)",
                                          ephemeral=True,
                                          components=[disnake.ui.Button(style=disnake.ButtonStyle.green, label="Reveal podcast channel", custom_id="podcast_reveal")])

    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="podcast_revealchannel", description="Reveal podcast channel")
    async def podcast_revealchannel(self, inter: ApplicationCommandInteraction):
        social_channel = self.bot.get_channel(
            Configuration.instance().SOCIAL_CATEGORY_ID)
        podcast_channel = self.bot.get_channel(
            Configuration.instance().PODCAST_CHANNEL_ID)

        # Move podcast channel to bottom of social category
        await podcast_channel.move(end=True, category=social_channel)
        await inter.response.send_message("Moved podcast channel to social category", ephemeral=True)

    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="podcast_hidechannel", description="Hide podcast channel")
    async def podcast_hidechannel(self, inter: ApplicationCommandInteraction):
        archive_channel = self.bot.get_channel(Configuration.instance().ARCHIVE_CATEGORY_ID)
        podcast_channel = self.bot.get_channel(Configuration.instance().PODCAST_CHANNEL_ID)

        # Move podcast channel to bottom of archive category
        await podcast_channel.move(end=True, category=archive_channel)
        await inter.response.send_message("Moved podcast channel to archive category", ephemeral=True)

    @commands.Cog.listener('on_button_click')
    async def button_listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "podcast_reveal":
            await self.podcast_revealchannel(inter)
        elif inter.component.custom_id == "podcast_hide":
            await self.podcast_hidechannel(inter)


# Called by bot.load_extension in main
def setup(bot: commands.Bot):
    bot.add_cog(PodcastCog(bot))
