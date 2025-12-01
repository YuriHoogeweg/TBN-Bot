from disnake import ApplicationCommandInteraction
import disnake
from disnake.ext import commands
from config import Configuration
import re
import yt_dlp
import asyncio
import os

'''
TODO:
+ Add listener so that it reacts to links without having to do anything manually
+ Recognize video links
+ Add option to keep embed
'''


INSTAGRAM_REGEX = re.compile(
    r"(https?://(?:www\.)?instagram\.com/[^\s>]+)", re.IGNORECASE
)

REDDIT_REGEX = re.compile(r"(https?://(?:www\.)?reddit\.com/[^\s>]+)", re.IGNORECASE)

# Max size for the file, idk what it should be so feel free to change it.
MAX_DISCORD_FILE_SIZE = 96 * 1024 * 1024  # 96 MB


class EmbedVideo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def download_video(self, url: str) -> str | None:
        """
        Downloads a video to the current folder using yt-dlp.
        Returns the actual downloaded file path.
        """
        loop = asyncio.get_running_loop()
        result = {"path": None, "error": None}

        
        # Need to download ffmpeg and the folder to root (or change this path)!
        ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg", "bin")

        def async_download():
            try:
                output_tmpl = "resources/downloads/%(title)s.%(ext)s"

                ydl_opts = {
                    "outtmpl": output_tmpl,
                    "noplaylist": True,
                    "quiet": True,
                    "no_warnings": True,
                    "ffmpeg_location": ffmpeg_path,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)

                    filepath = None
                    requested = info.get("requested_downloads")

                    if requested and isinstance(requested, list):
                        filepath = requested[0].get("filepath")

                    if not filepath:
                        filepath = ydl.prepare_filename(info)

                    result["path"] = filepath

            except Exception as e:
                result["error"] = e

        await loop.run_in_executor(None, async_download)

        if result["error"]:
            print("[download_video] Error:", result["error"])
            return None

        file_path = result["path"]

        if not file_path or not os.path.exists(file_path):
            print("[download_video] File not found after download:", file_path)
            return None

        size = os.path.getsize(file_path)

        if size == 0:
            print("[download_video] EMPTY FILE ???", file_path)
            os.remove(file_path)
            return None

        if size > MAX_DISCORD_FILE_SIZE:
            print("[download_video] File too large:", size)
            os.remove(file_path)
            return None

        return file_path

    @commands.slash_command(
        guild_ids=[Configuration.instance().GUILD_ID],
        name="embed_video",
        description="Embeds Reddit or Instagram video to message"
    )
    async def embed_video(
        self,
        inter: ApplicationCommandInteraction,
        url: str,
    ):
        if inter.author.bot:
            return

        await inter.response.defer(ephemeral=True)
        
        # Saving this here for later, not really necessary right now
        # ----------------------------------------------------------
        # insta_links = INSTAGRAM_REGEX.findall(url)
        # reddit_links = REDDIT_REGEX.findall(url)
        # links = insta_links + reddit_links
        links = [url]

        if not links:
            await inter.edit_original_response(
                content="No valid Instagram or Reddit links found in that URL.",
            )
            return

        await inter.edit_original_response(content="Downloading video, please wait...")

        any_success = False

        for link in links:
            file_path = await self.download_video(link)

            if file_path:
                any_success = True
                try:
                    await inter.followup.send(
                        content=f"{link}",
                        suppress_embeds=True,
                        file=disnake.File(file_path)
                    )
                except Exception as e:
                    print(f"[embed_video] Failed to send file: {e}")
                    await inter.followup.send(
                        content=f"Downloaded the video for {link}, but failed to send it to Discord.",
                        ephemeral=True,
                    )
                finally:
                    try:
                        os.remove(file_path)
                    except FileNotFoundError:
                        pass
            else:
                await inter.followup.send(
                    content=f"Could not download video from: {link} (it might still be processing or too large).",
                    ephemeral=True,
                )

            if not any_success:
                await inter.edit_original_response(
                    content="Failed to download any videos from the provided URL(s)."
                )
            else:
                await inter.edit_original_response(
                    content="Here is the embedded video!"
                )


def setup(bot: commands.Bot):
    bot.add_cog(EmbedVideo(bot))
