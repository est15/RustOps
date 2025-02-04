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

# [!] SERVER COMMAND GROUP 
class ServerCommandGroup(app_commands.Group):
    def __init__(self):
        # Inherit app_commands.Group's method to append our own
        # /server Commands
        super().__init__(name="groups", description="Rust group configuration commands")

grpcmds = ServerCommandGroup()

# [!] /group list
@grpcmds.command(name="list", description="List current groups defined")
async def list(interaction: Interaction):
    # Stored as list
    results = db.get_all_groups()
    if not results:
        await interaction.response.send_message("[-] No groups have been created")
    else:
        all_groups_message = "```\n" + "[+] GROUPS:\n" + "-"*11 + "\n" +  '\n'.join([f'{num+1}. {group_name}' for num, group_name in enumerate(results)]) + "```"
        await interaction.response.send_message(all_groups_message)
    pass

# /group add <group name> <steam url>
@grpcmds.command(name="add", description="Add player to group")
async def group_add(interaction: Interaction, group_name: str, steam_url: str):
    try:
        # Expected params: add_group_member(self, group_name, group_member, member_steam_id, *args) --> args[0] = battlemetrics player ID (not sure how to grab this yet)
        # GET STEAM INFO
        steam_id, steam_username = steam.get_player_info(steam_url)
        
        # Ensure Member is not already part of group:
        exist_check = db.get_member_group(steam_id)
        if exist_check:
            await interaction.response.send_message(f"[+] **{exist_check.member}** (Steam ID: {exist_check.steam_id}) is already a member of **{exist_check.name}** group.")
            return

        # Add User to database
        db.add_group_member(group_name=group_name, group_member=steam_username, member_steam_id=steam_id)

        # Print Success:
        await interaction.response.send_message(f"[+] **{steam_username}** successfully added to **{group_name}**")

    except Exception as e:
        print(f"[-] grp_add_mem Error: {e}")

# /group remove <groupname> <member name>
@grpcmds.command(name="remove", description="Remove player from group")
async def group_remove(interaction: Interaction, group_name: str, member_name: str):
# [!] THOUGHTS ON METHODS FOR REMOVING USER
# not sure whats best method for removing from group (i.e. use display name or steam id)
# Steam ID would be preferable as its unique and people can have the same display name 
# Ill have to check the database's display name against that from the steam web api (that will handle the user changing their display name or url on steam)  
#
# [!] FLOW:
#      1. Query name (group_name) and member (member_name)
# In writing this flow I realized that I was thinking about it all wrong. There is no problem handling user's changing their display name in this.
# 
# Although using the display name does bring about the potential for duplicate names, in which case it'll remove the first occurence 
# of the firt user in the group that matches member_name 
#       ----> going to implement in future
#       ----> need some way to get all members in the group that share
#             diisplay names, then return their steam profile urls
#             and prompt user for which one (might have to increase timeout on this one and set ephmeral=True when calling send_message()) 
#             [^] ephemeral = True only shows the message to the command caller (or so I believe)  
###########################################################################################################################################
    results = db.rem_group_member(group_name, member_name)
    
    # Reference db.py's rem_group_member() method
    # for better explanation of this logic.
    # This means it was was successfully
    if not results:
        await interaction.response.send_message(f"[+] ╔═ {member_name} REMOVED FROM {group_name} ═╗")
    else:
        await interaction.response.send_message(results)

# /group check <group name>
@grpcmds.command(name="check", description="Checks player status for all group members")
async def group_check(interaction: Interaction, group_name: str):
# [!] check command Flow:
#       1. Get all steam ID columns where name is the passed group_name
#       2. Send these results which should be a list of tuples [('stemid', 'member name')]
#       3. Send the steam ID through steam web API to get user's currently set display name (which is going to be whats tracked in battlemetrics)
#       4. Get currently active server's Server ID
#       5. Send the user's current display name through BattleMetric's API to check for current users
#       6. Displays:
#          [+] {group_name} ACTIVE PLAYERS (2/10):
#          -------------------------------- 
#          1. user_name IS ACTIVE
#          2. user_2 IS NOT ACTIVE
#          ..<SNIP>..
    try:
        # GET ACTIVE SERVER ID
        # [!] Get Active Server:
        server_results = await active.get_server()
        if server_results:
            server_id, _ = server_results.split(":")  # Unused Variable == server_name
            
            # Queries steam IDs and usernames (member):
            results = db.check_group_members(group_name)

            # Ensure results returned
            if not results:
                await interaction.response.send_message("[-] group doesnt exist")
                
            
            # For each member check if they're on the active server
            # results list of tuple [(membername, steam_id)]
            active_count = 0
            results_list = []
            for member in results:
                _, member_steam_id = member  # Unused var == member_name
                # GET STEAM INFO
                _, steam_username = steam.get_player_info(member_steam_id) # Unused va steam ID
                
                # Call the BattleMetric's API to check if player is active
                result_msg, result = battlemettrics.send_request(1, server_id.strip(), steam_username.strip())
                # Playuer is Active
                if result == 1:
                    active_count += 1
                    results_list.append(result_msg)
                # Player NOT Active
                elif result == 0:
                    results_list.append(result_msg)
            
            user_server_prompt = "```\n" + f"[+] {group_name} ACTIVE PLAYERS: ({active_count} / {len(results_list)})\n" + "-"*32 + "\n" +  "\n".join(results_list) + "```"
            await interaction.response.send_message(user_server_prompt)
        else:
            await interaction.response.send_message("[-] **no server set**\nset server: `/server set <Server Name>`")
    except Exception as e:
        print(f"[-] grp_check_atv Error: {e}")

# /group del <group name>
@grpcmds.command(name="del", description="Deletes entire group (non-recoverable)")
async def group_del(interaction: Interaction, group_name: str):
    # Ensure passing interaction object to prompt for confirmation
    pass

# /group change <group name> <new group name>
@grpcmds.command(name="change", description="Change existing group name")
async def group_change(interaction: Interaction, group_name: str):
    pass