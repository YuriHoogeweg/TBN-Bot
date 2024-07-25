from datetime import datetime, timedelta
import logging
import random
from typing import Optional
from disnake import Member, Streaming, TextChannel
from disnake.ext import commands
from sqlalchemy import select

from cogs.shared.chatcompletion_cog import ChatCompletionCog
from config import Configuration
from database.tbnbotdatabase import TbnMember, database_session

class StreamAnnouncer(commands.Cog):
    def __init__(self, bot: commands.Bot, chat_bots: list[ChatCompletionCog]):
        self.bot = bot
        self.chat_bots = chat_bots
        self.db_session = database_session()
        self.streamer_role_id = Configuration.instance().STREAMER_ROLE_ID
        self.announcement_channel_id = Configuration.instance().BOT_CHANNEL_ID

    @commands.Cog.listener()
    async def on_presence_update(self, before: Member, after: Member):
        try:
            can_announce, tbn_member = await self.can_announce_stream(before, after)
            if not can_announce:
                return
            
            placeholder_replacements = {"%username%": "TBN"}
            chatbot = random.choice(self.chat_bots)
            
            stream_info = after.activity
            chatbot_message = f"""Our mutual friend {after.display_name} just started streaming, could you write an announcement to share and promote their stream to our Discord server called The Biscuit Network (TBN)?
                The game they're streaming is `{stream_info.game}`, their stream title is `{stream_info.name}` and the URL to their stream is `{stream_info.url}`.
                Incorporate the Discord server's name, their name, game, stream title and URL in your announcement, include the URL exactly as provided and do not alter it in any way! Tell me only the announcement, nothing else"""
            
            response = await chatbot.get_response(chatbot_message, placeholder_replacements)
            message = f"# Content Alert!\n**{chatbot.name}:** {response}"
            logging.info(f"Stream live announcement: {message}")
            
            await self.send_announcement(message)            
            await self.update_member_last_announcement_timestamp(after, tbn_member)
        except Exception as e:
            logging.error(f"Error in on_presence_update: {str(e)}", exc_info=True)
            
    async def send_announcement(self, message: str):
        try:
            channel = self.bot.get_channel(self.announcement_channel_id)
            if not isinstance(channel, TextChannel):
                logging.error(f"Channel with ID {self.announcement_channel_id} is not a TextChannel or doesn't exist.")
                return
            sent_message = await channel.send(message)
            logging.info(f"Announcement sent successfully. Message ID: {sent_message.id}")
        except Exception as e:
            logging.error(f"Failed to send announcement: {str(e)}", exc_info=True)

    async def can_announce_stream(self, before: Member, after: Member):
        has_streamer_role = self.streamer_role_id in [role.id for role in after.roles]
        is_new_stream = isinstance(after.activity, Streaming) and not isinstance(before.activity, Streaming)
        
        if not (has_streamer_role and is_new_stream):
            return False, None
        
        member = self.db_session\
            .query(TbnMember)\
            .filter(TbnMember.id == after.id)\
            .first()
        
        last_stream_announcement_time = member.last_stream_announcement_timestamp if member else None
        
        return (last_stream_announcement_time is None 
                or last_stream_announcement_time < datetime.now() - timedelta(minutes=10)), member

    async def update_member_last_announcement_timestamp(self, discord_member: Member, tbn_member: Optional[TbnMember]):
        async with database_session() as session:
            if tbn_member is None:
                tbn_member = TbnMember(discord_member.id)
                session.add(tbn_member)
            
            tbn_member.last_stream_announcement_timestamp = datetime.now()
            await session.commit()