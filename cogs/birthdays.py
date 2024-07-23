import time
from disnake import ApplicationCommandInteraction
import disnake
from disnake.ext import commands, tasks
from sqlalchemy import extract
from cogs.shared.chatcompletion_cog import ChatCompletionCog
from config import Configuration
from datetime import datetime, timedelta, timezone, time
from database import database_session, TbnMember
import os
import logging

from database.tbnbotdatabase import TbnMemberAudit

birthday_input_format = '%d/%m/%Y'
birthday_output_format = '%d %B'

logger = logging.getLogger(__name__)

class Birthdays(ChatCompletionCog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
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

    # Register as slash command - pass in Guild ID so command changes propagate immediately
    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="setbirthday", description="Set your birthday")
    async def set_birthday(self, interaction: ApplicationCommandInteraction, birthday: str):
        """
        Set your birthday so you can be congratulated in the future.

        Parameters
        ----------
        birthday: dd/mm or dd/mm/yyyy format.
        """        
        date = datetime.strptime(birthday if len(birthday) == 10 else birthday[0:5] + '/1900', birthday_input_format)

        changed_member = TbnMember(interaction.author.id, date)        
        self.db_session.merge(changed_member)        
        self.db_session.add(TbnMemberAudit(changed_member))
        
        self.db_session.commit()

        await interaction.response.send_message(f"{interaction.author.mention}, your birthday is registered as {date.date().strftime(birthday_output_format)}", ephemeral=True)

    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], name="upcomingbirthdays", description="See all birthdays in the next 31 days.")
    async def upcoming_birthdays(self, interaction: ApplicationCommandInteraction):
        # TODO figure out how to filter this within the sqlalchemy query
        all_members = self.db_session.query(TbnMember)\
            .filter(TbnMember.birthday != None)\
            .order_by(TbnMember.birthday.asc()).all()
        
        def is_upcoming_birthday(member: TbnMember):
            birthday = datetime(year = datetime.now().year, month = member.birthday.month, day = member.birthday.day)
            return birthday > datetime.now() and birthday < datetime.now() + timedelta(days = 31)

        upcoming_birthday_bois = filter(is_upcoming_birthday, all_members)

        await interaction.response.send_message(f"Upcoming birthdays in the next 31 days:\n{os.linesep.join([f'<@!{member.id}>: {member.birthday.strftime(birthday_output_format)}' for member in upcoming_birthday_bois])}", ephemeral=True)

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
                member = guild.get_member(db_member.discord_id)
                if member:
                    try:
                        await member.add_roles(birthday_role, reason="It's their birthday!")
                        logger.info(f"Added birthday role to {member.name} (ID: {member.id}) in {guild.name}")
                    except disnake.HTTPException as e:
                        logger.error(f"Failed to add birthday role to {member.name} (ID: {member.id}) in {guild.name}: {e}")
                else:
                    logger.warning(f"Member with ID {db_member.discord_id} not found in guild {guild.name} (ID: {guild.id})")

    @manage_birthday_roles.before_loop
    async def before_manage_birthday_roles(self):
        await self.bot.wait_until_ready()

    @manage_birthday_roles.error
    async def manage_birthday_roles_error(self, error):
        logger.error(f"An error occurred in the manage_birthday_roles task: {error}")

# Called by bot.load_extension in main
def setup(bot: commands.Bot):
    bot.add_cog(Birthdays(bot))