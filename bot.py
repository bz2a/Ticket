# bot.py
import nextcord
from nextcord.ext import commands
import os
import config 

# --- إعدادات البوت ---
intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(intents=intents)

# --- حدث التشغيل ---
@bot.event
async def on_ready():
    print(f'Logged in as: {bot.user.name}')
    print('Bot is ready and connected to Discord!')
    print('------')

# --- تحميل الـ Cogs ---
if __name__ == '__main__':
    # ✅ الإصلاح هنا: تجاهل الملفات التي تبدأ بـ __
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('_'):
            try:
                bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Successfully loaded cog: {filename}')
            except Exception as e:
                print(f'Failed to load cog {filename}: {e.__class__.__name__} - {e}')
    
    bot.run(config.BOT_TOKEN)