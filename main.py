import disnake
from disnake.ext.commands import InteractionBot
from cogs.berlinmajor import BerlinMajor
from cogs.overthrowcourage import OverthrowCourage
from cogs.birthdays import Birthdays
from cogs.sandbot import SandBot
from cogs.shakespearianinsult import ShakeSpearianInsult
from cogs.formulaone import FormulaOne
from config import Configuration
import openai 
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Set the openai api key
openai.api_key = Configuration.instance().OPENAI_KEY

# Set intents for the bot here - intents info: https://discord.com/developers/docs/topics/gateway#gateway-intents
intents = disnake.Intents.default()

# message_content intent is necessary for the bot to be able to read commands.
intents.message_content = True

# Create a Bot instance. This bot client is our connection to Discord.
bot = InteractionBot(intents=intents)

# Load cogs here
bot.add_cog(ShakeSpearianInsult(bot))
bot.add_cog(OverthrowCourage(bot))
bot.add_cog(SandBot(bot))
bot.add_cog(Birthdays(bot))
bot.add_cog(BerlinMajor(bot))
bot.add_cog(FormulaOne(bot))

# Register an event, the on_ready callback is fired when the bot has finished connecting.
# See a complete list of supported events under https://docs.pycord.dev/en/master/api/events.html#discord.on_ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

    # Sync our registered slash commands
    await bot._sync_application_commands()

# Run the client and pass it our bot's authentication token
bot.run(Configuration.instance().TOKEN)