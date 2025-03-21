import time
from disnake import ApplicationCommandInteraction
import disnake
from disnake.ext import commands, tasks
from sqlalchemy import and_, case, extract, or_
from cogs.shared.chatcompletion_cog import ChatCompletionCog
from config import Configuration
from datetime import datetime, timedelta, timezone, time
from database import database_session, TbnMember
from sqlalchemy.exc import SQLAlchemyError
import os
import logging

from database.tbnbotdatabase import TbnMemberAudit

BIRTHDAY_INPUT_FORMAT = "%d/%m/%Y"
BIRTHDAY_OUTPUT_FORMAT = "%d %B"

logger = logging.getLogger(__name__)

class Birthdays(ChatCompletionCog):
    def __init__(self, bot: commands.Bot):
        super().__init__("Birthdays", bot)
        
        self.db_session = database_session()
        self.notify_birthdays.start()
        self.manage_birthday_roles.start()

        system_message = """You are an announcer for birthdays of members of a Discord community called 'The Biscuit Network' or TBN for short. You will write messages to announce birthdays in an announcements channel."""

        user_message_1 = f"""Hi. I'd like you to write a birthday announcement for a Discord community called 'The Biscuit Network'. 
        The announcement should contain a short paragraph for each user referencing them by their ID. 
        For example, for a user with ID 186222231125360641 you could say: 
        "Hello gang! It's one of our esteemed members' birthday today! 
        Please congratulate <@!186222231125360641> on their birthday! <@!186222231125360641>"
        Followed by a short message wishing them a happy birthday and expressing how much they mean to the community. This message should be funny, complimentary and flirtatious.
        Include many emoji relevant to birthday celebrations such as 🎂, 🥳, 🎉, ❤. Make sure to format it neatly by starting a new paragraph for each user. 
        If there are multiple users with birthdays on the same day, make sure to mention all of them in the announcement, but each of their paragraphs should be unique.
        Be creative in your response, but make sure to NEVER mention a User ID unless it's surrounded by <@! and > in the form of a Discord mention such as <@!186222231125360641>! 
        Respond "Ok." if you understand.
        """

        assistant_message_1 = "Ok."

        self.set_message_context(system_message, [user_message_1], [assistant_message_1])

    def cog_unload(self):
        self.notify_birthdays.cancel()
        self.clear_birthday_roles.cancel()

    @commands.slash_command(
        guild_ids=[Configuration.instance().GUILD_ID],
        name="setbirthday",
        description="Set your birthday"
    )
    async def set_birthday(self, interaction: ApplicationCommandInteraction, birthday: str):
        """
        Set your birthday so you can be congratulated in the future.
        Parameters
        ----------
        birthday: dd/mm or dd/mm/yyyy format.
        """
        logger = logging.getLogger(__name__)
        logger.info(f"User {interaction.author.name} (ID: {interaction.author.id}) is attempting to set birthday: {birthday}")

        try:
            # Parse the date
            if len(birthday) == 5:  # dd/mm format
                date = datetime.strptime(birthday + '/1900', BIRTHDAY_INPUT_FORMAT)
            elif len(birthday) == 10:  # dd/mm/yyyy format
                date = datetime.strptime(birthday, BIRTHDAY_INPUT_FORMAT)
            else:
                raise ValueError("Invalid date format")

            # Create or update member
            changed_member = TbnMember(interaction.author.id, date)
            self.db_session.merge(changed_member)
            
            # Add audit entry
            self.db_session.add(TbnMemberAudit(changed_member))
            
            # Commit changes
            self.db_session.commit()

            logger.info(f"Successfully set birthday for user {interaction.author.name} (ID: {interaction.author.id}) to {date.date()}")
            
            await interaction.response.send_message(
                f"{interaction.author.mention}, your birthday is registered as {date.date().strftime(BIRTHDAY_OUTPUT_FORMAT)}",
                ephemeral=True
            )

        except ValueError as e:
            logger.error(f"Invalid date format provided by user {interaction.author.name} (ID: {interaction.author.id}): {birthday}")
            await interaction.response.send_message(
                f"Sorry, that's not a valid date format. Please use dd/mm or dd/mm/yyyy.",
                ephemeral=True
            )

        except SQLAlchemyError as e:
            logger.error(f"Database error while setting birthday for user {interaction.author.name} (ID: {interaction.author.id}): {str(e)}")
            self.db_session.rollback()
            await interaction.response.send_message(
                "Sorry, there was an error saving your birthday. Please try again later.",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Unexpected error while setting birthday for user {interaction.author.name} (ID: {interaction.author.id}): {str(e)}")
            await interaction.response.send_message(
                "Sorry, an unexpected error occurred. Please try again later.",
                ephemeral=True
            )
            
    @commands.slash_command(
        guild_ids=[Configuration.instance().GUILD_ID],
        name="upcomingbirthdays",
        description="See all birthdays in the next 31 days."
    )
    async def upcoming_birthdays(self, interaction: ApplicationCommandInteraction):
        today = datetime.now().date()
        thirty_days_later = today + timedelta(days=31)
        
        # Create a case statement for sorting
        sort_case = case(
            (extract('month', TbnMember.birthday) < today.month, extract('month', TbnMember.birthday) + 12),
            (and_(extract('month', TbnMember.birthday) == today.month, 
                  extract('day', TbnMember.birthday) < today.day), 
             extract('month', TbnMember.birthday) + 12),
            else_=extract('month', TbnMember.birthday)
        )

        # Build the query
        query = self.db_session.query(TbnMember).filter(
            or_(
                and_(extract('month', TbnMember.birthday) == today.month, 
                     extract('day', TbnMember.birthday) >= today.day),
                and_(extract('month', TbnMember.birthday) == thirty_days_later.month, 
                     extract('day', TbnMember.birthday) <= thirty_days_later.day),
                and_(extract('month', TbnMember.birthday) > today.month, 
                     extract('month', TbnMember.birthday) < thirty_days_later.month),
                and_(today.month == 12, 
                     extract('month', TbnMember.birthday) == 1)
            )
        ).order_by(
            sort_case,
            extract('day', TbnMember.birthday)
        )

        upcoming_birthdays = query.all()

        if not upcoming_birthdays:
            await interaction.response.send_message("There are no upcoming birthdays in the next 31 days.", ephemeral=True)
            return

        birthday_output_format = "%B %d"  # Month Day format
        birthday_list = []
        for member in upcoming_birthdays:
            birthday_date = member.birthday.replace(year=today.year)
            if birthday_date < today:
                birthday_date = birthday_date.replace(year=today.year + 1)
            days_until = (birthday_date - today).days
            if days_until <= 31:  # Additional check to ensure we're within 31 days
                birthday_list.append(f"<@{member.id}>: {member.birthday.strftime(birthday_output_format)} (in {days_until} days)")

        message = "Upcoming birthdays in the next 31 days:\n" + os.linesep.join(birthday_list)
        
        # Handle message length limit
        if len(message) > 2000:
            message = message[:1997] + "..."

        await interaction.response.send_message(message, ephemeral=True)

    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="removebirthday", description="Remove your birthday.")
    async def remove_birthday(self, interaction: ApplicationCommandInteraction):
        self.db_session.query(TbnMember).filter(TbnMember.id == interaction.author.id).first().birthday = None
        self.db_session.commit()

        await interaction.response.send_message(f"{interaction.author.mention}, your birthday has been removed.", ephemeral=True)

    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="showbirthday", description="Show your birthday, just in case you forgot.")
    async def show_birthday(self, interaction: ApplicationCommandInteraction):
        birthday_boi = self.db_session.query(TbnMember).filter(TbnMember.id == interaction.author.id).first()
        await interaction.response.send_message(f"{interaction.author.mention}, your birthday is registered as {birthday_boi.birthday.strftime(birthday_output_format)}", ephemeral=True)
    
    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="announcebirthdays", description="Trigger the birthday announcement.")
    @commands.default_member_permissions(manage_guild=True)
    async def trigger_birthdays_announcement(self, interaction: ApplicationCommandInteraction):
        await interaction.response.defer()        
        await self.notify_birthdays()        
        await interaction.delete_original_response()

    @tasks.loop(time=time(hour=7, minute=0, tzinfo=timezone.utc), count=None, reconnect=True)
    async def notify_birthdays(self):
        birthday_bois = self.db_session.query(TbnMember)\
            .filter(extract('month', TbnMember.birthday) == datetime.now().month)\
            .filter(extract('day', TbnMember.birthday) == datetime.now().day)\
            .all()
            
        if len(birthday_bois) < 1: 
            return

        message = f"There are {len(birthday_bois)} birthdays today, their User IDs are {', '.join([str(member.id) for member in birthday_bois])}. Please write the announcement."
        announcement = await self.get_response(message)

        if announcement == "":
            announcement = (
                f'Good morning gang, today is <@!{birthday_bois[0].id}>\'s birthday! Happy birthday <@!{birthday_bois[0].id}>! :partying_face: :birthday: :partying_face:'
                if len(birthday_bois) == 1
                else f'Good morning gang, we have _multiple_ birthdays today! Happy birthday to {", ".join([f"<@!{member.id}>" for member in birthday_bois])}! :partying_face: :birthday: :partying_face:'
            )

        await self.bot.get_channel(Configuration.instance().BIRTHDAYS_CHANNEL_ID).send(announcement + "\n\n_Use the /setbirthday command to register your own birthday for future announcements_")

    @tasks.loop(time=time(hour=1, minute=0, second=0, tzinfo=timezone.utc), count=None, reconnect=True)
    async def manage_birthday_roles(self):
        birthday_role_id = Configuration.instance().BIRTHDAY_ROLE_ID
        today = datetime.now().date()

        for guild in self.bot.guilds:
            birthday_role = guild.get_role(birthday_role_id)
            if not birthday_role:
                logger.warning(f"Birthday role not found in guild {guild.name} (ID: {guild.id})")
                continue

            # Remove birthday roles from all current holders
            for member in birthday_role.members:
                try:
                    await member.remove_roles(birthday_role, reason="Birthday role cleanup")
                    logger.info(f"Removed birthday role from {member.name} (ID: {member.id}) in {guild.name}")
                except disnake.HTTPException as e:
                    logger.error(f"Failed to remove birthday role from {member.name} (ID: {member.id}) in {guild.name}: {e}")

            # Assign birthday roles to members whose birthday is today
            current_birthday_members = self.db_session.query(TbnMember).filter(
                extract('month', TbnMember.birthday) == today.month,
                extract('day', TbnMember.birthday) == today.day
            ).all()

            for db_member in current_birthday_members:
                member = guild.get_member(db_member.id)
                if member:
                    try:
                        await member.add_roles(birthday_role, reason="It's their birthday!")
                        logger.info(f"Added birthday role to {member.name} (ID: {member.id}) in {guild.name}")
                    except disnake.HTTPException as e:
                        logger.error(f"Failed to add birthday role to {member.name} (ID: {member.id}) in {guild.name}: {e}")
                else:
                    logger.warning(f"Member with ID {db_member.id} not found in guild {guild.name} (ID: {guild.id})")

    @manage_birthday_roles.before_loop
    async def before_manage_birthday_roles(self):
        await self.bot.wait_until_ready()

    @manage_birthday_roles.error
    async def manage_birthday_roles_error(self, error):
        logger.error(f"An error occurred in the manage_birthday_roles task: {error}")

# Called by bot.load_extension in main
def setup(bot: commands.Bot):
    bot.add_cog(Birthdays(bot))