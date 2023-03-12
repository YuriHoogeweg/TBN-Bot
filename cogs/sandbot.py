import os
from disnake import Member, ApplicationCommandInteraction
from disnake.ext import commands
from config import Configuration
import openai

class SandBot(commands.Cog):
    sand_prompt: str

    def __init__(self, bot: commands.Bot):
        openai.api_key = Configuration.instance().OPENAI_KEY
        self.bot = bot
        with open("resource/sand-fish.txt", "r") as f:
            self.sand_prompt = f.read()

    def __get_response(self, message: str):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": self.sand_prompt},
                {"role": "assistant", "content": "OK."},
                {"role": "user", "content": message},
            ]
        )

        return completion.choices[0].message.content.replace("\n", "")

    # Register as slash command - pass in Guild ID so command changes propagate immediately
    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID])
    async def sand(self, interaction: ApplicationCommandInteraction, message: str):
        """
        Talk to sand.

        Parameters
        ----------
        message: message to send to sand.
        """
        await interaction.response.send_message(f"sand-fish: {SandBot.__get_response(self, message)}")

# Called by bot.load_extension in main
def setup(bot: commands.Bot):
    bot.add_cog(SandBot(bot))
