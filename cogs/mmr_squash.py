from disnake import ApplicationCommandInteraction
from disnake.ext import commands

# Valve's Immortal MMR squash: new = FLOOR(5630 + 0.31 * (old - 5630)).
# MMR at or below the base is left unchanged.
SQUASH_BASE = 5630
# 0.31 as a fraction so the maths stays exact with integers.
RATIO_NUM = 31
RATIO_DEN = 100


def old_to_new(old_mmr: int) -> int:
    """Convert pre-squash MMR to post-squash MMR."""
    if old_mmr <= SQUASH_BASE:
        return old_mmr
    return SQUASH_BASE + (RATIO_NUM * (old_mmr - SQUASH_BASE)) // RATIO_DEN


def new_to_old_range(new_mmr: int) -> tuple[int, int]:
    """Return the (min, max) pre-squash MMR that floors to the given post-squash MMR.

    Because the squash formula floors, each new MMR maps back to a small range
    of old MMRs (about 1/0.31 ≈ 3.23 wide), so an exact single inverse value
    doesn't exist.
    """
    if new_mmr < SQUASH_BASE:
        # Below the base the squash is the identity, so the old value is exact.
        return new_mmr, new_mmr
    k = new_mmr - SQUASH_BASE
    # floor(31*d/100) == k  <=>  100k <= 31d < 100(k+1)
    d_min = (RATIO_DEN * k + RATIO_NUM - 1) // RATIO_NUM
    d_max = (RATIO_DEN * (k + 1) - 1) // RATIO_NUM
    return SQUASH_BASE + d_min, SQUASH_BASE + d_max


class MmrSquash(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="new_mmr",
        description="Convert pre-squash Immortal MMR to post-squash MMR.",
    )
    async def new_mmr(self, inter: ApplicationCommandInteraction, old_mmr: int):
        """
        Convert pre-squash (old) Immortal MMR to post-squash (new) MMR.
        Parameters
        ----------
        old_mmr: Your MMR before the Immortal MMR squash.
        """
        if old_mmr < 0:
            await inter.response.send_message("MMR can't be negative.", ephemeral=True)
            return

        new_mmr = old_to_new(old_mmr)
        if new_mmr == old_mmr:
            await inter.response.send_message(
                f"**{old_mmr}** is at or below {SQUASH_BASE}, so it's unchanged by the squash."
            )
        else:
            await inter.response.send_message(
                f"**{old_mmr}** old MMR ≈ **{new_mmr}** new MMR"
            )

    @commands.slash_command(
        name="old_mmr",
        description="Convert post-squash Immortal MMR back to pre-squash MMR.",
    )
    async def old_mmr(self, inter: ApplicationCommandInteraction, new_mmr: int):
        """
        Convert post-squash (new) Immortal MMR back to pre-squash (old) MMR.
        Parameters
        ----------
        new_mmr: Your MMR after the Immortal MMR squash.
        """
        if new_mmr < 0:
            await inter.response.send_message("MMR can't be negative.", ephemeral=True)
            return

        old_min, old_max = new_to_old_range(new_mmr)
        if old_min == old_max:
            await inter.response.send_message(
                f"**{new_mmr}** is below {SQUASH_BASE}, so it's unchanged by the squash."
            )
        else:
            old_mmr = (old_min + old_max) // 2
            await inter.response.send_message(
                f"**{new_mmr}** new MMR ≈ **{old_mmr}** old MMR"
            )
