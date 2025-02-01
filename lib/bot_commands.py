import asyncio # Handle retrieving any timeout based errors
import discord # Handles Discord API Communications with Server (Guild in documentation)
from discord.ext import commands # Handle Custom Server Commands
from lib.battlemetrics import ApiClient # Methods to Query BattleMetrics API

# Initialize Battle Metrics API Client (sets BM API Bearer Token)
api_client = ApiClient()

# Server find bot command
@commands.command(
        name="find",
        help="/find <server name>\nFind a server's server ID value",
        usage="/find <server name>"
            )
async def server_find(ctx, server_name: str = ""):
    if not server_name:
        await ctx.send_help(ctx.command)
        return

    # Calls BM API Method to Return Dictionary with Server Name (key) Server ID (value) pairs
    server_results = api_client.send_request(0, server_name.strip())
    if not server_results:
        await ctx.send("[-] No Servers Found")
        return


    server_names = list(server_results.keys())
    # Get all servers with a # for them to select
    user_server_prompt = "**[*] SELECT A SERVER**:\n" + "\n".join(
        [f"[{i+1}]. {name}" for i, name in enumerate(server_names)]
    )

    # Print the servers
    srv_listing_msg = await ctx.send(user_server_prompt)

    # Ensure Input Meets Critiera (i.e. from command caller)
    def valid_msg(msg):
        return (
            msg.author == ctx.author
            and msg.channel == ctx.channel
            and msg.content.isdigit()
            and 1 <= int(msg.content) <= len(server_names)
        )

    # Get user's choice to set target server from list
    try:
        user_choice = await ctx.bot.wait_for("message", check=valid_msg, timeout=30)
        selected_server = server_names[int(user_choice.content) - 1]
        await ctx.send(f"[+] {selected_server} (Server ID: **{server_results[selected_server]}**)")
    except asyncio.TimeoutError:
        await ctx.send("[-] You didn't reply in time. Please try again.")
    # Ensure that message printing server details is always deleted
    finally:
        await srv_listing_msg.delete()
        await user_choice.delete()

# Player find bot command
@commands.command(
        name="check",
        help="/check <server ID> <player name>\nCheck if player is active on a given server.\nIf username contains a space wrap the username in quotes.",
        usage="/check <server ID> <player name>"
            )
async def player_find(ctx, server_id:str = "", player:str = ""):
    if not server_id or not player:
        await ctx.send_help(ctx.command)
        return

    # Call the BattleMetric's API to check if player is active
    result = api_client.send_request(1, server_id.strip(), player.strip())
    await ctx.send(result)
