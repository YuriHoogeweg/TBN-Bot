from logger_config import setup_logging

setup_logging()
from cogs.streamannouncer import StreamAnnouncer
import disnake
from disnake.ext.commands import InteractionBot
from cogs.corybot import CoryBot
from cogs.birthdays import Birthdays
from cogs.sandbot import SandBot
from cogs.formulaone import FormulaOne
from cogs.jointime import JoinTimeCog
from cogs.podcast import PodcastCog
from cogs.naughtylist import NaughtyListCog
from config import Configuration
import openai

# Set the openai api key
openai.api_key = Configuration.instance().OPENAI_KEY

# Set intents for the bot here - intents info: https://discord.com/developers/docs/topics/gateway#gateway-intents
intents = disnake.Intents.default()
intents.members = True
intents.presences = True

# members intent is necessary for the bot to be able to read the list of members in a channel or role.
intents.members = True

# message_content intent is necessary for the bot to be able to read commands.
intents.message_content = True

# Create a Bot instance. This bot client is our connection to Discord.
bot = InteractionBot(intents=intents)

# Load cogs here
sand_bot = SandBot(bot)
bot.add_cog(sand_bot)

cory_bot = CoryBot(bot)
bot.add_cog(cory_bot)

bot.add_cog(StreamAnnouncer(bot, [sand_bot, cory_bot]))
bot.add_cog(Birthdays(bot))
bot.add_cog(FormulaOne(bot))
bot.add_cog(JoinTimeCog(bot))
bot.add_cog(PodcastCog(bot))
bot.add_cog(NaughtyListCog(bot))

# Register an event, the on_ready callback is fired when the bot has finished connecting.
# See a complete list of supported events under https://docs.pycord.dev/en/master/api/events.html#discord.on_ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

    # Sync our registered slash commands
    await bot._sync_application_commands()

# Run the client and pass it our bot's authentication token
bot.run(Configuration.instance().TOKEN, reconnect=True)