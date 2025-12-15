from datetime import datetime, timedelta
import logging
import random
from typing import Optional
from disnake import ApplicationCommandInteraction, Member, Streaming, TextChannel
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
        
        config = Configuration.instance()
        self.streamer_role_id = config.STREAMER_ROLE_ID
        self.announcement_channel_id = config.BOT_CHANNEL_ID
        self.bambeaner_role_Id = config.BAMBEANER_ROLE_ID
        self.bambo_user_id = config.BAMBO_USER_ID

    @commands.Cog.listener()
    async def on_presence_update(self, before: Member, after: Member):
        try:
            can_announce, tbn_member = self.can_announce_stream(before, after)
            if not can_announce:
                return
            
            await self._announce_stream_internal(after)
        except Exception as e:
            logging.error(f"Error in on_presence_update: {str(e)}", exc_info=True)
            
    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="announce_stream", description="Announce someone's stream (manually)")
    async def announce_stream(self, user: Member, inter: ApplicationCommandInteraction):
        try:
            await inter.response.send_message("Sending...", ephemeral=True)
            await self._announce_stream_internal(user)
        except Exception as e:
            logging.error(f"Error announcing stream: {str(e)}", exc_info=True)
    
    async def _announce_stream_internal(self, user: Member):
        try:
            placeholder_replacements = {"%username%": "TBN"}
            chatbot = random.choice(self.chat_bots)
            
            streaming = self._get_streaming_activity(user)
            game = getattr(streaming, "game", None) or getattr(streaming, "details", None) or "their game"
            title = getattr(streaming, "name", None) or getattr(streaming, "details", None) or "Live now"
            
            chatbot_message = f"""Our mutual friend {user.display_name} just started streaming, could you write an announcement to share and promote their stream to our Discord server called The Biscuit Network (TBN)?
                The game they're streaming is `{game}`, their stream title is `{title}` and the URL to their stream is `{streaming.url}`.
                Incorporate the Discord server's name, their name, game, stream title and URL in your announcement, include the URL exactly as provided and do not alter it in any way! Tell me only the announcement, nothing else"""
            
            response = await chatbot.get_response(chatbot_message, placeholder_replacements, "openai")
            sanitized = sanitize_url_in_text(response, streaming.url)
            
            message_heading = f"# Content Alert <@&{self.bambeaner_role_Id}>!" if user.id == self.bambo_user_id else f"# Content Alert!" 
            message = f"{message_heading}\n**{chatbot.name}:** {sanitized}"
            logging.info(f"Stream live announcement: {message}")
            
            await self.send_announcement(message)            
            
            session = database_session()
            result = session.execute(select(TbnMember).filter(TbnMember.id == user.id))
            tbn_member = result.scalar_one_or_none()
            self.update_member_last_announcement_timestamp(user, tbn_member)
        except Exception as e:
            logging.error(f"Error announcing stream: {str(e)}", exc_info=True)
            
    def _get_streaming_activity(self, member: Member) -> Optional[Streaming]:
        """
        Find a discord.Streaming activity from the member, if any.
        """
        for act in getattr(member, "activities", []) or []:
            if isinstance(act, Streaming):
                return act
        return None
            
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
        # Helper: does this member currently have any Streaming activity?
        def _is_streaming(member: Member) -> bool:
            activities = getattr(member, "activities", None) or []
            return any(isinstance(a, Streaming) for a in activities)

        has_streamer_role = any(role.id == self.streamer_role_id for role in getattr(after, "roles", []))
        is_new_stream = _is_streaming(after) and not _is_streaming(before)

        logging.debug(
            f"Checking stream for {after.name} (ID: {after.id}): "
            f"has_streamer_role={has_streamer_role}, is_new_stream={is_new_stream}, "
            f"before_acts={[type(a).__name__ for a in (getattr(before, 'activities', None) or [])]}, "
            f"after_acts={[type(a).__name__ for a in (getattr(after, 'activities', None) or [])]}"
        )

        if not (has_streamer_role and is_new_stream):
            return False, None

        session = database_session()
        try:
            result = session.execute(select(TbnMember).filter(TbnMember.id == after.id))
            member = result.scalar_one_or_none()

            logging.debug(f"Database query result for {after.name} (ID: {after.id}): {member}")

            last_stream_announcement_time = member.last_stream_announcement_timestamp if member else None
            can_announce = (
                last_stream_announcement_time is None
                or last_stream_announcement_time < datetime.now() - timedelta(hours=1)
            )

            logging.info(
                f"Can announce for {after.name} (ID: {after.id}): {can_announce}, "
                f"Last announcement time: {last_stream_announcement_time}"
            )

            return can_announce, member

        except Exception as e:
            logging.error(
                f"Error in database query for {after.name} (ID: {after.id}): {str(e)}",
                exc_info=True
            )
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