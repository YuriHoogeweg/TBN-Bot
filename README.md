# Configuration

config.ini:

## [discord]  

**GUILD_ID**  
Server ID that commands should be limited to. If this is left empty the bot registers them as global commands, which work _everywhere_ (including DMs) and take a lot longer to propagate. Set this to your own test server during development. 
Discord have a decent [help article](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-) to help you find these.

**CLIENT_ID**  
Your bot user's Client ID. Currently unused.

**TOKEN**  
Your bot's authentication token. If you're not sure how to get this, you can learn how to set up a bot account [here](https://discord.com/developers/docs/getting-started#creating-an-app)

## [openai]
**KEY**  
Your [OpenAI API key](https://platform.openai.com/account/api-keys)

# Resources

The following are some resources that might come in handy if you want to tinker with making the bot do something useful:

1. https://github.com/ValvePython/dota2 
2. http://steamwebapi.azurewebsites.net/
3. https://pypi.org/project/stratz/
4. https://pypi.org/project/pyopendota/
5. https://github.com/mdiller/MangoByte