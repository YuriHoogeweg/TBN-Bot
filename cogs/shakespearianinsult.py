import random
from discord import Member, Interaction
from discord.ext import commands
from config import Configuration


class ShakeSpearianInsult(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def __get_insult():
        col1 = ['Artless', 'Bawdy', 'Beslubbering', 'Bootless', 'Churlish', 'Cockered', 'Clouted', 'Craven', 'Currish', 'Dankish', 'Dissembling', 'Droning', 'Errant', 'Fawning', 'Fobbing', 'Froward', 'Frothy', 'Gleeking', 'Goatish', 'Gorbellied', 'Impertinent', 'Infectious',
                'Jarring', 'Loggerheaded', 'Lumpish', 'Mammering', 'Mangled', 'Mewling', 'Paunchy', 'Pribbling', 'Puking', 'Puny', 'Qualling', 'Rank', 'Reeky', 'Roguish', 'Ruttish', 'Saucy', 'Spleeny', 'Spongy', 'Surly', 'Tottering', 'Unmuzzled', 'Vain', 'Venomed', 'Villainous', 'Warped']
        col2 = ['base-court', 'bat-fowling', 'beef-witted', 'beetle-headed', 'boil-brained', 'common-kissing', 'crook-pated', 'dismal-dreaming', 'dizzy-eyed', 'dog-hearted', 'dread-bolted', 'earth-vexing', 'elf-skinned', 'fat-kidneyed', 'fen-sucked', 'flap-mouthed', 'fly-bitten', 'folly-fallen', 'fool-born', 'full-gorged', 'futs-griping', 'half-faced', 'hasty-witted',
                'hedge-born', 'hell-hated', 'idle-headed', 'ill-nurtured', 'knotty-pated', 'milk-livered', 'motley-minded', 'onion-eyed', 'plume-plucked', 'pottle-deep', 'pox-marked', 'reeling-ripe', 'rough-hewn', 'rude-growing', 'rump-fed', 'shard-borne', 'sheep-biting', 'spur-galled', 'swag-bellied', 'tardy-gaited', 'tickle-brained', 'toad-spotted', 'unchin-snouted', 'weather-bitten']
        col3 = ['apple-john', 'baggage', 'barnacle', 'bladder', 'boar-pig', 'bugbear', 'bum-bailey', 'canker-blossom', 'clack-dish', 'clotpole', 'coxcomb', 'death-token', 'dewberry', 'flap-dragon', 'flax-wench', 'flirt-gill', 'foot-licker', 'fustilarian', 'giglet', 'gudgeon', 'haggard', 'harpy',
                'hedge-pig', 'horn-beast', 'hugger-mugger', 'jolthead', 'lewdster', 'lout', 'maggot-pie', 'malt-worm', 'mammet', 'measle', 'minnow', 'miscreant', 'moldwarp', 'mumble-news', 'nut-hook', 'pigeon-egg', 'pignut', 'puttock', 'pumpion', 'ratsbane', 'scut', 'skainsmate', 'strumpet', 'vartlot', 'vassal']

        return f"{random.choice(col1).lower()} {random.choice(col2).lower()} {random.choice(col3).lower()}."

    # Register as slash command - someone who knows Python should find a way to extract this guild ID from config instead of hardcoding it.
    @commands.slash_command(guild_ids=[Configuration.instance().GUILD_ID], description="Insult a user as if it's the year 1600")
    async def shakespeareinsult(self, interaction: Interaction, user: Member):
        await interaction.response.send_message(f"{user.mention}, you {ShakeSpearianInsult.__get_insult()}")

# Called by bot.load_extension in main
def setup(bot: commands.Bot):
    bot.add_cog(ShakeSpearianInsult(bot))
