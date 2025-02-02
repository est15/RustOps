# [!] Handle Server File Operations
import pathlib
from discord import Interaction # Handles Discord API Communications with Server (Guild in documentation)
from discord.ext import commands # Handle Custom Server Commands
import asyncio # Handle retrieving any timeout based errors

class activeServer:
    def __init__(self):
        self.fileName = pathlib.Path(".activeServer")
        try:
            if not self.fileName.exists():
                raise f"[-] Error .activeServer File Not Found"
        except Exception as e:
            print(f"[-] actvSrv Error: {e}")
    
    # [!] GET ACTIVE SERVER
    async def get_server(self):
        server_results = self.fileName.read_text().strip()
        if server_results: # if not empty
            return server_results
        else:
            return None
    
    # [!] SET ACTIVE SERVER
    async def set_server(self, interaction: Interaction, server_name:str, server_id):
        active_server = self.fileName
        active_server_id = ""
        active_server_server = ""
        if not active_server.read_text() == "":
            active_server_id, active_server_server = active_server.read_text().split(":") # Current Active Server (not currently used but you never know)

        active_server.write_text(f"{server_id}:{server_name}")
        await interaction.followup.send(f"[+] Server Set to **{server_name}** (Server ID: {server_id})")

    # [!] CLEAR ACTIVE SERVER
    def clear_server(self):
        active_server = self.fileName.read_text()
        if active_server: # if not empty
            # [!] Not prompting or confirmation on clearing           
            # Clear active server
            self.fileName.write_text("") 
            return f"[+] Active server cleared"
        else:
            return f"[-] no server set:\nSet Server with: `/server set <Server ID>`"
        


