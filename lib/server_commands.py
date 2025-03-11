import asyncio # Handle retrieving any timeout based errors
from discord import app_commands # Handles Discord API Communications with Server (Guild in documentation)
from discord.ext import commands # Handle Custom Server Commands
from discord import Interaction
from lib.battlemetrics import ApiClient # Methods to Query BattleMetrics API 
from lib.db import activeServer # Methods to handle group database interactions

# Initialize Battle Metrics API Client (sets BM API Bearer Token)
battlemettrics = ApiClient()
active = activeServer()

# [!] SERVER COMMAND GROUP 
class ServerCommandGroup(app_commands.Group):
    def __init__(self):
        # Inherit app_commands.Group's method to append our own
        # /server Commands
        super().__init__(name="server", description="Rust server configuration commands")

actsrv = ServerCommandGroup()

# [!] /server get
@actsrv.command(name="get", description="Retrieve currently set active server")
async def get(interaction: Interaction):
    server_results = active.get_server()
    if server_results:
        server_id, server_name = server_results # Returns list [server_id,]
        await interaction.response.send_message(f"```[+] Active Server: {server_name} (server id: {server_id})```")
    else:
        await interaction.response.send_message("```[-] No Server Set\nSet Server: /server set <Server Name>```")

# /server set <Server Name>
@actsrv.command(name="set", description="Set's active server")
async def set(interaction: Interaction, server_name: str):
    # [!] Discord ensures that parameter is set
    #if not server_id:
    #    await interaction.response.send_message("[-] You must provide a server ID.")
    #    return
    server_results = await _server_find(interaction, server_name) # Returns list [server_id, server_name]
    if server_results:
        server_id, server_name = server_results
        server_set_notif = active.set_server(server_id, server_name)  # activeServer()'s set_server message returns results of success or failed 
        await interaction.followup.send(server_set_notif)

# /server clear
@actsrv.command(name="clear", description="Clear active server") 
async def clear(interaction: Interaction):
    server_clear_notif = active.clear_server() # activeServer()'s clear_server message returns results of success or failed
    await interaction.response.send_message(server_clear_notif)

# [!] Internal Function to get target server ID and name 
async def _server_find(interaction: Interaction, server_name: str):
    # Calls BM API Method to Return Dictionary with Server Name (key) Server ID (value) pairs
    server_results = battlemettrics.find_server(server_name.strip())
    if not server_results:
        await interaction.response.send_message("[-] No Servers Found")
        return

    # Defer interactiion to prevent timeout errors when getting user choice
    await interaction.response.defer()

    server_names = list(server_results.keys())
    # Get all servers with a # for them to select
    user_server_prompt = "```\n" + "[+] SELECT A SERVER:\n" + "-"*20 + "\n" +  "\n".join([f"[{i+1}]. {name}" for i, name in enumerate(server_names)]) + "```"

    # Print the servers
    srv_listing_msg = await interaction.channel.send(user_server_prompt)

    # Ensure Input Meets Critiera (i.e. from command caller)
    def valid_msg(msg):
        print(f"Received message: {msg.content} from {msg.author}")
        return (
            msg.author == interaction.user
            and msg.channel == interaction.channel
            and msg.content.isdigit()
            and 1 <= int(msg.content) <= len(server_names)
        )

    user_choice = None
    # Get user's choice to set target server from list
    # check=valid_msg,
    try:
        user_choice = await interaction.client.wait_for("message", check=valid_msg, timeout=30)
        selected_server = server_names[int(user_choice.content) - 1]
        return [server_results[selected_server], selected_server] # Returns list [server_id, server_name]
    except asyncio.TimeoutError:
        await interaction.response.send_message("```[-] You didn't reply in time. Please try again.```")
    # Ensure that message printing server details is always deleted
    finally:
        await srv_listing_msg.delete()
        if user_choice:
            # Deltes message if bot timesout
            await user_choice.delete()