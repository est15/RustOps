import asyncio # Handle retrieving any timeout based errors
from discord import app_commands # Handles Discord API Communications with Server (Guild in documentation)
from discord.ext import commands # Handle Custom Server Commands
from discord import Interaction
from lib.battlemetrics import ApiClient # Methods to Query BattleMetrics API
from lib.steam import steamClient # Methods to Query Steam Web API
from lib.db import activeServer # Methods to handle the active server configuration
from lib.db import database # Methods to handle group database interactions
from datetime import datetime 
import re

# Initialize Battle Metrics API Client (sets BM API Bearer Token)
battlemettrics = ApiClient()
steam = steamClient()
active = activeServer()

# Initializee database's Methods
db = database()

# [!] SERVER COMMAND GROUP 
class ServerCommandGroup(app_commands.Group):
    def __init__(self):
        # Inherit app_commands.Group's method to append our own
        # /server Commands
        super().__init__(name="group", description="Rust group configuration commands")

grpcmds = ServerCommandGroup()

# [!] Internal Function
# Used in /groups list to convert the stored last_checked_date with the currentimestamp 
# then print it out into a readable format
def _format_time_difference(last_checked_date: str) -> str:
    """Formats the time difference between the current time and the last checked time."""
    try:
        # Convert last_checked string to datetime object
        last_checked_dt = datetime.strptime(last_checked_date, '%Y-%m-%d %H:%M:%S')

        # Get the current timestamp and calculate the difference
        time_diff = datetime.now() - last_checked_dt

        # Format based on the time difference
        if time_diff.days >= 1:
            return f"{time_diff.days}d ago"
        elif time_diff.seconds >= 3600:  # 1 hour = 3600 seconds
            hours, remainder = divmod(time_diff.seconds, 3600)
            minutes = remainder // 60
            return f"{hours}h {minutes}m ago"
        else:
            minutes = time_diff.seconds // 60
            return f"{minutes}m ago"
    except Exception as e:
        print(f"[-] Error formatting time difference: {e}")
        return "Unknown"

# [!] /group list
@grpcmds.command(name="list", description="List current groups defined")
async def list(interaction: Interaction):
    # Stored as list
    group_names = db.get_all_groups()
    if not group_names:
        await interaction.response.send_message("[-] No groups have been created")
    # Fetch last checked data for each group and build output
    group_lines = []
    for num, group_name in enumerate(group_names):
        # Get last checked information
        last_check = db.get_group_last_checked(group_name)

        # Comapre times
        if last_check:
            active_count = last_check.active_count
            total_count = last_check.total_count
            last_checked = last_check.date or "Never"
            time_since_checked = _format_time_difference(last_checked) if last_checked != "Never" else "Never"
        else:
            active_count, total_count, time_since_checked = "0", "0", "Never"

        # Format the output line for this group
        group_line = f"{num+1}. {group_name} ({active_count}/{total_count}) : {time_since_checked}"
        group_lines.append(group_line)

    # Send the message to Discord
    all_groups_message = "```\n" + "[+] GROUPS:\n" + "-" * 11 + "\n" + "\n".join(group_lines) + "```"
    await interaction.response.send_message(all_groups_message)

# /group add <group name> <player steam id, battle id, or username>
@grpcmds.command(name="add", description="Add player to group")
async def group_add(interaction: Interaction, group_name: str, profile: str):
    try:
        # Default empty variables
        battle_id = ""  # can be empty
        steam_id = ""  # can be empty
        results = None  # Ensure results has a default value
        encoding_issue_notif = "" # if encoding issue in player's display name

        # Get Active server
        server_results = active.get_server() # Returns list [server_id, server_name]
        if server_results:
            server_id, server_name = server_results
        else:
            await interaction.response.send_message("```[-] No Server Set\nSet Server: /server set <Server Name>```")
            return

        # [STEP 1] Determine Input Type (Steam Profile, BattleMetrics ID, or Username)
        # Steam Profile URL
        if 'https://steamcommunity.com/' in profile:
            steam_id, found_name = steam.get_player_info(profile)
            username = found_name
            
            # Check to see if multiple players match the user's username
            results = battlemettrics.single_player_check(server_id.strip(), server_name, username.strip())

        # BattleMetrics Player URL
        # e.g. https://www.battlemetrics.com/players/1106206685
        elif 'https://www.battlemetrics.com/players/' in profile:
            # Extract BattleMetrics Player ID
            battle_id_regex = re.search(r"(\d{5,11})", profile)  # [UPDATED] Fixed regex for extracting IDs

            # If ID was grabbed:
            if battle_id_regex:
                battle_id = battle_id_regex.group(1)  # [UPDATED] Extract only the ID portion

                # Check if valid Battle ID:
                player_data = battlemettrics.get_player_by_id(battle_id=battle_id)
                
                # If HTTP STATUS code against BM API != 200; then invalid BM Player ID
                if not player_data:
                    await interaction.response.send_message("```[-] Error: Invalid Battlemetrics Player ID```")
                    return
                else:
                    # Valid BM Player get their current name as its stored on Battlemetrics
                    username = player_data['attributes']['name']
                    results = [battle_id, username, None]
            else:
                await interaction.response.send_message("```[-] Error: Could Not Extract Battlemetrics ID```")
                return

        # [!] If an ID is passed directly, determine if it's a Steam ID or BattleMetrics ID
        elif profile.isdigit():
            id_type_check = steam.is_valid_steam_id(profile)

            # Valid Steam ID
            if id_type_check:
                steam_id, found_name = steam.get_player_info(profile)
                username = found_name

                # Check if multiple players match that username
                results = battlemettrics.single_player_check(server_id.strip(),
                                                             server_name,
                                                             username.strip())
    
            # Else BattleMetrics ID
            else:
                battle_id = profile

                # Check if valid Battle ID:
                player_data = battlemettrics.get_player_by_id(battle_id=battle_id)
                
                # If HTTP STATUS code against BM API != 200; then invalid BM Player ID
                if not player_data:
                    await interaction.response.send_message("```[-] Error: Invalid Battlemetrics Player ID```")  
                    return
                else:
                    # Valid BM Player get their current name as its stored on Battlemetrics
                    username = player_data['attributes']['name']
                    results = [battle_id, username, None]

        # If none of the above, then it must be a username
        else:
            username = profile
            # Check if multiple players match that username
            results = battlemettrics.single_player_check(server_id.strip(),
                                                            server_name,
                                                            username.strip())

        if not results:
            await interaction.response.send_message("```[-] No matching players found.```")
            return

        # Display the multiple player matches on the server 
        if len(results) == 3 and results[0] is None:
            # results[2] = dictionary of {"battle_id":[username, last_seen], ...}
            multiple_player_data = results[2] 
            
            # Returns battle_id for target player
            target_battle_id = await battlemettrics.handle_multi_players_found(interaction, multiple_player_data)

            # Something went wrong
            if not target_battle_id:
                return

            battle_id = target_battle_id
            username = multiple_player_data[target_battle_id][0] 

        # Extract player's battle ID and name
        if len(results) == 3:
            battle_id, username, _ = results
        
        if username.startswith("Player_"):
            encoding_issue_notif = f"***\*** Player's name contains a character that could not be decoded. Storing user as {username}*"

        # Ensure the member is not already part of the group
        exist_check = db.check_duplicate_group_member(group_name, steam_id=steam_id, battle_id=battle_id)
        if exist_check:
            await interaction.response.send_message(f"```[+] {exist_check.member} is already a member of the {exist_check.name} group.```{encoding_issue_notif}")
            return

        # Add User to database
        db.add_group_member(group_name=group_name, 
                            group_member=username,
                            member_steam_id=steam_id or None, 
                            member_battle_id=battle_id)

        # Print Success:
        await interaction.response.send_message(f"```[+] {username} successfully added to {group_name}```{encoding_issue_notif}")
    except Exception as e:
        print(f"[-] grp_add_mem Error: {e}")


# /group check <group name>
@grpcmds.command(name="check", description="Checks player status for all group members")
async def group_check(interaction: Interaction, group_name: str):
    try:
        # Tell discord to wait for the command to process
        await interaction.response.defer()
        # GET ACTIVE SERVER ID
        server_results = active.get_server() # Returns list [server_id, server_name]
        if server_results:
            server_id, server_name = server_results
            
            # Queries steam IDs and usernames (member):
            results = db.check_group_members(group_name.lower())

            # Ensure results returned
            if not results:
                # Method to send messages when using .defer()
                await interaction.followup.send("```[-] group doesnt exist```")
                return 
                
            
            # For each member check if they're on the active server
            # results contains list of tuple [(membername, steam_id, battle_id), ...]
            active_count = 0
            results_list = [] # Stores activity status for each group member checked
            for member in results:
                active_name = ""
                member_name, member_steam_id, member_battle_id = member  # Unused var == member_name

                # If the member has a battle ID stored use that to check the activity status
                if member_battle_id:
                    activity_status_message = battlemettrics.check_player_using_battle_id(
                        server_id=server_id.strip(),
                        bm_player_id=member_battle_id,
                        fallback_name=active_name
                    )

                    # Add to active count if player is active
                    if "ACTIVE" in activity_status_message:
                        active_count += 1
                    
                    # Append the result otherwise (last seen time)
                    results_list.append(activity_status_message)
                        
                # If Steam ID attempt to identify target player (this should honestly never run if battlemetrics.py does its job in /group add)
                else: 
                    # [UPDATE] make sure to update this later so handle dynamically selecting the target player if multiply players found matching the username
                    if member_steam_id:
                        # GET STEAM INFO
                        _, active_name = steam.get_player_info(member_steam_id) # Unused var is steam_id
                    else: 
                        active_name = member_name

                    single_result = battlemettrics.single_player_check(
                        server_id=server_id.strip(),
                        server_name=server_name,
                        trgt_player=active_name.strip()
                    )
            
            # Add Group's results to group_last_check Table:
            db.update_group_last_checked(group_name, active_count, total_player_count=len(results_list)) # 

            # Print the results
            length_of_seperator = len(group_name) + 20 # Length of "-" to go under title, 20 == len of non-variable string (i.e.[+] {group_name} ACTIVE PLAYERS:)
            user_server_prompt = "```\n" + f"[+] {group_name} ACTIVE PLAYERS: ({active_count} / {len(results_list)})\n" + "-"*length_of_seperator + "\n" +  "\n".join(results_list) + "```" + "*\* only as accurate as the last time the BattleMetric's API was updated*"
            await interaction.followup.send(user_server_prompt)
        else:
            await interaction.response.send_message("```[-] No Server Set\nSet Server: /server set <Server Name>```")
            return
    except Exception as e:
        print(f"[-] grp_check_atv Error: {e}")

# /group remove <group_name> <member_name>
@grpcmds.command(name="remove", description="Remove a player from a group")
async def group_remove(interaction: Interaction, group_name: str, member_name: str):
    try:
        # Trim any spaces from input
        member_name = member_name.strip()

        # Debugging Log (REMOVE AFTER TESTING)
        print(f"[DEBUG] Removing player: '{member_name}' from group: '{group_name}'")

        # Call the actual remove function
        delete_result = db.rem_group_member(group_name.lower(), member_name)

        # Check if deletion was successful
        if delete_result is False:
            await interaction.response.send_message(f"```[+] {member_name} successfully removed from {group_name}```")
        else:
            await interaction.response.send_message(delete_result)  # Sends error message if user not found

    except Exception as e:
        print(f"[-] grp_rem_cmd Error: {e}")
        await interaction.response.send_message("```[-] Error removing member```")

# /group del <group name>
@grpcmds.command(name="del", description="Deletes entire group (non-recoverable)")
async def group_del(interaction: Interaction, group_name: str):
    # Ensure passing interaction object to prompt for confirmation
    try:
        # Call the database method to delete the group
        result = db.delete_group(group_name)

        # Send the result message to the user
        await interaction.response.send_message(result)
    except Exception as e:
        print(f"[-] group_del Error: {e}")
        await interaction.response.send_message(f"```[-] Error deleting group '{group_name}'.```")

# /group rename <group name> <new group name>
@grpcmds.command(name="rename", description="Change existing group name")
async def group_rename(interaction: Interaction, current_name: str, new_name: str):
    try:
        # Call the database method to change the group name
        result = db.change_group_name(current_name.lower(), new_name.lower())

        # Send response message
        await interaction.response.send_message(result)
    except Exception as e:
        print(f"[-] grp_chng_cmd Error: {e}")
        await interaction.response.send_message("```[-] Error changing group name```")