import asyncio
from io import BytesIO

import aiohttp
import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands
from PIL import Image, ImageDraw, ImageFont

from config import Configuration
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

LEAGUE_MATCH_LIMIT = 50   # max individual match fetches to avoid API abuse
BANNER_SECTION_GAP = 16   # horizontal gap between sections in draft banner
BANNER_LABEL_H = 18       # height of the section label row
BANNER_TOP_N = 8          # heroes per section in the draft banner
BANNER_ROW_GAP = 8        # extra vertical gap between banner and first player row
SECTION_TITLE_H = 26      # height of bold section title rows
SECTION_SEP_H = 2         # thickness of separator line between sections
SECTION_SEP_GAP = 8       # padding on each side of separator

DATE_TO_LABEL = {
    "1week":  "last week",
    "2week":  "last 2 weeks",
    "1month": "last month",
    "2month": "last 2 months",
    "3month": "last 3 months",
    "6month": "last 6 months",
    "year":   "last year",
}

DATE_TO_DAYS = {
    "1week":  7,
    "2week":  14,
    "1month": 30,
    "2month": 60,
    "3month": 90,
    "6month": 180,
    "year":   365,
}


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default(size)


class _RateLimiter:
    """Sliding-window rate limiter. Allows `calls` requests per `period` seconds."""
    def __init__(self, calls: int, period: float):
        self._sem = asyncio.Semaphore(calls)
        self._period = period

    async def __aenter__(self):
        await self._sem.acquire()
        return self

    async def __aexit__(self, *_):
        asyncio.get_running_loop().call_later(self._period, self._sem.release)


_OPENDOTA_LIMITER: _RateLimiter | None = None


def _get_limiter() -> _RateLimiter:
    global _OPENDOTA_LIMITER
    if _OPENDOTA_LIMITER is None:
        key = Configuration.instance().OPENDOTA_KEY
        _OPENDOTA_LIMITER = _RateLimiter(calls=2950 if key else 55, period=60.0)
    return _OPENDOTA_LIMITER


async def _get_json(session: aiohttp.ClientSession, url: str) -> list | dict:
    key = Configuration.instance().OPENDOTA_KEY
    if key:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}api_key={key}"
    async with _get_limiter():
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


async def _fetch_league_matches(session: aiohttp.ClientSession, league_id: int) -> list[dict]:
    match_id_records = await _get_json(session, f"{OPENDOTA_BASE}/leagues/{league_id}/matchIds")
    if not match_id_records:
        return []
    limited = match_id_records[:LEAGUE_MATCH_LIMIT]
    results = await asyncio.gather(
        *[_get_json(session, f"{OPENDOTA_BASE}/matches/{r}") for r in limited],
        return_exceptions=True,
    )
    return [r for r in results if isinstance(r, dict)]


def _filter_matches_for_team(matches: list[dict], team_id: int) -> list[dict]:
    return [
        m for m in matches
        if m.get("radiant_team_id") == team_id or m.get("dire_team_id") == team_id
    ]


def _determine_team_side(match: dict, steam32_ids: set[int]) -> int | None:
    for p in match.get("players", []):
        if p.get("account_id") in steam32_ids:
            return 0 if p.get("player_slot", 128) < 128 else 1
    return None


async def _ensure_picks_bans(session: aiohttp.ClientSession, matches: list[dict]) -> list[dict]:
    first_with_data = next((m for m in matches if m.get("picks_bans")), None)
    if first_with_data is not None:
        return matches

    limited = matches[:LEAGUE_MATCH_LIMIT]
    results = await asyncio.gather(
        *[_get_json(session, f"{OPENDOTA_BASE}/matches/{m['match_id']}") for m in limited],
        return_exceptions=True,
    )
    return [r for r in results if isinstance(r, dict)]


def _aggregate_league_stats(
    matches: list[dict], steam32_ids: set[int]
) -> tuple[dict, dict, dict, dict, dict]:
    per_player: dict[int, dict[int, dict]] = {}
    own_bans: dict[int, int] = {}
    bans_against: dict[int, int] = {}
    own_picks: dict[int, int] = {}
    opp_picks: dict[int, int] = {}

    for match in matches:
        team_side = _determine_team_side(match, steam32_ids)
        if team_side is None:
            continue

        radiant_win = match.get("radiant_win", False)

        for p in match.get("players", []):
            acct = p.get("account_id")
            if acct not in steam32_ids:
                continue
            hero_id = p.get("hero_id")
            if not hero_id:
                continue
            slot = p.get("player_slot", 128)
            won = (slot < 128) == radiant_win
            stats = per_player.setdefault(acct, {})
            entry = stats.setdefault(hero_id, {"games": 0, "wins": 0})
            entry["games"] += 1
            if won:
                entry["wins"] += 1

        for pb in match.get("picks_bans", []) or []:
            hero_id = pb.get("hero_id")
            if not hero_id:
                continue
            is_pick = pb.get("is_pick", False)
            team = pb.get("team")
            if is_pick:
                if team == team_side:
                    own_picks[hero_id] = own_picks.get(hero_id, 0) + 1
                else:
                    opp_picks[hero_id] = opp_picks.get(hero_id, 0) + 1
            else:
                if team == team_side:
                    own_bans[hero_id] = own_bans.get(hero_id, 0) + 1
                else:
                    bans_against[hero_id] = bans_against.get(hero_id, 0) + 1

    return per_player, own_bans, bans_against, own_picks, opp_picks


def _build_heroes_from_league_stats(
    player_stats: dict[int, dict], hero_lookup: dict
) -> list[dict]:
    sorted_heroes = sorted(player_stats.items(), key=lambda kv: kv[1]["games"], reverse=True)
    heroes = []
    for hero_id, entry in sorted_heroes[:10]:
        games = entry["games"]
        if games == 0:
            continue
        info = hero_lookup.get(hero_id, {})
        heroes.append({
            "name": info.get("localized_name", str(hero_id)),
            "matches": games,
            "win_rate": (entry["wins"] / games) * 100,
            "icon_url": info.get("icon_url", ""),
        })
    return heroes


async def _build_draft_banner_canvas(
    own_bans: dict[int, int],
    bans_against: dict[int, int],
    own_picks: dict[int, int],
    opp_picks: dict[int, int],
    hero_lookup: dict,
) -> Image.Image:
    sections = [
        ("Their Bans", own_bans),
        ("Banned vs Them", bans_against),
        ("Their Picks", own_picks),
        ("Opp Picks", opp_picks),
    ]

    # Build sorted hero lists for each section (top N by count)
    section_heroes: list[list[tuple[int, int]]] = []
    for _, counts in sections:
        top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:BANNER_TOP_N]
        section_heroes.append(top)

    # Collect all icon URLs for concurrent fetch
    all_icon_requests: list[tuple[int, int, str]] = []  # (section_idx, slot_idx, url)
    for si, heroes in enumerate(section_heroes):
        for hi, (hero_id, _) in enumerate(heroes):
            url = hero_lookup.get(hero_id, {}).get("icon_url", "")
            all_icon_requests.append((si, hi, url))

    async with aiohttp.ClientSession() as session:
        icons_flat = await asyncio.gather(
            *[_fetch_hero_image(session, url) for _, _, url in all_icon_requests]
        )

    # Arrange icons back into sections
    icons_by_section: list[list] = [[] for _ in sections]
    for (si, hi, _), icon in zip(all_icon_requests, icons_flat):
        while len(icons_by_section[si]) <= hi:
            icons_by_section[si].append(None)
        icons_by_section[si][hi] = icon

    row_h = BANNER_LABEL_H + CARD_H
    total_w = BANNER_TOP_N * CARD_SLOT - CARD_GAP
    total_h = len(sections) * row_h + (len(sections) - 1) * ROW_GAP

    canvas = Image.new("RGB", (total_w, total_h), BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    label_font = _load_font(13)
    count_font = _load_font(FONT_SIZE)

    y_offset = 0
    for si, (label, _) in enumerate(sections):
        heroes = section_heroes[si]
        icons = icons_by_section[si]

        draw.text((H_PAD, y_offset + (BANNER_LABEL_H - 13) // 2), label, font=label_font, fill="#ffffff")

        icon_y = y_offset + BANNER_LABEL_H + V_PAD
        text_y = icon_y + ICON_H + ICON_TEXT_GAP

        for hi, (hero_id, count) in enumerate(heroes):
            x = hi * CARD_SLOT
            icon = icons[hi] if hi < len(icons) else None
            if icon is not None:
                canvas.paste(icon, (x + H_PAD, icon_y), icon)
            draw.text((x + H_PAD, text_y), f"{count}x", font=count_font, fill=TEXT_GRAY)

        y_offset += row_h + ROW_GAP

    return canvas


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
        date: str = commands.Param(default="3month", choices=["1week", "2week", "1month", "2month", "3month", "6month", "year"]),
        ninja_mode: bool = commands.Param(default=False, description="Only show the result to you"),
    ):
        """
        Scout a player's top 10 most played Dota 2 heroes.
        Parameters
        ----------
        player_id: Steam32 or Steam64 player ID (visible in your Dotabuff/OpenDota URL).
        date: How far back to look — 1 week, 2 weeks, 1 month, 2 months, 3 months, 6 months, or 1 year.
        """
        await interaction.response.defer(ephemeral=ninja_mode)

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
                profile, player_heroes, all_heroes = await asyncio.gather(
                    _get_json(session, f"{OPENDOTA_BASE}/players/{steam32}"),
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
        player_name = (profile.get("profile") or {}).get("personaname") or str(steam32)

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

        image_fp = await generate_scout_image(heroes, player_name)
        await interaction.followup.send(file=disnake.File(image_fp, filename="scout.png"), ephemeral=ninja_mode)

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
        date: str = commands.Param(default="3month", choices=["1week", "2week", "1month", "2month", "3month", "6month", "year"]),
        ninja_mode: bool = commands.Param(default=False, description="Only show the result to you"),
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
        date: How far back to look — 1 week, 2 weeks, 1 month, 2 months, 3 months, 6 months, or 1 year.
        """
        await interaction.response.defer(ephemeral=ninja_mode)

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
        await interaction.followup.send(content=content, file=disnake.File(fp, filename="scout_team.png"), ephemeral=ninja_mode)

    @commands.slash_command(
        description="Scout all players on one side of a Dota 2 match.",
    )
    async def scout_match(
        self,
        interaction: ApplicationCommandInteraction,
        match_id: str,
        side: str = commands.Param(choices=["radiant", "dire"]),
        date: str = commands.Param(default="3month", choices=["1week", "2week", "1month", "2month", "3month", "6month", "year"]),
        ninja_mode: bool = commands.Param(default=False, description="Only show the result to you"),
    ):
        """
        Parameters
        ----------
        match_id: Dota 2 match ID.
        side: Which team to scout — Radiant or Dire.
        date: How far back to look — 1 week, 2 weeks, 1 month, 2 months, 3 months, 6 months, or 1 year.
        """
        await interaction.response.defer(ephemeral=ninja_mode)

        try:
            mid = int(match_id)
        except ValueError:
            await interaction.followup.send("Invalid match ID.", ephemeral=True)
            return

        async with aiohttp.ClientSession() as session:
            try:
                match_data, all_heroes = await asyncio.gather(
                    _get_json(session, f"{OPENDOTA_BASE}/matches/{mid}"),
                    _get_json(session, f"{OPENDOTA_BASE}/heroes"),
                )
            except aiohttp.ClientResponseError as e:
                if e.status == 404:
                    await interaction.followup.send("Match not found.", ephemeral=True)
                else:
                    await interaction.followup.send(
                        f"OpenDota API error (HTTP {e.status}). Try again later.", ephemeral=True
                    )
                return
            except Exception as e:
                await interaction.followup.send(f"Failed to fetch match data: {e}", ephemeral=True)
                return

            players = match_data.get("players", [])
            if side == "radiant":
                team_players = [p for p in players if p.get("player_slot", 128) < 128]
            else:
                team_players = [p for p in players if p.get("player_slot", 0) >= 128]

            steam32_ids = [p["account_id"] for p in team_players if p.get("account_id")]

            if not steam32_ids:
                await interaction.followup.send(
                    "No public player accounts found on that side.", ephemeral=True
                )
                return

            hero_lookup = _make_hero_lookup(all_heroes)
            days = DATE_TO_DAYS[date]

            per_player_tasks = [
                asyncio.gather(
                    _get_json(session, f"{OPENDOTA_BASE}/players/{s32}"),
                    _get_json(session, f"{OPENDOTA_BASE}/players/{s32}/heroes?date={days}"),
                )
                for s32 in steam32_ids
            ]
            player_results = await asyncio.gather(*per_player_tasks, return_exceptions=True)

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
                "No hero data found for any players.\n" + "\n".join(errors), ephemeral=True
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
        await interaction.followup.send(content=content, file=disnake.File(fp, filename="scout_match.png"), ephemeral=ninja_mode)

    async def _scout_league_team_impl(
        self,
        interaction: ApplicationCommandInteraction,
        team_id: int,
        league_id: int,
        date: str,
        ninja_mode: bool,
    ):
        await interaction.response.defer(ephemeral=ninja_mode)

        days = DATE_TO_DAYS[date]

        async with aiohttp.ClientSession() as session:
            try:
                all_heroes, league_matches_raw, league_info, team_info = await asyncio.gather(
                    _get_json(session, f"{OPENDOTA_BASE}/heroes"),
                    _fetch_league_matches(session, league_id),
                    _get_json(session, f"{OPENDOTA_BASE}/leagues/{league_id}"),
                    _get_json(session, f"{OPENDOTA_BASE}/teams/{team_id}"),
                )
            except aiohttp.ClientResponseError as e:
                if e.status == 404:
                    await interaction.followup.send("League not found. Check the league ID.", ephemeral=True)
                else:
                    await interaction.followup.send(f"OpenDota API error (HTTP {e.status}). Try again later.", ephemeral=True)
                return
            except Exception as e:
                await interaction.followup.send(f"Failed to fetch league data: {e}", ephemeral=True)
                return

            if not league_matches_raw:
                await interaction.followup.send("No matches found for this league.", ephemeral=True)
                return

            team_matches = _filter_matches_for_team(league_matches_raw, team_id)
            if not team_matches:
                await interaction.followup.send(
                    f"Team `{team_id}` has no matches in league `{league_id}`.", ephemeral=True
                )
                return

            enriched = await _ensure_picks_bans(session, team_matches)

            # Collect all players who appeared on the team's side across all matches
            all_team_steam32s: set[int] = set()
            for match in enriched:
                team_side = 0 if match.get("radiant_team_id") == team_id else 1
                for p in match.get("players", []):
                    slot = p.get("player_slot", 128)
                    on_team = (slot < 128) == (team_side == 0)
                    if on_team and p.get("account_id"):
                        all_team_steam32s.add(p["account_id"])

            steam32_list = list(all_team_steam32s)
            all_player_results = await asyncio.gather(
                *[_get_json(session, f"{OPENDOTA_BASE}/players/{s32}") for s32 in steam32_list],
                *[_get_json(session, f"{OPENDOTA_BASE}/players/{s32}/heroes?date={days}") for s32 in steam32_list],
                return_exceptions=True,
            )

        n = len(steam32_list)
        profile_results = all_player_results[:n]
        recent_hero_results = all_player_results[n:]

        league_name = (league_info.get("name") or f"League {league_id}") if isinstance(league_info, dict) else f"League {league_id}"
        # Try pro teams API first; fall back to match data for amateur teams
        team_name = (team_info.get("name") or "") if isinstance(team_info, dict) else ""
        if not team_name:
            for match in enriched:
                for side in ("radiant_team", "dire_team"):
                    t = match.get(side) or {}
                    if t.get("team_id") == team_id and t.get("name"):
                        team_name = t["name"]
                        break
                if team_name:
                    break
        if not team_name:
            team_name = f"Team {team_id}"
        hero_lookup = _make_hero_lookup(all_heroes)
        per_player, own_bans, bans_against, own_picks, opp_picks = _aggregate_league_stats(enriched, all_team_steam32s)

        # Seed names from match data (always available, even for untracked profiles)
        name_map: dict[int, str] = {}
        for match in enriched:
            for p in match.get("players", []):
                acct = p.get("account_id")
                if acct and acct in all_team_steam32s and acct not in name_map:
                    name_map[acct] = p.get("personaname") or p.get("name") or str(acct)
        # Override with profile API results where a name is available
        for s32, result in zip(steam32_list, profile_results):
            if not isinstance(result, Exception):
                name = (result.get("profile") or {}).get("personaname")
                if name:
                    name_map[s32] = name
            name_map.setdefault(s32, str(s32))

        sorted_players = sorted(
            per_player.items(),
            key=lambda kv: sum(v["games"] for v in kv[1].values()),
            reverse=True,
        )

        # Build league pick canvases
        league_canvases = []
        for s32, player_stats in sorted_players:
            heroes = _build_heroes_from_league_stats(player_stats, hero_lookup)
            if not heroes:
                continue
            canvas = await _build_scout_canvas(heroes, player_name=name_map.get(s32, str(s32)))
            league_canvases.append(canvas)

        if not league_canvases:
            await interaction.followup.send("No hero data found for this team.", ephemeral=True)
            return

        # Build recent play canvases (same player order)
        recent_hero_map = dict(zip(steam32_list, recent_hero_results))
        recent_canvases = []
        for s32, _ in sorted_players:
            result = recent_hero_map.get(s32)
            if isinstance(result, Exception) or not result:
                continue
            heroes = _build_heroes(result, hero_lookup)
            if not heroes:
                continue
            canvas = await _build_scout_canvas(heroes, player_name=name_map.get(s32, str(s32)))
            recent_canvases.append(canvas)

        banner = await _build_draft_banner_canvas(own_bans, bans_against, own_picks, opp_picks, hero_lookup)

        # --- Composite ---
        def col_h(canvases):
            return sum(c.size[1] for c in canvases) + ROW_GAP * (len(canvases) - 1)

        sep_block_h = SECTION_SEP_GAP + SECTION_SEP_H + SECTION_SEP_GAP

        # Load fonts early so we can measure title text for minimum column width
        heading_font = _load_font(20)
        title_font = _load_font(14)
        small_font = _load_font(11)

        _dummy_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        def _title_text_w(text, subtitle=None):
            w = _dummy_draw.textbbox((0, 0), text, font=title_font)[2]
            if subtitle:
                w += 6 + _dummy_draw.textbbox((0, 0), subtitle, font=small_font)[2]
            return H_PAD + w + H_PAD

        left_title_min_w = _title_text_w(f"{league_name} Picks", f"({len(enriched)} matches)")
        left_w = max(max(c.size[0] for c in league_canvases), left_title_min_w)
        right_w = max(c.size[0] for c in recent_canvases) if recent_canvases else 0
        cols_w = left_w + (BANNER_SECTION_GAP + right_w if recent_canvases else 0)
        max_w = max(banner.size[0], cols_w)

        players_h = max(col_h(league_canvases), col_h(recent_canvases) if recent_canvases else 0)
        HEADING_H = 36
        total_h = (
            HEADING_H + sep_block_h
            + SECTION_TITLE_H + ROW_GAP + banner.size[1]
            + sep_block_h
            + SECTION_TITLE_H + ROW_GAP + players_h
        )

        composite = Image.new("RGB", (max_w, total_h), BG_COLOR)
        draw = ImageDraw.Draw(composite)

        def draw_title(text, y, x=0, subtitle=None):
            draw.text((x + H_PAD, y + (SECTION_TITLE_H - 14) // 2), text, font=title_font, fill="#ffffff")
            if subtitle:
                title_w = draw.textbbox((0, 0), text, font=title_font)[2]
                draw.text((x + H_PAD + title_w + 6, y + (SECTION_TITLE_H - 11) // 2), subtitle, font=small_font, fill=TEXT_GRAY)

        def paste_separator(y):
            draw.line([(0, y + SECTION_SEP_GAP), (max_w, y + SECTION_SEP_GAP)], fill="#555555", width=SECTION_SEP_H)
            return y + sep_block_h

        # Team heading
        draw.text((H_PAD, (HEADING_H - 20) // 2), f"Scouting Report - {team_name} - {league_name}", font=heading_font, fill="#ffffff")
        y = paste_separator(HEADING_H)

        # Section 1: Draft Overview
        draw_title("Draft Overview", y, subtitle=f"({len(enriched)} matches)")
        y += SECTION_TITLE_H + ROW_GAP
        composite.paste(banner, (0, y))
        y += banner.size[1]
        y = paste_separator(y)

        # Sections 2 & 3: side by side
        draw_title(f"{league_name} Picks", y, subtitle=f"({len(enriched)} matches)")
        if recent_canvases:
            right_x = left_w + BANNER_SECTION_GAP
            draw_title("Recently Played", y, x=right_x, subtitle=f"({DATE_TO_LABEL[date]})")
        y += SECTION_TITLE_H + ROW_GAP

        left_y = y
        for c in league_canvases:
            composite.paste(c, (0, left_y))
            left_y += c.size[1] + ROW_GAP

        if recent_canvases:
            right_y = y
            for c in recent_canvases:
                composite.paste(c, (right_x, right_y))
                right_y += c.size[1] + ROW_GAP

        fp = BytesIO()
        composite.save(fp, format="PNG")
        fp.seek(0)
        await interaction.followup.send(file=disnake.File(fp, filename="scout_league_team.png"), ephemeral=ninja_mode)

    @commands.slash_command(
        description="Scout a team's draft history and player hero pools for a specific league.",
    )
    async def scout_league_team(
        self,
        interaction: ApplicationCommandInteraction,
        team_id: int,
        league_id: int,
        date: str = commands.Param(default="3month", choices=["1week", "2week", "1month", "2month", "3month", "6month", "year"]),
        ninja_mode: bool = commands.Param(default=False, description="Only show the result to you"),
    ):
        """
        Parameters
        ----------
        team_id: OpenDota team ID (visible in the team's OpenDota/Dotabuff URL).
        league_id: League/tournament ID. e.g. 19382 = Kobold Season 3
        date: How far back to look for the Recently Played section.
        """
        await self._scout_league_team_impl(interaction, team_id, league_id, date, ninja_mode)

    @commands.slash_command(
        description="Scout a Kobold Season 3 team's draft history and player hero pools.",
    )
    async def scout_kobold_team(
        self,
        interaction: ApplicationCommandInteraction,
        team_id: int,
        date: str = commands.Param(default="3month", choices=["1week", "2week", "1month", "2month", "3month", "6month", "year"]),
        ninja_mode: bool = commands.Param(default=False, description="Only show the result to you"),
    ):
        """
        Parameters
        ----------
        team_id: OpenDota team ID (visible in the team's OpenDota/Dotabuff URL).
        date: How far back to look for the Recently Played section.
        """
        await self._scout_league_team_impl(interaction, team_id, 19382, date, ninja_mode)
