from datetime import datetime, timedelta
import logging
import random
from typing import Optional
from disnake import Member, Streaming
from disnake.ext import commands

from cogs.shared.chatcompletion_cog import ChatCompletionCog
from config import Configuration
from database.tbnbotdatabase import TbnMember, database_session

class StreamAnnouncer(commands.Cog):
    def __init__(self, bot: commands.Bot, chat_bots: list[ChatCompletionCog]):
        self.bot = bot
        self.chat_bots = chat_bots
        self.db_session = database_session()
        self.streamer_role_id = Configuration.instance().STREAMER_ROLE_ID

    @commands.Cog.listener()
    async def on_presence_update(self, before: Member, after: Member):
        can_announce, tbn_member = await self.can_announce_stream(before, after)
        if (can_announce == False):
            return
        
        placeholder_replacements = {f"%username%" : "TBN"}
        chatbot = random.choice(self.chat_bots)
        
        chatbot_message = f"""Our mutual friend {after.display_name} just started streaming, could you write an announcement to share and promote his stream to our Discord server called The Biscuit Network (TBN)? 
            The game they're streaming is {after.activity.game}, their stream title is {after.activity.name} and the URL to their stream is {after.activity.url}. 
            Make sure to incorporate the Discord server's name, their name, game, stream title and URL in your announcement! Tell me only the announcement, nothing else"""
        
        response = await chatbot.get_response(chatbot_message, placeholder_replacements)

        message = f"# Content Alert!\n**{chatbot.name}:** {response}"
        logging.info(f"Stream live announcement: {message}")

        await self.bot\
            .get_channel(Configuration.instance().BOT_CHANNEL_ID)\
            .send(message)
        
        await self.update_member_last_announcement_timestamp(after, tbn_member)        
    
    async def can_announce_stream(self, before: Member, after: Member):
        has_streamer_role = len([role for role in after.roles if role.id == self.streamer_role_id]) > 0

        # Skip if user doesn't have streamer role, was already streaming, or isn't currently streaming
        if (not has_streamer_role or not isinstance(after.activity, Streaming) or isinstance(before.activity, Streaming)):
            return False, None
        
        member = self.db_session\
            .query(TbnMember)\
            .filter(TbnMember.id == after.id)\
            .first()
        
        last_stream_announcement_time = None if member is None\
            else member.last_stream_announcement_timestamp
        
        # no previous announcement or previous announcement was more than 10 min ago
        return last_stream_announcement_time is None \
            or last_stream_announcement_time < datetime.now() - timedelta(minutes = 10), member
    
    async def update_member_last_announcement_timestamp(self, discord_member: Member, tbn_member: Optional[TbnMember]):
        if tbn_member is None:
            tbn_member = TbnMember(discord_member.id)
            self.db_session.add(tbn_member)
    
        tbn_member.last_stream_announcement_timestamp = datetime.now()
        self.db_session.commit()