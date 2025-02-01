import os                         # Handle Environment Variable querying for script secrets
from dotenv import load_dotenv    # Handle Environment Variable querying for script secrets
import discord                    # Handles Discord API Communications with Server (Guild in documentation)
from discord.ext import commands  # Handle Custom Server Commands
from lib import bot_commands      # Custom Commands defined

# Load environment variables
load_dotenv()
discord_token = os.getenv('DISCORD_TOKEN')

if not discord_token:
    raise EnvironmentError("[-] DISCORD_TOKEN not found in environment variables.")

# Ensure Discord bot has necessary intents (aka Guild permissions)
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Register the commands from lib.bot_commands
bot.add_command(bot_commands.server_find)
bot.add_command(bot_commands.player_find)

# Bot ready event
@bot.event
async def on_ready():
    print(f"{bot.user} is ready to query some Rust servers.")

# Run the bot
if __name__ == "__main__":
    try:
        bot.run(discord_token)
    except Exception as e:
        print(f"[-] Error occurred: {e}")