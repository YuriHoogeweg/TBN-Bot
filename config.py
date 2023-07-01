from configparser import ConfigParser
import logging


class Configuration:
    _instance = None

    def __init__(self):
        raise RuntimeError('Call instance() instead')

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls.__new__(cls)

            # Read config variables from config.ini
            config = ConfigParser()
            config.read('config.ini')
            cls._instance.GUILD_ID: int = int(config['discord']['GUILD_ID'])
            cls._instance.CLIENT_ID: int = int(config['discord']['CLIENT_ID'])
            cls._instance.TOKEN: str = config['discord']['TOKEN']
            cls._instance.OPENAI_KEY: str = config['openai']['KEY']
            cls._instance.BIRTHDAYS_CHANNEL_ID: int = int(
                config['discord']['BIRTHDAYS_CHANNEL_ID'])
            cls._instance.DOTABUFF_EMOJI: str = config['discord']['DOTABUFF_EMOJI']
            cls._instance.TWITCH_EMOJI: str = config['discord']['TWITCH_EMOJI']
            cls._instance.LIQUIPEDIA_EMOJI: str = config['discord']['LIQUIPEDIA_EMOJI']
            cls._instance.YOUTUBE_EMOJI: str = config['discord']['YOUTUBE_EMOJI']
            cls._instance.PODCAST_PARTICIPANT_ROLE_ID: int = int(config['discord']['PODCAST_PARTICIPANT_ROLE_ID'])
            cls._instance.PODCAST_CHANNEL_ID: int = int(config['discord']['PODCAST_CHANNEL_ID'])
            cls._instance.SOCIAL_CATEGORY_ID: int = int(config['discord']['SOCIAL_CATEGORY_ID'])
            cls._instance.ARCHIVE_CATEGORY_ID: int = int(config['discord']['ARCHIVE_CATEGORY_ID'])
        return cls._instance
