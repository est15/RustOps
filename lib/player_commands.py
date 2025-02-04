import asyncio # Handle retrieving any timeout based errors
from discord import app_commands # Handles Discord API Communications with Server (Guild in documentation)
from discord.ext import commands # Handle Custom Server Commands
from discord import Interaction
from lib.battlemetrics import ApiClient # Methods to Query BattleMetrics API
from lib.steam import steamClient # Methods to Query Steam Web API
from lib.utils import activeServer # Methods to handle the active server configuration
from lib.db import database # Methods to handle group database interactions 

# Initialize Battle Metrics API Client (sets BM API Bearer Token)
battlemettrics = ApiClient()
steam = steamClient()
active = activeServer()

# Initializee database's Methods
db = database()

# [!] PLAYER COMMAND GROUP 
class PlayerCommandGroup(app_commands.Group):
    # Inherit app_commands.Group's method to append our own
    # /player Commands
    def __init__(self):
        super().__init__(name="player", description="Rust player specific commands")

plyrcmds = PlayerCommandGroup()

# Player find bot command
@plyrcmds.command(name="check", description="Checks if player is active against set active server")
async def player_find(interaction: Interaction, player: str):
    # Exchange steam profile URL instead display name
    # Then run the returned display name against BattleMetric's API
    try:
        _, player = steam.get_player_info(player) # Unused Variable == profile_ID (not implemented in this method)
        
        # [!] Get Active Server:
        server_results = await active.get_server()
        if server_results:
            server_id, _ = server_results.split(":")  # Unused Variable == server_name
            
            # Call the BattleMetric's API to check if player is active
            result_msg, result = battlemettrics.send_request(1, server_id.strip(), player.strip())
            # Playuer is Active
            if result == 1:
                await interaction.response.send_message(result_msg)
            # Player NOT Active
            elif result == 0:
                await interaction.response.send_message(result_msg)
        else:
            await interaction.response.send_message("[-] **no server set**\nset server: `/server set <Server Name>`")
    except Exception as e:
        print(f"[-] ply_fnd_cmd Error: {e}")