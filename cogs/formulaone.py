import fastf1
import pytz
from disnake import Embed, ApplicationCommandInteraction
from disnake.ext import commands
from config import Configuration
from datetime import datetime   
import calendar

class FormulaOne(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Register as slash command - pass in Guild ID so command changes propagate immediately
    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="schedule", description="Check the F1 schedule for the upcoming race weekend.")
    async def schedule(self, interaction: ApplicationCommandInteraction):
        # The sessions object keeps the original index while removing the past races, hence we have to 
        # iterate through the past races indexes until it hits the first accessible event object
        sessions = fastf1.get_events_remaining()

        # Keeping maximum retries at 30 to futureproof against Dominicali's obsession to add more races in a season
        for x in range(0, 30):
            try:
                event = sessions.get_event_by_round(x)
                embed = Embed(
                    title=event['EventName'],
                    type='rich',
                    color=0xe3088b
                )
                embed.add_field(name=event['Session1'],
                                value=convert_discord_localized_timestamp(event['Session1Date'], x),
                                inline=False)
                embed.add_field(name=event['Session2'],
                                value=convert_discord_localized_timestamp(event['Session2Date'], x),
                                inline=False)
                embed.add_field(name=event['Session3'],
                                value=convert_discord_localized_timestamp(event['Session3Date'], x),
                                inline=False)
                embed.add_field(name=event['Session4'],
                                value=convert_discord_localized_timestamp(event['Session4Date'], x),
                                inline=False)
                embed.add_field(name=event['Session5'],
                                value=convert_discord_localized_timestamp(event['Session5Date'], x),
                                inline=False)
                
                await interaction.response.send_message(embed=embed)

            except Exception as str_error:
                pass
            else:
                break


def convert_discord_localized_timestamp(dt, tzi):
    tz = ["Asia/Bahrain", "Asia/Bahrain", "Asia/Riyadh", "Australia/Melbourne", "Asia/Baku", "America/Detroit", "Europe/Rome", "Europe/Monaco", "Europe/Madrid", "America/Montreal", "Europe/Vienna", "Europe/London", "Europe/Budapest", "Europe/Brussels", "Europe/Amsterdam", "Europe/Rome", "Asia/Singapore", "Asia/Tokyo", "Asia/Qatar", "America/Chicago", "America/Mexico_City", "America/Sao_Paulo", "America/Los_Angeles", "Asia/Baku"] 

    local = pytz.timezone(tz[tzi])
    naive = datetime.strptime(str(dt), '%Y-%m-%d %H:%M:%S')
    local_dt = local.localize(naive)
    utc_dt = local_dt.astimezone(pytz.utc)
    utc_timestamp = round(calendar.timegm(utc_dt.timetuple()))

    return f"<t:{utc_timestamp}:f>"


def setup(bot: commands.Bot):
    bot.add_cog(FormulaOne(bot))