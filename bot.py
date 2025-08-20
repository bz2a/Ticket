# bot.py
import nextcord
from nextcord.ext import commands
import os
import config 


intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(intents=intents)


@bot.event
async def on_ready():
    print(f'Logged in as: {bot.user.name}')
    print('Bot is ready and connected to Discord!')
    print('------')

if __name__ == '__main__':
    
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('_'):
            try:
                bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Successfully loaded cog: {filename}')
            except Exception as e:
                print(f'Failed to load cog {filename}: {e.__class__.__name__} - {e}')
    
    bot.run(config.BOT_TOKEN)