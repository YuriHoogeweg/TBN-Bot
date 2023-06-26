import datetime
from disnake import ui, Embed, ApplicationCommandInteraction
from disnake.ext import commands
import humanize
from config import Configuration


class Major(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Register as slash command - pass in Guild ID so command changes propagate immediately
    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name='major', description='Major info post with various links to resources')
    async def berlin_major(self, interaction: ApplicationCommandInteraction):
        embed = Embed(
            title='Bali Major 2023',
            type='rich',
            color=0xf8bf38
        )

        dotabuff_emoji = Configuration.instance().DOTABUFF_EMOJI
        twitch_emoji = Configuration.instance().TWITCH_EMOJI
        liquipedia_emoji = Configuration.instance().LIQUIPEDIA_EMOJI

        major_start_time = datetime.datetime.utcfromtimestamp(1688004000)
        time_until_major = humanize.precisedelta(major_start_time - datetime.datetime.utcnow(), minimum_unit='minutes')

        embed.add_field(name='Group stage',
                        value=f'June 29th to July 3rd (in {time_until_major})',
                        inline=False)
        embed.add_field(name='Playoffs',
                        value='July 5th to July 9th',
                        inline=False)
        # embed.add_field(name='Sweepstakes Teams',
        #                 value='[Post](https://discord.com/channels/296709532070182912/777332475243266099/1099801369931686049)',
        #                 inline=False)

        liquipedia_buttons = [
            ui.Button(label='Liquipedia Page', 
                      row=0,
                      url='https://liquipedia.net/dota2/Bali_Major/2023',
                      emoji=liquipedia_emoji),
            ui.Button(label='Teams',
                      row=0,
                      url='https://liquipedia.net/dota2/Bali_Major/2023#Participants',
                      emoji=liquipedia_emoji),
            ui.Button(label='Group Stage Standings',
                      row=0,
                      url='https://liquipedia.net/dota2/Bali_Major/2023#Group_A',
                      emoji=liquipedia_emoji),
            # ui.Button(label='Group Stage Matches',
            #           row=0,
            #           url='https://liquipedia.net/dota2/ESL_One/Berlin_Major/2023/Group_Stage#Matches',
            #           emoji=liquipedia_emoji),
            ui.Button(label='Playoffs Bracket',
                      row=0,
                      url='https://liquipedia.net/dota2/Bali_Major/2023#Playoffs',
                      emoji=liquipedia_emoji)]

        stream_buttons = [
            ui.Button(label='EpulzeGaming',
                      row=1,
                      url='https://www.twitch.tv/epulzegaming',
                      emoji=twitch_emoji),
            ui.Button(label='EpulzeEN',
                      row=1,
                      url='https://www.twitch.tv/EpulzeEN',
                      emoji=twitch_emoji),
            ui.Button(label='EpulzeEN',
                      row=1,
                      url='https://www.twitch.tv/EpulzeEN2',
                      emoji=twitch_emoji),
            ui.Button(label='EpulzeEN3',
                      row=1,
                      url='https://www.twitch.tv/EpulzeEN3',
                      emoji=twitch_emoji),
            ui.Button(label='EpulzeEN4',
                      row=1,
                      url='https://www.twitch.tv/EpulzeEN4',
                      emoji=twitch_emoji)]

        stats_buttons = [
            ui.Button(label='Dotabuff Page',
                      row=2,
                      url='https://www.dotabuff.com/esports/leagues/15438-the-bali-major',
                      emoji=dotabuff_emoji),
            ui.Button(label='Picks and Bans',
                      row=2,
                      url='https://www.dotabuff.com/esports/leagues/15438-the-bali-major/picks',
                      emoji=dotabuff_emoji),
            ui.Button(label='Drafts',
                      row=2,
                      url='https://www.dotabuff.com/esports/leagues/15438-the-bali-major/drafts',
                      emoji=dotabuff_emoji)]

        embed.set_thumbnail(url='https://i.imgur.com/kSwVOrR.png')

        await interaction.response.send_message(embed=embed, components=[liquipedia_buttons, stream_buttons, stats_buttons])

# Called by bot.load_extension in main


def setup(bot: commands.Bot):
    bot.add_cog(Major(bot))
