import logging
from disnake import Member
from disnake.ext import commands

from config import Configuration
from database.tbnbotdatabase import database_session, TbnMember

class NaughtyListCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot;
        self.db_session = database_session()
        self.naughty_list_role_id = Configuration.instance().NAUGHTY_LIST_ROLE_ID
        self.bot_channel_id = Configuration.instance().BOT_CHANNEL_ID
        
    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        """Fires whenever a user joins the guild. Sticks them back on the naughty list with a system message to shame them

        Args:
            member (Member): the member who joined
        """
        logger = logging.getLogger(__name__)
        
        try:
            db_member = self.db_session.query(TbnMember).filter(TbnMember.id == member.id).first()
            logger.info(f"{member.global_name} joined. {'Does not exist' if not db_member else 'Exists'} in db.")
            
            if db_member and db_member.is_naughty_listed:
                # User was previously naughty listed so needs to be re-naughty-listed
                await self.naughty_list(member)
                if member.guild.system_channel:
                    await member.guild.system_channel.send(f"{member.mention} tried to cheat the naughty list. Welcome back!")
                
            if not db_member:
                tbn_member = TbnMember(id=member.id, birthday=None)
                self.db_session.add(tbn_member)
                self.db_session.commit()            
        except Exception as e:
            logger.error(f"Error in on_member_join: {str(e)}", exc_info=True)
            
    async def naughty_list(self, member: Member):
        logger = logging.getLogger(__name__)
        
        naughty_list_role = member.guild.get_role(self.naughty_list_role_id)
        
        if not naughty_list_role:
            logger.error(f"Naughty list role (ID {self.naughty_list_role_id}) did not exist in guild {member.guild.name} (ID {member.guild.id})")
            return
        await member.add_roles(naughty_list_role)
        
    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        """Fires whenever a user is updated (including but not limited to role updates)
        Checks whether the user put on the naughty list or removed from it and updates its db flag accordingly

        Args:
            before (Member): the member's details prior to the update
            after (Member): the member's details after having been updated
        """
        if before.roles != after.roles:
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            
            naughty_status_change = None
        
            if any(role.id == self.naughty_list_role_id for role in added_roles):
                naughty_status_change = True  # Added to naughty list
            elif any(role.id == self.naughty_list_role_id for role in removed_roles):
                naughty_status_change = False  # Removed from naughty list
            
            # User wasn't naughty listed or un-naughty listed - nothing left to do
            if naughty_status_change is None:
                return
                       
            # User was just naughty listed
            db_member = self.db_session.query(TbnMember).filter(TbnMember.id == after.id).first()
            
            if db_member:
                db_member.is_naughty_listed = naughty_status_change
            else:
                db_member = TbnMember(id=after.id, birthday=None, is_naughty_listed=naughty_status_change)
                self.db_session.add(db_member)
                
            self.db_session.commit()