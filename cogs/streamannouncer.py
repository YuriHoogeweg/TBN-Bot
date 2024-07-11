import logging
import pprint
import random
from disnake import Member, Status, Streaming
from disnake.ext import commands

from cogs.shared.chatcompletion_cog import ChatCompletionCog
from config import Configuration

class StreamAnnouncer(commands.Cog):
    def __init__(self, bot: commands.Bot, chat_bots: list[ChatCompletionCog]):
        self.bot = bot
        self.chat_bots = chat_bots

    @commands.Cog.listener()
    async def on_presence_update(self, before: Member, after: Member):
        # Skip if user was already streaming, or isn't currently streaming
        if (not isinstance(after.activity, Streaming) or isinstance(before.activity, Streaming)):
            return

        placeholder_replacements = {f"%username%" : "TBN"}
        chatbot = random.choice(self.chat_bots)
        
        chatbot_message = f"""Our mutual friend {after.display_name} just started streaming, could you write an announcement to share and promote his stream? 
            The game they're streaming is {after.activity.game}, their stream title is {after.activity.name} and the URL to their stream is {after.activity.url}. 
            Make sure to incorporate their name, game, stream title and URL in your announcement! Tell me only the announcement, nothing else"""
        
        response = await chatbot.get_response(chatbot_message, placeholder_replacements)

        message = f"Content Alert!\n**{chatbot.name}:** {response}"
        logging.info(f"Stream live announcement: {message}")
        
        self.bot\
            .get_channel(Configuration.instance().BOT_CHANNEL_ID)\
            .send(message)