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
            cls._instance.GUILD_ID: int = int(config['discord']['GUILD_ID'])
            cls._instance.CLIENT_ID: int = int(config['discord']['CLIENT_ID'])
            cls._instance.TOKEN: str = config['discord']['TOKEN']
            cls._instance.OPENAI_KEY: str = config['openai']['KEY']

        return cls._instance
