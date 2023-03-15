# Mostly yoinked from https://github.com/mdiller/MangoByte (MIT Licence)

import datetime
import random
from disnake.ext import commands
from sqlalchemy import or_
from config import Configuration
from dotabase import *
from sqlalchemy.sql.expression import func
import disnake
import utils.drawing.dota as drawdota

session = dotabase_session()

# Filters a query for rows containing a column that contains the value in a | separated list
def query_filter_list(query, column, value, separator="|"):
    return query.filter(or_(column.like(f"%|{value}"), column.like(f"{value}|%"), column.like(f"%|{value}|%"), column.like(value)))


class OverthrowCourage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = session
        drawdota.init_dota_info_resources(self.get_hero_infos(), self.get_item_infos())

    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], description="Overthrow courage (no bkb/dagon/midas/rapier/pugna)")
    async def overthrowcourage(self, inter: disnake.CmdInter):
        all_boots = query_filter_list(session.query(
            Item), Item.recipe, "item_boots").all()

        for boots in all_boots:
            boots_that_build_from_other_boots = query_filter_list(
                session.query(Item), Item.recipe, boots.name).all()
            for entry in boots_that_build_from_other_boots:
                all_boots.append(entry)

        seed = datetime.datetime.now().timestamp()
        random.seed(seed)
        items = session.query(Item) \
            .filter(~Item.localized_name.contains("Recipe")) \
            .filter(~Item.localized_name.contains("Boots")) \
            .filter(~Item.localized_name.contains("Dagon")) \
            .filter(~Item.localized_name.contains("Midas")) \
            .filter(~Item.localized_name.contains("Black King Bar")) \
            .filter(~Item.localized_name.contains("Guardian Greaves")) \
            .filter(~Item.localized_name.contains("Power Treads")) \
            .filter(~Item.localized_name.contains("Divine Rapier")) \
            .filter(~Item.localized_name.contains("Aghanim")) \
            .filter(Item.recipe != None) \
            .filter(Item.icon != None) \
            .filter(Item.cost > 2100) \
            .order_by(func.random()) \
            .limit(5) \
            .all()

        items.append(random.choice(all_boots))
        random.shuffle(items)

        item_ids = []
        for item in items:
            item_ids.append(item.id)
        else:
            hero_id = session.query(Hero).filter(~Hero.name.contains(
                "Pugna")).order_by(func.random()).first().id

        image = disnake.File(await drawdota.draw_courage(hero_id, item_ids), "courage.png")
        await inter.send(file=image)

    def get_hero_infos(self):
        result = {}
        for hero in session.query(Hero):
            result[hero.id] = {
                "name": hero.localized_name,
                "full_name": hero.full_name,
                "icon": hero.icon,
                "attr": hero.attr_primary,
                "portrait": hero.portrait,
                "image": hero.image,
                "roles": dict(zip(hero.roles.split("|"), map(int, hero.role_levels.split("|"))))
            }

        result[0] = {
            "name": "Unknown",
            "full_name": "unknown_hero",
            "icon": "/panorama/images/heroes/icons/npc_dota_hero_antimage_png.png",
            "attr": "strength",
            "portrait": "/panorama/images/heroes/selection/npc_dota_hero_default_png.png",
            "image": "/panorama/images/heroes/npc_dota_hero_default_png.png",
            "emoji": "unknown_hero",
            "roles": {}
        }
        return result

    def get_item_infos(self):
        result = {}
        for item in session.query(Item):
            if item.icon is None:
                continue
            result[item.id] = {
                "name": item.localized_name,
                "icon": item.icon,
            }
        return result

# Called by bot.load_extension in main
def setup(bot: commands.Bot):
    bot.add_cog(OverthrowCourage(bot))