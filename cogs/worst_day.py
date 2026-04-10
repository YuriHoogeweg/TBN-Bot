import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO

import aiohttp
import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands
from PIL import Image, ImageDraw, ImageFont

from utils.opendota import OPENDOTA_BASE, fetch_image, get_json
from utils.steam import convert_to_steam32

logger = logging.getLogger(__name__)

MEDALS = ["🥇", "🥈", "🥉"]

# OpenDota lobby_type values.
LOBBY_TYPE_LABELS = {
    -1: "Invalid",
    0: "Normal",
    1: "Practice",
    2: "Tournament",
    3: "Tutorial",
    4: "Co-op Bots",
    5: "Team Match",
    6: "Solo Queue",
    7: "Ranked",
    8: "1v1 Mid",
    9: "Battle Cup",
}

# Layout constants for the match-history image.
BG_COLOR = "#23272A"
ROW_BG_WIN = "#1d3324"
ROW_BG_LOSS = "#3a1f1f"
WIN_GREEN = "#4CAF50"
LOSS_RED = "#F44336"
TEXT_GRAY = "#aaaaaa"
WHITE = "#ffffff"

H_PAD = 12
V_PAD = 10
ROW_V_PAD = 8
ICON_W, ICON_H = 96, 54
# Dota item icons are natively 88x64 (11:8 landscape) — preserve that ratio.
ITEM_W, ITEM_H = 44, 32
ITEM_GAP = 2
ITEMS_W = 6 * ITEM_W + 5 * ITEM_GAP
HERO_TEXT_W = 170
RESULT_W = 80
COL_GAP = 12
ROW_H = 2 * ROW_V_PAD + ICON_H
HEADER_H = 40

IMAGE_W = (
    H_PAD + ICON_W + COL_GAP + HERO_TEXT_W + COL_GAP + ITEMS_W + COL_GAP + RESULT_W + H_PAD
)

HERO_ICON_PATH = "/apps/dota2/images/dota_react/heroes/{short}.png"


def _load_font(size: int):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default(size)


def _build_hero_lookup(all_heroes: list) -> dict[int, dict]:
    lookup = {}
    for h in all_heroes:
        short = h["name"].replace("npc_dota_hero_", "")
        lookup[h["id"]] = {
            "name": h["localized_name"],
            "icon_url": HERO_ICON_PATH.format(short=short),
        }
    return lookup


def _build_item_lookup(items_constants: dict) -> dict[int, dict]:
    lookup = {}
    for name, data in items_constants.items():
        iid = data.get("id")
        if iid is None:
            continue
        lookup[iid] = {
            "name": data.get("dname") or name,
            "icon_url": data.get("img", ""),
        }
    return lookup


class WorstDay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="worst_day",
        description="Find a player's worst day in Dota 2 (biggest loss - win delta).",
    )
    async def worst_day(
        self,
        interaction: ApplicationCommandInteraction,
        player_id: str,
    ):
        """
        Find a player's worst day in Dota 2 — the day they had the biggest loss-to-win delta.
        Parameters
        ----------
        player_id: Steam32 or Steam64 player ID (visible in your Dotabuff/OpenDota URL).
        """
        await self._run_day_command(interaction, player_id, best=False)

    @commands.slash_command(
        name="best_day",
        description="Find a player's best day in Dota 2 (biggest win - loss delta).",
    )
    async def best_day(
        self,
        interaction: ApplicationCommandInteraction,
        player_id: str,
    ):
        """
        Find a player's best day in Dota 2 — the day they had the biggest win-to-loss delta.
        Parameters
        ----------
        player_id: Steam32 or Steam64 player ID (visible in your Dotabuff/OpenDota URL).
        """
        await self._run_day_command(interaction, player_id, best=True)

    async def _run_day_command(
        self,
        interaction: ApplicationCommandInteraction,
        player_id: str,
        *,
        best: bool,
    ):
        noun = "best" if best else "worst"

        try:
            steam32 = convert_to_steam32(int(player_id))
        except ValueError:
            await interaction.response.send_message(
                "Invalid player ID. Please provide a Steam32 or Steam64 ID.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session_http:
                profile, matches, all_heroes, items_constants = await asyncio.gather(
                    get_json(session_http, f"{OPENDOTA_BASE}/players/{steam32}"),
                    get_json(session_http, f"{OPENDOTA_BASE}/players/{steam32}/matches"),
                    get_json(session_http, f"{OPENDOTA_BASE}/heroes"),
                    get_json(session_http, f"{OPENDOTA_BASE}/constants/items"),
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
            logger.error(f"Failed to fetch {noun}_day data for {steam32}: {e}")
            await interaction.followup.send(
                f"Failed to fetch Dota data: {e}", ephemeral=True
            )
            return

        player_name = (profile.get("profile") or {}).get("personaname") or str(steam32)

        if not matches:
            await interaction.followup.send(
                f"No matches found on OpenDota for {player_name}. Their profile may be private.",
                ephemeral=True,
            )
            return

        top_days = _compute_top_days(matches, top_n=3, best=best)

        if not top_days:
            await interaction.followup.send(
                f"No match data to analyse for {player_name}.", ephemeral=True
            )
            return

        top_delta = (top_days[0]["wins"] - top_days[0]["losses"]) if best else (top_days[0]["losses"] - top_days[0]["wins"])
        if top_delta <= 0:
            msg = (
                f"{player_name} has no winning days on record. Better luck next time."
                if best
                else f"{player_name} has no losing days on record. Lucky them."
            )
            await interaction.followup.send(msg, ephemeral=True)
            return

        hero_lookup = _build_hero_lookup(all_heroes)
        item_lookup = _build_item_lookup(items_constants)

        embed = disnake.Embed(
            title=f"{player_name}'s {noun} days in Dota",
            color=disnake.Color.green() if best else disnake.Color.red(),
        )
        for idx, day in enumerate(top_days):
            medal = MEDALS[idx] if idx < len(MEDALS) else f"#{idx + 1}"
            top_hero_id = max(day["hero_counts"].items(), key=lambda kv: kv[1])[0]
            top_hero_name = hero_lookup.get(top_hero_id, {}).get("name", "Unknown")
            if best:
                delta = day["wins"] - day["losses"]
                delta_str = f"(+{delta})"
            else:
                delta = day["losses"] - day["wins"]
                delta_str = f"(−{delta})"
            embed.add_field(
                name=f"{medal} {day['date'].isoformat()}",
                value=(
                    f"**{day['wins']}W – {day['losses']}L** {delta_str} · "
                    f"{day['games']} games · most played: {top_hero_name}"
                ),
                inline=False,
            )

        # Render a match-history image for the single top day.
        top_day_date = top_days[0]["date"]
        day_matches = [
            m for m in matches
            if m.get("start_time") is not None
            and datetime.fromtimestamp(m["start_time"], tz=timezone.utc).date() == top_day_date
        ]
        day_matches.sort(key=lambda m: m.get("start_time", 0))

        filename = f"{noun}_day.png"
        image_file = None
        try:
            rows = await _build_match_rows(day_matches, steam32)
            if rows:
                image_fp = await _render_match_history_image(
                    rows,
                    top_day_date,
                    player_name,
                    hero_lookup,
                    item_lookup,
                )
                image_file = disnake.File(image_fp, filename=filename)
                embed.set_image(url=f"attachment://{filename}")
        except Exception as e:
            logger.error(f"Failed to render {noun}-day image for {steam32}: {e}")

        if image_file is not None:
            await interaction.followup.send(embed=embed, file=image_file)
        else:
            await interaction.followup.send(embed=embed)


def _compute_top_days(matches: list, top_n: int, best: bool) -> list[dict]:
    daily: dict = defaultdict(lambda: {"wins": 0, "losses": 0, "games": 0, "hero_counts": defaultdict(int)})
    for m in matches:
        start_time = m.get("start_time")
        radiant_win = m.get("radiant_win")
        player_slot = m.get("player_slot")
        if start_time is None or radiant_win is None or player_slot is None:
            continue
        won = (player_slot < 128) == radiant_win
        day = datetime.fromtimestamp(start_time, tz=timezone.utc).date()
        bucket = daily[day]
        bucket["games"] += 1
        bucket["wins" if won else "losses"] += 1
        hero_id = m.get("hero_id")
        if hero_id is not None:
            bucket["hero_counts"][hero_id] += 1

    entries = [
        {"date": day, **stats}
        for day, stats in daily.items()
    ]
    entries.sort(
        key=lambda e: (
            (e["wins"] - e["losses"]) if best else (e["losses"] - e["wins"]),
            e["games"],
            e["date"],
        ),
        reverse=True,
    )
    return entries[:top_n]


async def _build_match_rows(day_matches: list, steam32: int) -> list[dict]:
    """Fetch match details in parallel and extract render-ready rows."""
    if not day_matches:
        return []

    async with aiohttp.ClientSession() as session_http:
        details = await asyncio.gather(
            *[
                get_json(session_http, f"{OPENDOTA_BASE}/matches/{m['match_id']}")
                for m in day_matches
            ],
            return_exceptions=True,
        )

    rows: list[dict] = []
    for list_entry, detail in zip(day_matches, details):
        items = [0] * 6
        if isinstance(detail, dict):
            player = _find_player(detail, steam32, list_entry.get("player_slot"))
            if player is not None:
                items = [player.get(f"item_{i}", 0) or 0 for i in range(6)]
        won = (list_entry["player_slot"] < 128) == list_entry["radiant_win"]
        rows.append({
            "hero_id": list_entry.get("hero_id"),
            "kills": list_entry.get("kills", 0),
            "deaths": list_entry.get("deaths", 0),
            "assists": list_entry.get("assists", 0),
            "duration": list_entry.get("duration", 0),
            "items": items,
            "won": won,
            "lobby_type": list_entry.get("lobby_type"),
            "start_time": list_entry.get("start_time", 0),
        })
    return rows


def _find_player(match_detail: dict, steam32: int, fallback_slot: int | None) -> dict | None:
    players = match_detail.get("players", [])
    for p in players:
        if p.get("account_id") == steam32:
            return p
    # Fallback: match by player_slot if account_id wasn't populated (e.g. private profile).
    if fallback_slot is not None:
        for p in players:
            if p.get("player_slot") == fallback_slot:
                return p
    return None


async def _render_match_history_image(
    rows: list[dict],
    day_date,
    player_name: str,
    hero_lookup: dict,
    item_lookup: dict,
) -> BytesIO:
    wins = sum(1 for r in rows if r["won"])
    losses = len(rows) - wins

    height = HEADER_H + len(rows) * ROW_H + V_PAD
    canvas = Image.new("RGB", (IMAGE_W, height), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    title_font = _load_font(16)
    name_font = _load_font(13)
    kda_font = _load_font(14)
    small_font = _load_font(12)

    header_text = f"{player_name} — {day_date.isoformat()}   {wins}W – {losses}L"
    draw.text((H_PAD, (HEADER_H - 16) // 2), header_text, font=title_font, fill=WHITE)

    # Fetch all images in parallel (hero icons + item icons).
    async with aiohttp.ClientSession() as session_http:
        hero_coros = [
            fetch_image(
                session_http,
                hero_lookup.get(r["hero_id"], {}).get("icon_url", ""),
                (ICON_W, ICON_H),
            )
            for r in rows
        ]
        # Flatten (row_idx, item_idx, item_id) for item slots.
        item_jobs: list[tuple[int, int, int]] = []
        item_coros = []
        for ri, r in enumerate(rows):
            for ii, iid in enumerate(r["items"]):
                if iid and iid > 0:
                    item_jobs.append((ri, ii, iid))
                    item_coros.append(
                        fetch_image(
                            session_http,
                            item_lookup.get(iid, {}).get("icon_url", ""),
                            (ITEM_W, ITEM_H),
                        )
                    )

        hero_images, item_images = await asyncio.gather(
            asyncio.gather(*hero_coros),
            asyncio.gather(*item_coros) if item_coros else _noop(),
        )

    # Reassemble item images into a [row][slot] grid.
    row_item_images: list[list] = [[None] * 6 for _ in rows]
    for (ri, ii, _iid), img in zip(item_jobs, item_images):
        row_item_images[ri][ii] = img

    for i, row in enumerate(rows):
        y = HEADER_H + i * ROW_H
        row_bg = ROW_BG_WIN if row["won"] else ROW_BG_LOSS
        draw.rectangle((0, y, IMAGE_W, y + ROW_H), fill=row_bg)

        hero_x = H_PAD
        hero_y = y + ROW_V_PAD
        hero_img = hero_images[i]
        if hero_img is not None:
            canvas.paste(hero_img, (hero_x, hero_y), hero_img)
        else:
            draw.rectangle((hero_x, hero_y, hero_x + ICON_W, hero_y + ICON_H), outline="#555555")

        text_x = hero_x + ICON_W + COL_GAP
        text_y1 = y + ROW_V_PAD + 2
        text_y2 = text_y1 + 17
        text_y3 = text_y2 + 17
        hero_name = hero_lookup.get(row["hero_id"], {}).get("name", "Unknown")
        draw.text((text_x, text_y1), hero_name, font=name_font, fill=WHITE)
        draw.text(
            (text_x, text_y2),
            f"{row['kills']}/{row['deaths']}/{row['assists']}",
            font=kda_font,
            fill=TEXT_GRAY,
        )
        lobby_label = LOBBY_TYPE_LABELS.get(row.get("lobby_type"), "Unknown")
        draw.text((text_x, text_y3), lobby_label, font=small_font, fill=TEXT_GRAY)

        items_x = text_x + HERO_TEXT_W + COL_GAP
        items_y = y + ROW_V_PAD + (ICON_H - ITEM_H) // 2
        for k in range(6):
            ix = items_x + k * (ITEM_W + ITEM_GAP)
            slot_img = row_item_images[i][k]
            if slot_img is not None:
                canvas.paste(slot_img, (ix, items_y), slot_img)
            else:
                draw.rectangle(
                    (ix, items_y, ix + ITEM_W, items_y + ITEM_H),
                    outline="#444444",
                )

        result_x = items_x + ITEMS_W + COL_GAP
        result_label = "WON" if row["won"] else "LOST"
        result_color = WIN_GREEN if row["won"] else LOSS_RED
        draw.text((result_x, text_y1), result_label, font=name_font, fill=result_color)

        mins, secs = divmod(int(row["duration"]), 60)
        draw.text(
            (result_x, text_y2),
            f"{mins}:{secs:02d}",
            font=small_font,
            fill=TEXT_GRAY,
        )

    fp = BytesIO()
    canvas.save(fp, format="PNG")
    fp.seek(0)
    return fp


async def _noop():
    return []
