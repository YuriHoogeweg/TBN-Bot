from disnake import ui, Embed, ApplicationCommandInteraction
from disnake.ext import commands
from config import Configuration


class BerlinMajor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Register as slash command - pass in Guild ID so command changes propagate immediately
    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name='berlin', description='Berlin major info post with links to resources')
    async def berlin_major(self, interaction: ApplicationCommandInteraction):
        embed = Embed(
            title='ESL One Berlin Major',
            type='rich',
            color=0xe3088b
        )

        dotabuff_emoji = Configuration.instance().DOTABUFF_EMOJI
        twitch_emoji = Configuration.instance().TWITCH_EMOJI

        embed.add_field(name='Group stage',
                        value='April 26th to 30th',
                        inline=False)
        embed.add_field(name='Playoffs',
                        value='May 1st to 7th',
                        inline=False)
        embed.add_field(name='Sweepstakes Teams',
                        value='[Post](https://discord.com/channels/296709532070182912/777332475243266099/1099801369931686049)',
                        inline=False)
        embed.add_field(name='TBN Attendees\' Thread',
                        value='https://discord.com/channels/296709532070182912/1072531012287995944',
                        inline=False)

        liquipedia_buttons = [
            ui.Button(label='Group Stage Matches',
                      row=0,
                      url='https://liquipedia.net/dota2/ESL_One/Berlin_Major/2023/Group_Stage#Matches',
                      emoji='📅'),
            ui.Button(label='Playoffs Bracket',
                      row=0,
                      url='https://liquipedia.net/dota2/ESL_One/Berlin_Major/2023#Playoffs',
                      emoji='📅')]

        stream_buttons = [
            ui.Button(label='Squad Stream',
                      row=1,
                      url='https://www.twitch.tv/esl_dota2/squad',
                      emoji=twitch_emoji),
            ui.Button(label='Main Stream',
                      row=1,
                      url='https://www.twitch.tv/esl_dota2',
                      emoji=twitch_emoji),
            ui.Button(label='Ember',
                      row=1,
                      url='https://www.twitch.tv/esl_dota2ember',
                      emoji=twitch_emoji),
            ui.Button(label='Storm',
                      row=1,
                      url='https://www.twitch.tv/esl_dota2storm',
                      emoji=twitch_emoji),
            ui.Button(label='Earth',
                      row=1,
                      url='https://www.twitch.tv/esl_dota2earth',
                      emoji=twitch_emoji)]

        stats_buttons = [
            ui.Button(label='Overview',
                      row=2,
                      url='https://www.dotabuff.com/esports/leagues/15251-esl-one-the-berlin-major-powered-by-intel',
                      emoji=dotabuff_emoji),
            ui.Button(label='Picks and Bans',
                      row=2,
                      url='https://www.dotabuff.com/esports/leagues/15251-esl-one-the-berlin-major-powered-by-intel/picks',
                      emoji=dotabuff_emoji),
            ui.Button(label='Drafts',
                      row=2,
                      url='https://www.dotabuff.com/esports/leagues/15251-esl-one-the-berlin-major-powered-by-intel/drafts',
                      emoji=dotabuff_emoji)]

        embed.set_thumbnail(url='https://i.imgur.com/YNrTpSL.png')

        await interaction.response.send_message(embed=embed, components=[liquipedia_buttons, stream_buttons, stats_buttons])

# Called by bot.load_extension in main


def setup(bot: commands.Bot):
    bot.add_cog(BerlinMajor(bot))
