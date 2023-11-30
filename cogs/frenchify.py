from disnake import ApplicationCommandInteraction, Member
import disnake
from disnake.ext import commands
from cogs.shared.chatcompletion_cog import ChatCompletionCog
from config import Configuration

# Inspired by https://i.imgur.com/11qFcwi.png
class Frenchify(ChatCompletionCog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        user_message_1 = f"""Hi! Today I'd like you to transform text given to you into a thick French accent. I'll be sending you messages and I want you to repeat them back to me in this heavily accented, entirely lowercase, caricatured version of a French accent.
        Don't give me any additional information, only repeat back what I said but modified to sound french. Do you understand?"""

        assistant_message_1 = f"I understand."

        user_message_2 = "Ehm I'm French and plz we don't talk all like that argh!"

        assistant_message_2 = "euhmx i'm frenche and pleaze oui doun't taulke alles laeque zåt aurghex"

        user_messages = [user_message_1, user_message_2]
        assistant_messages = [assistant_message_1, assistant_message_2]

        self.set_message_context("", user_messages, assistant_messages)

    # Register as slash command - pass in Guild ID so command changes propagate immediately
    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID])
    async def french(self, interaction: ApplicationCommandInteraction, user: Member):
        """
        Make a message french

        Parameters
        ----------
        user: do a french impression of the user's last message in this channel
        """
        await interaction.response.defer()

        messages = await interaction.channel.history(limit=20).flatten()
        user_message = next(m for m in messages if m.author.id == user.id)

        if user_message is None:
            await interaction.followup.send("Could not find a message to make french", ephemeral=True)
            return

        response = await self.get_response(user_message.content)

        await interaction.followup.send(f"{interaction.author.mention}: {user_message.content}\n\n{user.nick or user.name}: {response}")

# Called by bot.load_extension in main
def setup(bot: commands.Bot):
    bot.add_cog(Frenchify(bot))
