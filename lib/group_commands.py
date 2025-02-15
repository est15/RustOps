import asyncio # Handle retrieving any timeout based errors
from discord import app_commands # Handles Discord API Communications with Server (Guild in documentation)
from discord.ext import commands # Handle Custom Server Commands
from discord import Interaction
from lib.battlemetrics import ApiClient # Methods to Query BattleMetrics API
from lib.steam import steamClient # Methods to Query Steam Web API
from lib.utils import activeServer # Methods to handle the active server configuration
from lib.db import database # Methods to handle group database interactions
from datetime import datetime 
import unicodedata

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


# [!] PROBLEM: 
#       catches for user added into a group they're already a part of
#       the group if they were added using a different method. Right now
#       if the user was added using battle_id first, then they wont have a SteamID
#       in the database. There are no checks in place currently to handle that edge case. 
#    SOLUTION:
#       At the point where the player's information is checked against the datbase
#       we already have the player's name and group name at minium. Could therefore
#       First filter by those two parameters. Then check how many rows are returned.
#       If more than one do additional filtering. If only one result then check if
#       either steam_id or battle-id columns are empty for that row. If they are update
#       the row with whatever parameter was also passed with the user (i.e. steam_id or 
#       battle_id). 
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
        server_results = await active.get_server()
        if server_results:
            server_id, server_name = server_results.split(":")  # Unused var = server_name
        else:
            await interaction.response.send_message("[-] **no server set**\nset server: `/server set <Server ID>`")
            return

        # Handle input type (Steam URL, BattleMetrics ID, or username)
        # STEAM URL
        if profile.startswith("https://"):
            # Handle URLs
            if "steamcommunity.com" in profile:
                steam_id, username = steam.get_player_info(profile)
                results = battlemettrics.single_player_check(server_id.strip(), server_name, username.strip())
            else:
                await interaction.response.send_message("[-] Invalid URL provided.")
                return
        # BATTLE ID DIRECTLY
        elif profile.isdigit():
            battle_id = profile
            player_data = battlemettrics.get_player_by_id(server_id.strip(), battle_id)
            if player_data:
                username = player_data['attributes']['name']
                results = [battle_id, username, None]
            else:
                await interaction.response.send_message("[-] Player with BattleMetrics ID not found on server.")
                return
        # USERNAME
        else:
            username = profile
            results = battlemettrics.single_player_check(server_id.strip(), server_name, username.strip())

        if not results:
            await interaction.response.send_message("[-] No matching players found.")
            return

        # Display the multiple player matches on the server 
        if results[0] is None:
            await interaction.response.send_message(results[2])
            return

        # Extract player's battle ID and name
        if len(results) == 3:
            battle_id, username, _ = results
        
        # Check if player's name contains a character that cannot be decoded
        if username.startswith("Player_"):
            encoding_issue_notif = f"***\*** Player's name contains a character that could not be decoded. Storing user as {username}*"

        # Ensure the member is not already part of the group
        exist_check = db.check_duplicate_group_member(group_name, steam_id=steam_id, battle_id=battle_id)
        if exist_check:
            await interaction.response.send_message(f"```[+] {exist_check.member} is already a member of the {exist_check.name} group.```{encoding_issue_notif}")
            return

        # Add User to database
        db.add_group_member(group_name=group_name, 
                            group_member=battlemettrics.sanitize_player_name(username), # Ensure username has no unprintable encoding characters in the string 
                            member_steam_id=steam_id or None, 
                            member_battle_id=battle_id or None)

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
        # [!] Get Active Server:
        server_results = await active.get_server()
        if server_results:
            server_id, _ = server_results.split(":")  # Unused Variable == server_name
            
            # Queries steam IDs and usernames (member):
            results = db.check_group_members(group_name)

            # Ensure results returned
            if not results:
                # Method to send messages when using .defer()
                await interaction.followup.send("[-] group doesnt exist")
                
            
            # For each member check if they're on the active server
            # results list of tuple [(membername, steam_id)]
            active_count = 0
            results_list = []
            for member in results:
                active_name = ""
                member_name, member_steam_id, member_battle_id = member

                if member_steam_id:
                    # GET STEAM INFO
                    _, active_name = steam.get_player_info(member_steam_id) # Unused var = steam_id

                    # [!] IMPLEMENT IN FUTURE VER
                    # Update user's member_name attribute if different than whats currently set
                    #if member_name != active_name:
                        # CODE TO UPDATE USER'S DISPLAY NAME IN DATABASE: ----> UPDATE THIS
                        #await interaction.followup.send(f"[-] User {member_name} updated to {active_name}")
                else: 
                    active_name = member_name

                # Call the BattleMetric's API to check if player is active
                result_code, results_message = battlemettrics.group_player_check(server_id.strip(), active_name, member_battle_id) # send_req(<primary search type>, <server id>, <bm player id>, <active player check search type>)
                # code 1 = active
                if result_code == 1:
                    active_count += 1
                    results_list.append(results_message) # Append Active Player Message
                # code 2 = not active, with last seen 
                elif result_code == 2:
                    results_list.append(results_message) # Append last seen message
                # code 0 = unknown status
                else:
                    results_list.append(results_message) # Append Unknown Player status Message
            
            # Add Group's results to group_last_check Table:
            db.update_group_last_checked(group_name, active_count, total_player_count=len(results_list)) # 

            # Print the results
            length_of_seperator = len(group_name) + 20 # Length of "-" to go under title
            user_server_prompt = "```\n" + f"[+] {group_name} ACTIVE PLAYERS: ({active_count} / {len(results_list)})\n" + "-"*length_of_seperator + "\n" +  "\n".join(results_list) + "```" + "*\* only as accurate as the last time the BattleMetric's API was updated*"
            await interaction.followup.send(user_server_prompt)
        else:
            await interaction.followup.send("[-] **no server set**\nset server: `/server set <Server Name>`")
    except Exception as e:
        print(f"[-] grp_check_atv Error: {e}")

# /group remove <group_name> <member_name>
@grpcmds.command(name="remove", description="Remove a player from a group")
async def group_remove(interaction: Interaction, group_name: str, member_name: str):
    try:
        # Trim any spaces from input
        member_name = member_name.strip()

        # Debugging Log 
        print(f"[DEBUG] Removing player: '{member_name}' from group: '{group_name}'")

        # Call the actual remove function
        delete_result = db.rem_group_member(group_name, member_name)

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

# /group change <group name> <new group name>
@grpcmds.command(name="rename", description="Change existing group name")
async def group_rename(interaction: Interaction, current_name: str, new_name: str):
    try:
        # Call the database method to change the group name
        result = db.change_group_name(current_name, new_name)

        # Send response message
        await interaction.response.send_message(f"```{result}```")
    except Exception as e:
        print(f"[-] grp_chng_cmd Error: {e}")
        await interaction.response.send_message("```[-] Error changing group name```")