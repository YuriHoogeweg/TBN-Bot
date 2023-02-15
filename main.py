import discord
from discord import Bot
from cogs.shakespearianinsult import ShakeSpearianInsult
from config import Configuration

# Set intents for the bot here - intents info: https://discord.com/developers/docs/topics/gateway#gateway-intents
intents = discord.Intents.default()

# message_content intent is necessary for the bot to be able to read commands.
intents.message_content = True

# Create a Bot instance. This bot client is our connection to Discord.
bot = Bot(intents=intents, command_prefix="")

# Load cogs here
bot.load_extension("cogs.shakespearianinsult")

# Register an event, the on_ready callback is fired when the bot has finished connecting.
# See a complete list of supported events under https://docs.pycord.dev/en/master/api/events.html#discord.on_ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

    # Sync our registered slash commands
    await bot.sync_commands()

# Run the client and pass it our bot's authentication token
bot.run(Configuration.instance().TOKEN)