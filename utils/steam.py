def convert_to_steam32(steam_id: int) -> int:
    """
    Convert a given SteamID (either Steam64 or Steam32) to Steam32.

    Parameters
    ----------
    steam_id : int
        The SteamID to convert.

    Returns
    -------
    int
        The converted Steam32 ID.
    """
    # SteamID64 identifiers start with '7656'
    if str(steam_id).startswith("7656"):
        # Convert SteamID64 to SteamID32
        return int(steam_id) - 76561197960265728
    else:
        # Assume the ID is already in SteamID32 format
        return steam_id
