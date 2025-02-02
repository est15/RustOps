import requests
import os
from dotenv import load_dotenv

# Class to handle BattleMetrics API Requests & Data Parsing
class ApiClient:
    def __init__(self):
        # Get Bearer Token from environment variable
        load_dotenv()
        self.token = os.getenv('BATTLEMETTRIC_TOKEN')
        if not self.token:
            raise EnvironmentError("[-] BATTLEMETTRIC_TOKEN not found")
        # Authoritzation Header & Content Type
        self.headers={
            "Authorization":f"Bearer {self.token}",
            "Content-Type":"application/json"
            }
    
    # [!] search_type: 0 (Find Server) || 1 (Find Player)
    def send_request(self, search_type:int, server_id:str, trgtPlayer:str=None):
        """Handles Sending HTTP Requests to BattleMetric's API Endpoint"""
        try:     
            base_url = "https://api.battlemetrics.com/servers"
            if search_type == 0: # Find Target Server
                return self._find_server(base_url, server_id)
            elif search_type == 1: # Check if Player is Active
                return self._player_active_check(base_url, server_id, trgtPlayer)
        except Exception as e:
            return f"[-] BM_API_REQ Error: {e}"
    
    # [!] Internal Function only executed by send_request() method
    # Searches for target server
    def _find_server(self, base_url:str, server_id:str):
        """Search for a server using the BattleMetrics API given a name parameter and returns the serverID"""
        base_url += f"?filter[search]={server_id}" # Append inputted server name as search filter
        servers = {} # {"Server Name":"Server ID"} Key/Value pairs
        count = 0 # Server result 
        try: 
            while count < 25: # Handling Parsing through results
                response = requests.get(base_url, headers=self.headers).json()
                for server in response['data']:
                    servers[server['attributes']['name']] = server['attributes']['id']
                    count += 1
                if len(response['data']) < 10:  # No pagination
                    break
                base_url = response['links']['next'] # Pagination next page link
            return servers  
        except Exception as e:
            return f"[-] BM_FND_SRV Error: {e}"
    
    # [!] Internal Function only executed by send_request() method
    # Gets Target Server's active players
    def _player_active_check(self, base_url,  server_id, trgt_player):
        """Searches for players on a server."""
        base_url += f"/{server_id}?include=player" # Append inputted player's user name as a search filter

        # [!] Entire JSON return to program that called method
        # [!] to handle parsing through data there and send messages in discord 
        try:
            response = requests.get(base_url, headers=self.headers).json() # Return All JSON Results 
            players = response.get('included', [])
            for player in players:
                if player['attributes']['name'] == trgt_player:
                    return f"[+] {trgt_player} is **ACTIVE**"
            return f"[-] {trgt_player} **NOT ACTIVE**"
        except Exception as e:
            return f"[-] BM_CHK_PLYR Error: {e}"
        