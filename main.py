import disnake
from disnake.ext.commands import InteractionBot
from cogs.sandbot import SandBot
from cogs.shakespearianinsult import ShakeSpearianInsult
from config import Configuration

# Set intents for the bot here - intents info: https://discord.com/developers/docs/topics/gateway#gateway-intents
intents = disnake.Intents.default()

# message_content intent is necessary for the bot to be able to read commands.
intents.message_content = True

# Create a Bot instance. This bot client is our connection to Discord.
bot = InteractionBot(intents=intents)

# Load cogs here
bot.add_cog(ShakeSpearianInsult(bot))
bot.add_cog(SandBot(bot))

# Register an event, the on_ready callback is fired when the bot has finished connecting.
# See a complete list of supported events under https://docs.pycord.dev/en/master/api/events.html#discord.on_ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

    # Sync our registered slash commands
    await bot._sync_application_commands()

# Run the client and pass it our bot's authentication token
bot.run(Configuration.instance().TOKEN)
