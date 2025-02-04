import os                         # Handle Environment Variable querying for script secrets
from dotenv import load_dotenv    # Handle Environment Variable querying for script secrets
import discord                    # Handles Discord API Communications with Server (Guild in documentation)
from discord.ext import commands  # Handle Custom Server Commands
from lib import group_commands, player_commands, server_commands  # Custom Discord bot command groups defined

# Load environment variables
load_dotenv()
discord_token = os.getenv('DISCORD_TOKEN')

if not discord_token:
    raise EnvironmentError("[-] DISCORD_TOKEN not found in environment variables.")

# Ensure Discord bot has necessary intents (aka Guild permissions)
intents = discord.Intents.default()
intents.message_content = True # Deprecated only intents.message = True is necessary
intents.messages = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Register the commands from lib.bot_commands
#bot.add_command(bot_commands.server_find)
bot.tree.add_command(player_commands.plyrcmds)
bot.tree.add_command(server_commands.actsrv)
bot.tree.add_command(group_commands.grpcmds)

# Bot ready event
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} is ready to query some Rust servers.")

# Run the bot
if __name__ == "__main__":
    try:
        bot.run(discord_token)
    except Exception as e:
        print(f"[-] Error occurred: {e}")