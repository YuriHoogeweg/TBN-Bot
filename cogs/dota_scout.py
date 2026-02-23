import asyncio
from io import BytesIO

import aiohttp
import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands
from PIL import Image, ImageDraw, ImageFont

from utils.steam import convert_to_steam32

OPENDOTA_BASE = "https://api.opendota.com/api"
# 256×144 landscape hero images — correct 16:9 aspect ratio, no stretching
STEAM_CDN = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes"

BG_COLOR = "#23272A"
TEXT_GRAY = "#aaaaaa"
WIN_GREEN = "#4CAF50"
LOSS_RED = "#F44336"

ICON_W = 96
ICON_H = 54      # 16:9 — matches the 256×144 source images exactly
H_PAD = 6        # left/right padding inside card
V_PAD = 6        # top/bottom padding
ICON_TEXT_GAP = 5
TEXT_LINE_H = 14
CARD_GAP = 4
CARD_SLOT = H_PAD + ICON_W + H_PAD + CARD_GAP  # 112px per slot
CARD_H = V_PAD + ICON_H + ICON_TEXT_GAP + TEXT_LINE_H * 2 + V_PAD  # 99px tall
FONT_SIZE = 11
NAME_ROW_H = 20  # header row height when player_name is shown
ROW_GAP = 4      # vertical gap between player rows in the team composite

DATE_TO_DAYS = {
    "3month": 90,
    "6month": 180,
    "year": 365,
}


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default(size)


async def _get_json(session: aiohttp.ClientSession, url: str) -> list | dict:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        resp.raise_for_status()
        return await resp.json()


async def _fetch_hero_image(
    session: aiohttp.ClientSession, url: str
) -> Image.Image | None:
    if not url:
        return None
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.read()
                img = Image.open(BytesIO(data)).convert("RGBA")
                return img.resize((ICON_W, ICON_H), Image.LANCZOS)
    except Exception:
        pass
    return None


def _make_hero_lookup(all_heroes: list) -> dict[int, dict]:
    lookup = {}
    for h in all_heroes:
        short_name = h["name"].replace("npc_dota_hero_", "")
        lookup[h["id"]] = {
            "localized_name": h["localized_name"],
            "icon_url": f"{STEAM_CDN}/{short_name}.png",
        }
    return lookup


def _build_heroes(player_heroes_raw: list, hero_lookup: dict) -> list[dict]:
    """Sort and map raw OpenDota hero entries into the format used by generate_scout_image."""
    player_heroes_raw.sort(key=lambda h: h.get("games", 0), reverse=True)
    heroes = []
    for h in player_heroes_raw[:10]:
        games = h.get("games", 0)
        if games == 0:
            continue
        hero_id = h["hero_id"]
        wins = h.get("win", 0)
        info = hero_lookup.get(hero_id, {})
        heroes.append({
            "name": info.get("localized_name", str(hero_id)),
            "matches": games,
            "win_rate": (wins / games) * 100,
            "icon_url": info.get("icon_url", ""),
        })
    return heroes


async def _build_scout_canvas(heroes: list[dict], player_name: str = None) -> Image.Image:
    n = len(heroes)
    img_w = CARD_SLOT * n - 4  # no trailing gap on the last card
    header_h = NAME_ROW_H if player_name else 0
    canvas = Image.new("RGB", (img_w, CARD_H + header_h), BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    font = _load_font(FONT_SIZE)

    if player_name:
        name_font = _load_font(13)
        draw.text((H_PAD, (NAME_ROW_H - 13) // 2), player_name, font=name_font, fill="#ffffff")

    async with aiohttp.ClientSession() as session:
        images = await asyncio.gather(
            *[_fetch_hero_image(session, h["icon_url"]) for h in heroes]
        )

    text_y1 = header_h + V_PAD + ICON_H + ICON_TEXT_GAP
    text_y2 = text_y1 + TEXT_LINE_H

    for i, (hero, icon) in enumerate(zip(heroes, images)):
        x = i * CARD_SLOT

        if icon is not None:
            canvas.paste(icon, (x + H_PAD, header_h + V_PAD), icon)

        win_rate = hero["win_rate"]
        wr_color = WIN_GREEN if win_rate >= 50.0 else LOSS_RED

        draw.text((x + H_PAD, text_y1), f"{hero['matches']} games", font=font, fill=TEXT_GRAY)
        draw.text((x + H_PAD, text_y2), f"{win_rate:.2f}%", font=font, fill=wr_color)

    return canvas


async def generate_scout_image(heroes: list[dict], player_name: str = None) -> BytesIO:
    canvas = await _build_scout_canvas(heroes, player_name)
    fp = BytesIO()
    canvas.save(fp, format="PNG")
    fp.seek(0)
    return fp


class DotaScout(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        description="Scout a player's top 10 most played Dota 2 heroes.",
    )
    async def scout(
        self,
        interaction: ApplicationCommandInteraction,
        player_id: str,
        date: str = commands.Param(default="3month", choices=["3month", "6month", "year"]),
    ):
        """
        Scout a player's top 10 most played Dota 2 heroes.
        Parameters
        ----------
        player_id: Steam32 or Steam64 player ID (visible in your Dotabuff/OpenDota URL).
        date: How far back to look — 3 months, 6 months, or 1 year.
        """
        await interaction.response.defer()

        try:
            steam32 = convert_to_steam32(int(player_id))
        except ValueError:
            await interaction.followup.send(
                "Invalid player ID. Please provide a Steam32 or Steam64 ID.",
                ephemeral=True,
            )
            return

        days = DATE_TO_DAYS[date]

        async with aiohttp.ClientSession() as session:
            try:
                player_heroes, all_heroes = await asyncio.gather(
                    _get_json(session, f"{OPENDOTA_BASE}/players/{steam32}/heroes?date={days}"),
                    _get_json(session, f"{OPENDOTA_BASE}/heroes"),
                )
            except aiohttp.ClientResponseError as e:
                if e.status == 404:
                    await interaction.followup.send(
                        "Player not found. Check the Steam ID.", ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"OpenDota API error (HTTP {e.status}). Try again later.",
                        ephemeral=True,
                    )
                return
            except Exception as e:
                await interaction.followup.send(
                    f"Failed to fetch player data: {e}", ephemeral=True
                )
                return

        hero_lookup = _make_hero_lookup(all_heroes)

        if not player_heroes:
            await interaction.followup.send(
                "No hero data found for this period. The profile may be private.",
                ephemeral=True,
            )
            return

        heroes = _build_heroes(player_heroes, hero_lookup)

        if not heroes:
            await interaction.followup.send(
                "No hero data found for this period.", ephemeral=True
            )
            return

        image_fp = await generate_scout_image(heroes)
        await interaction.followup.send(file=disnake.File(image_fp, filename="scout.png"))

    @commands.slash_command(
        description="Scout up to 5 players' hero pools side-by-side (one image per player).",
    )
    async def scout_team(
        self,
        interaction: ApplicationCommandInteraction,
        player_id_1: str,
        player_id_2: str = None,
        player_id_3: str = None,
        player_id_4: str = None,
        player_id_5: str = None,
        date: str = commands.Param(default="3month", choices=["3month", "6month", "year"]),
    ):
        """
        Scout up to 5 players' top 10 most played Dota 2 heroes.
        Parameters
        ----------
        player_id_1: Steam32 or Steam64 player ID.
        player_id_2: Steam32 or Steam64 player ID (optional).
        player_id_3: Steam32 or Steam64 player ID (optional).
        player_id_4: Steam32 or Steam64 player ID (optional).
        player_id_5: Steam32 or Steam64 player ID (optional).
        date: How far back to look — 3 months, 6 months, or 1 year.
        """
        await interaction.response.defer()

        raw_ids = [player_id_1, player_id_2, player_id_3, player_id_4, player_id_5]
        steam32_ids = []
        for pid in raw_ids:
            if pid is None:
                continue
            try:
                steam32_ids.append(convert_to_steam32(int(pid)))
            except ValueError:
                await interaction.followup.send(
                    f"Invalid player ID: `{pid}`. Please provide Steam32 or Steam64 IDs.",
                    ephemeral=True,
                )
                return

        days = DATE_TO_DAYS[date]

        async with aiohttp.ClientSession() as session:
            try:
                all_heroes = await _get_json(session, f"{OPENDOTA_BASE}/heroes")
            except Exception as e:
                await interaction.followup.send(
                    f"Failed to fetch hero list: {e}", ephemeral=True
                )
                return

            per_player_tasks = [
                asyncio.gather(
                    _get_json(session, f"{OPENDOTA_BASE}/players/{s32}"),
                    _get_json(session, f"{OPENDOTA_BASE}/players/{s32}/heroes?date={days}"),
                )
                for s32 in steam32_ids
            ]
            player_results = await asyncio.gather(*per_player_tasks, return_exceptions=True)

        hero_lookup = _make_hero_lookup(all_heroes)

        canvases = []
        errors = []
        for i, (s32, result) in enumerate(zip(steam32_ids, player_results), start=1):
            if isinstance(result, Exception):
                errors.append(f"Player {i} (`{s32}`): {result}")
                continue

            profile, player_heroes_raw = result
            player_name = (profile.get("profile") or {}).get("personaname") or str(s32)

            if not player_heroes_raw:
                errors.append(f"**{player_name}**: no hero data for this period (profile may be private)")
                continue

            heroes = _build_heroes(player_heroes_raw, hero_lookup)
            if not heroes:
                errors.append(f"**{player_name}**: no hero data for this period")
                continue

            canvas = await _build_scout_canvas(heroes, player_name=player_name)
            canvases.append(canvas)

        if not canvases:
            await interaction.followup.send(
                "No hero data found for any of the provided players.\n" + "\n".join(errors),
                ephemeral=True,
            )
            return

        max_w = max(c.size[0] for c in canvases)
        total_h = sum(c.size[1] for c in canvases) + ROW_GAP * (len(canvases) - 1)
        composite = Image.new("RGB", (max_w, total_h), BG_COLOR)
        y = 0
        for canvas in canvases:
            composite.paste(canvas, (0, y))
            y += canvas.size[1] + ROW_GAP

        fp = BytesIO()
        composite.save(fp, format="PNG")
        fp.seek(0)

        content = "\n".join(errors) if errors else None
        await interaction.followup.send(content=content, file=disnake.File(fp, filename="scout_team.png"))
