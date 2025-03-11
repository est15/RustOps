import asyncio # Handle retrieving any timeout based errors
from discord import app_commands # Handles Discord API Communications with Server (Guild in documentation)
from discord.ext import commands # Handle Custom Server Commands
from discord import Interaction
from lib.battlemetrics import ApiClient # Methods to Query BattleMetrics API
from lib.steam import steamClient # Methods to Query Steam Web API
from lib.db import activeServer # Methods to handle the active server configuration
from lib.db import database # Methods to handle group database interactions
import re

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
        username = None   # Default empty
        #encoding_issue_notif = ""  # If encoding issue in player's display name
        # ^^^ not used but should be implemented for end-user clarity

        # [STEP 1] Determine Input Type (Username, BattleMetrics ID, or Steam ID)
        # Steam Profile URL
        if 'https://steamcommunity.com/' in player_input:
            _, found_name = steam.get_player_info(player_input) # Unused var steam_player_id
            username = found_name

        # BattleMetrics Player URL
        elif 'https://www.battlemetrics.com/players/' in player_input:
            # Extract BattleMetrics Player ID
            battle_id_regex = re.search(r"(\d{5,11})", player_input)  # [UPDATED] Fixed regex for extracting IDs

            # If ID was grabbed:
            if battle_id_regex:
                battle_id = battle_id_regex.group(1)  # [UPDATED] Extract only the ID portion
            else:
                await interaction.response.send_message("```[-] Error: Improper URL or BattleID Provided```")
                return  # [UPDATED] Added return to stop further execution on error

        # [!] 
        # If a player (Steam or BattleMetrics) ID is passed directly, verify if it's a Steam ID
        elif player_input.isdigit():
            id_type_check = steam.is_valid_steam_id(player_input)

            # Valid Steam ID
            if id_type_check:
                _, found_name = steam.get_player_info(player_input) # Unused var steam_player_id
                username = found_name
            # BattleMetrics ID
            else:
                battle_id = player_input

        # If none of the above, then they must have passed a username directly
        else:
            username = player_input

        # [STEP 2] Get Active Server
        server_results = active.get_server() # Returns [server_id, server_name]
        if not server_results:
            await interaction.followup.send_message("```[-] No Server Set\nSet Server: /server set <Server Name>```")
            return

        server_id, server_name = server_results

        # [STEP 3A] If we already have a numeric BM ID => skip name-based searching
        if battle_id:
            player_data = battlemettrics.get_player_by_id(battle_id)
            if not player_data:
                await interaction.followup.send(
                    f"```[-] Player with ID {battle_id} not found on server {server_name}.```"
                )
                return

            display_name = player_data['attributes']['name']
            # [CHANGED] Use the new server-specific single check for final output
            final_str = battlemettrics.check_player_using_battle_id(server_id, battle_id, display_name)
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

            # Handle multiple matches
            if len(result) == 3 and result[0] is None:
                # 1) dictionary of {battle_id: [username, last_seen], ...}
                multiple_player_data = result[2]

                # 2) Let user pick which player
                target_battle_id = await battlemettrics.handle_multi_players_found(interaction, multiple_player_data)
                if not target_battle_id:
                    # user canceled or timed out
                    return

                # 3) We have a single chosen BM ID. 
                battle_username = multiple_player_data[target_battle_id][0]  # index [1] is last_seen if you need it

                # 4) Optionally show final activity with check_player_using_battle_id
                final_msg = battlemettrics.check_player_using_battle_id(
                    server_id,
                    target_battle_id,
                    battle_username
                )
                await interaction.followup.send(f"```{final_msg}```")
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