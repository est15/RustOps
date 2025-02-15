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

@plyrcmds.command(name="check", description="Checks if a player is active against set active server")
async def player_find(interaction: Interaction, player_input: str):
    try:
        # Tell Discord to defer the response while processing
        await interaction.response.defer()

        battle_id = None  # Default empty
        steam_id = None   # Default empty
        username = None   # Default empty
        #encoding_issue_notif = ""  # If encoding issue in player's display name
        # ^^^ not used but should be implemented for end-user clarity at some point

        # [STEP 1] **Determine Input Type (Username, BattleMetrics ID, or Steam ID)**
        if 'https://' in player_input: 
            _, found_name = steam.get_player_info(player_input) # steam_id = unused variable
            username = found_name
        elif player_input.isdigit():
            battle_id = player_input
        else:
            username = player_input

        # [STEP 2] **Get Active Server**
        server_results = await active.get_server()
        if not server_results:
            await interaction.followup.send("[-] **No server set**\nSet server: `/server set <Server ID>`")
            return

        server_id, server_name = server_results.split(":", 1)
        server_id = server_id.strip()
        server_name = server_name.strip()

        # [STEP 3A] If we already have a numeric BM ID => skip name-based searching
        if battle_id:
            player_data = battlemettrics.get_player_by_id(server_id, battle_id)
            if not player_data:
                await interaction.followup.send(
                    f"```[-] Player with ID {battle_id} not found on server {server_name}.```"
                )
                return

            display_name = player_data['attributes']['name']
            #    Use the new server-specific single check for final output
            final_str = battlemettrics.server_player_check_single(server_id, battle_id, display_name)
            await interaction.followup.send(f"```{final_str}```")
            return

        # [STEP 3B] If we have a username => do name-based searching
        if username:
            result = battlemettrics.single_player_check(
                server_id=server_id,
                server_name=server_name,
                trgt_player=username.strip()
            )

            # [STEP 4] Interpret the single_player_check response
            if not result:
                await interaction.followup.send("```[-] No matching players found on the server.```")
                return

            # If the first element is None => multiple matches
            if len(result) == 3 and result[0] is None:
                await interaction.followup.send(result[2])
                return

            # If it's a single-element list => it's an error or short info
            if len(result) == 1:
                await interaction.followup.send(result[0])
                return

            # Otherwise, we got [battle_id, name, message]
            if len(result) == 3:
                _, _, message = result
                await interaction.followup.send(message)
                return

            # fallback
            await interaction.followup.send("[-] Unexpected single_player_check response.")
            return

        # If no ID or username
        await interaction.followup.send("```[-] No player input provided.```")

    except Exception as e:
        print(f"[-] ply_fnd_cmd Error: {e}")
        await interaction.followup.send("```[-] Something went wrong while checking that player.```")