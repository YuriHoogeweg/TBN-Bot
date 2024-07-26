from datetime import datetime, timedelta
import logging
import random
from typing import Optional
from disnake import Member, Streaming, TextChannel
from disnake.ext import commands
from sqlalchemy import select, update
from utils.url_sanitizer import sanitize_url_in_text
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
            can_announce, tbn_member = self.can_announce_stream(before, after)
            if not can_announce:
                return
            
            placeholder_replacements = {"%username%": "TBN"}
            chatbot = random.choice(self.chat_bots)
            
            stream_info = after.activity
            chatbot_message = f"""Our mutual friend {after.display_name} just started streaming, could you write an announcement to share and promote their stream to our Discord server called The Biscuit Network (TBN)?
                The game they're streaming is `{stream_info.game}`, their stream title is `{stream_info.name}` and the URL to their stream is `{stream_info.url}`.
                Incorporate the Discord server's name, their name, game, stream title and URL in your announcement, include the URL exactly as provided and do not alter it in any way! Tell me only the announcement, nothing else"""
            
            response = await chatbot.get_response(chatbot_message, placeholder_replacements)
            sanitized = sanitize_url_in_text(response, stream_info.url)
            message = f"# Content Alert!\n**{chatbot.name}:** {sanitized}"
            logging.info(f"Stream live announcement: {message}")
            
            await self.send_announcement(message)            
            self.update_member_last_announcement_timestamp(after, tbn_member)
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

    def can_announce_stream(self, before: Member, after: Member):
        has_streamer_role = self.streamer_role_id in [role.id for role in after.roles]
        is_new_stream = isinstance(after.activity, Streaming) and not isinstance(before.activity, Streaming)
        
        logging.debug(f"Checking stream for {after.name} (ID: {after.id}): has_streamer_role={has_streamer_role}, is_new_stream={is_new_stream}")
        
        if not (has_streamer_role and is_new_stream):
            return False, None
        
        session = database_session()
        try:
            result = session.execute(
                select(TbnMember).filter(TbnMember.id == after.id)
            )
            member = result.scalar_one_or_none()
            
            logging.debug(f"Database query result for {after.name} (ID: {after.id}): {member}")
            
            last_stream_announcement_time = member.last_stream_announcement_timestamp if member else None
            
            can_announce = (last_stream_announcement_time is None 
                            or last_stream_announcement_time < datetime.now() - timedelta(minutes=10))
            
            logging.info(f"Can announce for {after.name} (ID: {after.id}): {can_announce}, Last announcement time: {last_stream_announcement_time}")
            
            return can_announce, member
        
        except Exception as e:
            logging.error(f"Error in database query for {after.name} (ID: {after.id}): {str(e)}", exc_info=True)
            return False, None
        finally:
            session.close()

    def update_member_last_announcement_timestamp(self, discord_member: Member, tbn_member: Optional[TbnMember]):
        session = database_session()
        try:
            if tbn_member is None:
                # If the member doesn't exist in the database, create a new entry
                tbn_member = TbnMember(id=discord_member.id, birthday=None, last_stream_announcement_timestamp=datetime.now())
                session.add(tbn_member)
            else:
                # If the member exists, update their timestamp
                stmt = update(TbnMember).where(TbnMember.id == discord_member.id).values(last_stream_announcement_timestamp=datetime.now())
                session.execute(stmt)
            
            session.commit()
            logging.info(f"Updated last announcement timestamp for member {discord_member.name} (ID: {discord_member.id})")
        except Exception as e:
            logging.error(f"Error updating last announcement timestamp for member {discord_member.name} (ID: {discord_member.id}): {str(e)}", exc_info=True)
            session.rollback()
        finally:
            session.close()