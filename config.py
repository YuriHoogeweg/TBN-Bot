from configparser import ConfigParser

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
            cls._instance.GUILD_ID = int(config['discord']['GUILD_ID'])
            cls._instance.CLIENT_ID = int(config['discord']['CLIENT_ID'])
            cls._instance.TOKEN = config['discord']['TOKEN']
            cls._instance.OPENAI_KEY = config['openai']['KEY']
            cls._instance.BIRTHDAYS_CHANNEL_ID = int(
                config['discord']['BIRTHDAYS_CHANNEL_ID'])
            cls._instance.DOTABUFF_EMOJI = config['discord']['DOTABUFF_EMOJI']
            cls._instance.TWITCH_EMOJI = config['discord']['TWITCH_EMOJI']
            cls._instance.LIQUIPEDIA_EMOJI = config['discord']['LIQUIPEDIA_EMOJI']
            cls._instance.YOUTUBE_EMOJI = config['discord']['YOUTUBE_EMOJI']
            cls._instance.PODCAST_PARTICIPANT_ROLE_ID = int(config['discord']['PODCAST_PARTICIPANT_ROLE_ID'])
            cls._instance.PODCAST_CHANNEL_ID = int(config['discord']['PODCAST_CHANNEL_ID'])
            cls._instance.SOCIAL_CATEGORY_ID = int(config['discord']['SOCIAL_CATEGORY_ID'])
            cls._instance.ARCHIVE_CATEGORY_ID = int(config['discord']['ARCHIVE_CATEGORY_ID'])
            cls._instance.BOT_CHANNEL_ID = int(config['discord']['BOT_CHANNEL_ID'])
            cls._instance.STREAMER_ROLE_ID = int(config['discord']['STREAMER_ROLE_ID'])
            cls._instance.BIRTHDAY_ROLE_ID = int(config['discord']['BIRTHDAY_ROLE_ID'])
        return cls._instance
