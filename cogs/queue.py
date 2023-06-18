from disnake import ChannelType, Member, ApplicationCommandInteraction, VoiceState
from disnake.ext import commands
from disnake.abc import GuildChannel
from config import Configuration
from datetime import datetime, timedelta

birthday_input_format = '%d/%m/%Y'
birthday_output_format = '%d %B'


class Queue(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_queues = dict(dict())

    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="reset_queue", description="Reset a queue")
    @commands.default_member_permissions(manage_guild=True)
    async def reset_queue(self, inter: ApplicationCommandInteraction, channel: GuildChannel = None):        
        channel = channel or inter.author.voice.channel if inter.author.voice is not None else None

        if channel is None:
            self.channel_queues = dict(dict())
            return await inter.response.send_message("All queues reset.", ephemeral=True)
        
        self.channel_queues[channel.id] = dict()
        await inter.response.send_message(f"Queue for {channel.name} reset.", ephemeral=True)

    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="show_queue", description="Show who's in queue")
    async def show_queue(self, inter: ApplicationCommandInteraction, channel: GuildChannel = None):
        await inter.response.defer()
        channel = channel or inter.author.voice.channel if inter.author.voice is not None else None

        if channel is None:
            return await inter.followup.send("You must be in a voice channel to use this command without explicit channel parameter.")

        if channel.id not in self.channel_queues or len(self.channel_queues[channel.id]) < 1:
            return await inter.followup.send("There is no queue for this channel.")

        queue = self.channel_queues[channel.id]
        #queue = dict({1078760423714730016: datetime.now(), 986670041460252723: datetime.now() + timedelta(minutes=-5), 516721359875735560: datetime.now() + timedelta(days=-5)})

        now = datetime.now()
        queue_positions = "".join(
            [f"<@!{position[0]}> {self.pretty_date(now, position[1])}\n" for position in sorted(queue.items(), key=lambda x: x[1])])

        await inter.followup.send(queue_positions)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if member.bot:
            return

        # If user left a channel, remove their position in that channel's queue.
        if before.channel is not None and after.channel.id != before.channel.id and self.channel_queues.get(before.channel.id) is not None:
            self.channel_queues[before.channel.id].pop(member.id, None)

        channel = self.channel_queues.setdefault(after.channel.id, dict())
        channel.setdefault(member.id, datetime.now())

    @commands.Cog.listener()
    async def on_ready(self):
        # initialise channel queues for all voice channels that already have members sitting in them
        for guild in self.bot.guilds:
            for channel in guild.channels:
                if channel.type == ChannelType.voice:
                    self.channel_queues.setdefault(channel.id, dict())
                    for voice_state in channel.voice_states:
                        self.channel_queues[channel.id].setdefault(voice_state, datetime.now())

    def pretty_date(self, now: datetime, time=False):
        if type(time) is int:
            diff = now - datetime.fromtimestamp(time)
        elif isinstance(time, datetime):
            diff = now - time
        elif not time:
            diff = 0
        second_diff = diff.seconds
        day_diff = diff.days

        if day_diff < 0:
            return ''

        if day_diff == 0:
            if second_diff < 10:
                return "just now"
            if second_diff < 60:
                return str(second_diff) + " seconds ago"
            if second_diff < 120:
                return "a minute ago"
            if second_diff < 3600:
                return str(second_diff // 60) + " minutes ago"
            if second_diff < 7200:
                return "an hour ago"
            if second_diff < 86400:
                return str(second_diff // 3600) + " hours ago"
        if day_diff == 1:
            return "Yesterday"
        if day_diff < 7:
            return str(day_diff) + " days ago"
        if day_diff < 31:
            return str(day_diff // 7) + " weeks ago"
        if day_diff < 365:
            return str(day_diff // 30) + " months ago"
        return str(day_diff // 365) + " years ago"

# Called by bot.load_extension in main
def setup(bot: commands.Bot):
    bot.add_cog(Queue(bot))
