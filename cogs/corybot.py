from disnake import ApplicationCommandInteraction
import disnake
from disnake.ext import commands
from cogs.shared.chatcompletion_cog import ChatCompletionCog
from config import Configuration


class CoryBot(ChatCompletionCog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        user_message_1 = f"""Hi! Today I'd like you to imitate a British roadman zoomer called Cory. I'll be sending you messages and I want you to respond to them the way a zoomer (gen-Z) would.
        Zoomers talk in Gen-Z slang such as "slay", "ong" (meaning "on god"), "fr" (meaning "for real"), "fr fr" (meaning "for real for real"), "no cap" or "no 🧢" and "rizz" (meaning charisma). 
        They use lots of emojis such as 🧢, 💀, 🤡, 🙏, 🔥, 👀, 🤙, 💯 and 🤪. They also randomly add terms such as "skibidi toilet", "skibidi ohio", "gyat", "sigma", "fanum tax" and "rizzler" to their sentences.
        Roadmen use lots of British slang such as "bruv" (brother/bro, used to address men even if there's no relation), "bare" (meaning really/very), "clapped" (meaning ugly), "ends" (my ends, meaning my area/neighbourhood) 
        "gassed" (meaning excited), "innit", "mandem" (meaning friend group), "roll with" (spend time with), "vex" or "vexed" (angry/angered), "wasteman" (someone who is acting foolish/annoying), "whip" (car).
        Cory tends to call people "lil bro" when talking to them.
        Be creative in your response, feel free to use any other emojis or slang you think fit this tone.
        Your messages should be informal and match the tone and spelling/grammar of a British roadman zoomer, your messages should be fully lowercase and include a lot of Gen-Z/zoomer slang and emojis and be funny.
        My name is %username% and you can refer to me by "lil bro" or %username% in your response.
        Do you understand?"""

        assistant_message_1 = f"bet, i gotchu lil bro fr fr 🤙💯"

        user_message_2 = "Can you tell me about UK grime?"

        assistant_message_2 = "gotchu lil bro. grime is lit. started in London init, it's a mashup of electronic, hip hop, and dancehall. Stormzy, Skepta and Wiley are fire 🔥🔥🔥"

        user_messages = [user_message_1, user_message_2]
        assistant_messages = [assistant_message_1, assistant_message_2]

        self.set_message_context("", user_messages, assistant_messages)
        super().__init__("Cory", bot)

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

        placeholder_replacements = {f'%username%': str(
            interaction.author.nick or interaction.author.name)}
        msg = f"Oh wow, you're doing a great job so far! Let's continue :). {message}"
        response = await self.get_response(msg, placeholder_replacements)

        await interaction.followup.send(f"{interaction.author.mention}: {message}\n\n**Cory:** {response}")

    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID])
    async def corys_thoughts(self, interaction: ApplicationCommandInteraction, num_message_context: int = 5, context_last_message_id: str = None):
        """
        Get cory's thoughts on the conversation.

        Parameters
        ----------
        num_message_context: number of messages to include in cory's thoughts.    
        context_last_message_id: id of the last message in the context. (in the default discord format of channelid-messageid)    
        """

        await interaction.response.defer()
        messages: list[disnake.Message] = []

        if context_last_message_id is not None:
            [channel_id, message_id] = context_last_message_id.split('-') if context_last_message_id.find('-') != -1 else context_last_message_id.split('/')[-2:]
            last_context_message = await self.bot.get_channel(int(channel_id)).get_partial_message(int(message_id)).fetch()
            messages.append(last_context_message)
            
            if num_message_context > 1:
                messages.extend(await interaction.channel.history(before=last_context_message, limit=num_message_context).flatten())
        else:
            messages = (await interaction.channel.history(limit=num_message_context).flatten())[1:]

        conversation = str.join('\n', [f'{interaction.author.nick or interaction.author.name}: {message.content}' for message in messages])
        placeholder_replacements = {'%username%': str(interaction.author.nick or interaction.author.name)}
        response = await self.get_response(f"Oh wow, you're doing a great job so far! Let's continue imitating cory :). Respond to the following conversation in one message: {conversation}", placeholder_replacements)

        if (len(response) > 2000):
            await interaction.followup.send(f"Sorry, the context is too long for cory to read. Please try again with a shorter context.")

        await interaction.followup.send(f"cory: {response.removeprefix('cory:').removeprefix('Cory:').strip()}")

# Called by bot.load_extension in main
def setup(bot: commands.Bot):
    bot.add_cog(CoryBot(bot))
