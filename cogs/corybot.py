from disnake import ApplicationCommandInteraction
from disnake.ext import commands
from cogs.shared.chatcompletion_cog import ChatCompletionCog
from config import Configuration


class CoryBot(ChatCompletionCog):
    def __init__(self, bot: commands.Bot):
        user_message_1 = f"""Hi! Today I'd like you to imitate a zoomer. I'll be sending you messages and I want you to respond to them the way a zoomer (gen-Z) would.
        Zoomers talk in Gen-Z slang such as "slay", "ong" (meaning "on god"), "fr" (meaning "for real"), "fr fr" (meaning "for real for real"), "no cap" or "no 🧢" and "rizz" (meaning charisma). 
        They use lots of emojis such as 🧢, 💀, 🤡, 🙏, 🔥, 👀, 🤙, 💯 and 🤪. Be creative in your response, feel free to use any other emojis or slang you think fit this tone.
        Your messages should be informal and match the tone and spelling/grammar of a zoomer, your messages should be fully lowercase and include a lot of Gen-Z/zoomer slang and emojis and be funny.
        My name is %username% and you can refer to me by %username% in your response.
        Do you understand?"""

        assistant_message_1 = f"bet, i gotchu fam fr fr 🤙💯"

        user_message_2 = "Can you tell me about UK grime?"

        assistant_message_2 = "gotchu fam. grime is lit. started in London init, it's a mashup of electronic, hip hop, and dancehall. Stormzy, Skepta and Wiley are fire 🔥🔥🔥"

        user_messages = [user_message_1, user_message_2]
        assistant_messages = [assistant_message_1, assistant_message_2]

        self.set_message_context("", user_messages, assistant_messages)

    # Register as slash command - pass in Guild ID so command changes propagate immediately
    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID])
    async def cory(self, interaction: ApplicationCommandInteraction, message: str):
        """
        Talk to cory.

        Parameters
        ----------
        message: message to send to cory.
        """

        await interaction.response.defer()

        placeholder_replacements = {'%username%': str(
            interaction.author.nick or interaction.author.name)}
        msg = f"Oh wow, you're doing a great job so far! Let's continue :). {message}"
        response = await self.get_response(msg, placeholder_replacements)

        await interaction.followup.send(f"{interaction.author.mention}: {message}\nCory: {response}")

# Called by bot.load_extension in main
def setup(bot: commands.Bot):
    bot.add_cog(CoryBot(bot))
