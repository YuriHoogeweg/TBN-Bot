from disnake import ChannelType, Member, ApplicationCommandInteraction, VoiceState
from disnake.ext import commands
from disnake.abc import GuildChannel
import humanize
from config import Configuration
from datetime import datetime
from database.tbnbotdatabase import JoinTime, database_session


class JoinTimeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_session = database_session()

    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="reset_jointimes", description="Reset a channel's join times")
    @commands.default_member_permissions(manage_guild=True)
    async def reset_jointimes(self, inter: ApplicationCommandInteraction, channel: GuildChannel = None):
        channel = channel or (
            inter.author.voice.channel if inter.author.voice is not None else None)

        if channel is None:
            self.db_session.query(JoinTime).delete()
            return await inter.response.send_message("All jointimes reset.", ephemeral=True)

        self.db_session.query(JoinTime).filter(
            JoinTime.channel_id == channel.id).delete()
        await inter.response.send_message(f"Jointimes for {channel.name} reset.", ephemeral=True)

    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="jointimes", description="Show who has been in a channel the longest")
    async def jointimes(self, inter: ApplicationCommandInteraction, channel: GuildChannel = None):
        channel = channel or (inter.author.voice.channel if inter.author.voice is not None else None)

        if channel is None:
            return await inter.response.send_message("You must be in a voice channel or specify the channel parameter.", ephemeral=True)
        
        channel_jointimes = self.db_session.query(JoinTime).filter(
            JoinTime.channel_id == channel.id).all()

        if len(channel_jointimes) < 1:
            return await inter.response.send_message("There's no one in this channel.", ephemeral=True)
        
        jointimes_display = "".join(
            [f"<@!{jointime.member_id}> {humanize.precisedelta(jointime.join_time, minimum_unit='minutes')} ago\n" for jointime in sorted(channel_jointimes, key=lambda x: x.join_time)])

        await inter.response.send_message(jointimes_display, ephemeral=True)

    # @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="testjointimes")
    # async def testjointimes(self, inter: ApplicationCommandInteraction, member: Member, before_channel: GuildChannel = None, after_channel: GuildChannel = None):
    #     await inter.response.defer()
    #     await self.move_user(member.id, after_channel.id)
    #     await inter.followup.send(f"Finished moving {member.name} from {before_channel.name} to {after_channel.name}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if member.bot:
            return

        to_channel_id = after.channel.id if after.channel is not None else None
        await self.move_user(member.id, to_channel_id)

    async def move_user(self, member_id: int, to_channel_id: int):
        # If user left a channel, remove their position in that channel's jointimes.        
        prev_join_time = self.db_session.query(JoinTime).filter(
            JoinTime.member_id == member_id).first()
        
        if prev_join_time != None and prev_join_time.channel_id != to_channel_id:
            self.db_session.delete(prev_join_time)
            
            if to_channel_id != None:
                self.db_session.add(JoinTime(member_id, to_channel_id, datetime.now()))
        elif prev_join_time == None:
            self.db_session.add(JoinTime(member_id, to_channel_id, datetime.now()))
        
        self.db_session.commit()    

    @commands.Cog.listener()
    async def on_ready(self):
        to_delete = self.db_session.query(JoinTime).all()
        
        # initialise channel jointimes for all voice channels that already have members sitting in them
        for guild in self.bot.guilds:
            for channel in guild.channels:
                if channel.type == ChannelType.voice:
                    for voice_state in channel.voice_states:                        
                        existing_entry = next((x for x in to_delete if x.member_id == voice_state), None)

                        # if user isn't in db or in db under a different channel, move them to the correct channel
                        if existing_entry is None or existing_entry.channel_id != channel.id:
                            await self.move_user(voice_state, channel.id)

                        to_delete.remove(existing_entry)

        for x in to_delete:
            self.db_session.delete(x)
            self.db_session.commit()

# Called by bot.load_extension in main
def setup(bot: commands.Bot):
    bot.add_cog(JoinTime(bot))