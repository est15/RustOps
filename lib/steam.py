# Handles Querying Steam Web API
import requests                 # Handle HTTP Requests to Steam Web API
import os                       # Handle Environment Variable querying for script secrets
from dotenv import load_dotenv  # Handle Environment Variable querying for script secrets
import re # Extract IDs from Stean URLs

class steamClient:
    def __init__(self):
        # Get secrets from environment  variables
        load_dotenv()       
        self.steam_key = os.getenv('STEAM_KEY')
        if not self.steam_key:
            raise EnvironmentError("[-] STEAM_KEY not found")

        # Content Type Header
        self.headers={"Content-Type":"application/json"}
    
    # [Verify if id is valid steam id]
    def is_valid_steam_id(self, profile_id):
        """Checks if a given Steam ID is a valid Steam profile."""
        try:
            # Query Steam API to check if the ID is associated with a real Steam account
            response = requests.get(
                f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={self.steam_key}&steamids={profile_id}",
                headers=self.headers
            )
            data = response.json()

            # Check if the response contains player data
            if "response" in data and "players" in data["response"] and data["response"]["players"]:
                return True  # valid steam player id
            return False # not valid steam player id

        except Exception as e:
            print(f"[-] stm_valid_id Error: {e}")
            return False
    
    def _valid_steam_url(self, profile_url):
        """Ensure valid steam profile URL"""
        return bool(re.match(r"^(?:https?://)?steamcommunity\.com/(?:profiles/|id/)", profile_url))

    # [!] Internal Method
    # Resolves Steam vanity URLs into their respective Steam IDs
    def _resolve_vanity(self, vanityname):
        try:
            # Convery Vanity URL to SteamID
            request = requests.get(f"http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={self.steam_key}&vanityurl={vanityname}", headers=self.headers)
            return request.json()
        except Exception as e:
            print(f"[-] stm_url_vnty Error: {e}")
    
    # [!] Internal Method
    # Queries Steam Web API
    def _send_request(self, profileName):
        try:
            # Handle Vanity URLs: https://stackoverflow.com/questions/62138380/how-to-resolve-a-steam-custom-vanity-profile-url-to-steamid64
            # b/c we need the 64-bit steamID to query a user's information
            request = requests.get(f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={self.steam_key}&steamids={profileName}", headers=self.headers)
            return request.json()
        except Exception as e:
            print(f"[-] stm_api_req ERROR: {e}")

    # [!] Get steamid and personaname attributes for player
    # [!] Working with https://steamcommunity.com/profiles/76561198067942001 as example
    def get_player_info(self, profileURL):
        """Returns Steam Profile's 64-bit steam ID and persona name (display name)."""
        # [1] Extract the username
        #       Steam profile URLs use the following format(s):
        #       https://steamcommunity.com/(profiles or id)/(either display name set or set of numbers)
        #       [!] REGEX FROM: https://stackoverflow.com/questions/37016532/check-if-valid-steam-profile-url --> Used chatgpt to modify to execute
        try:
            results = []
            steam_id = ""


            # Handle Steam Profile urls (from user input)
            if self._valid_steam_url(profileURL):
                profile_url_id = re.match(r"^(?:https?://)?steamcommunity\.com/(?:profiles/|id/)([0-9]{17}|[a-zA-Z0-9]+)/*$", profileURL)

                # Handle Vanity URLs: https://stackoverflow.com/questions/62138380/how-to-resolve-a-steam-custom-vanity-profile-url-to-steamid64
                # b/c we need the 64-bit steamID to query a user's information
                if "id" in profile_url_id.group(0):
                    # Get profile's displayname and steamID (used for tracking purposes in the future)
                    vanity_response = self._resolve_vanity(profile_url_id.group(1))
                    steam_id = vanity_response['response']['steamid']
                else:
                    # Get profile's displayname and steamID (used for tracking purposes in the future)
                    steam_id = profile_url_id.group(1)
            # Handle Direct Steam IDs (from database)
            elif self.is_valid_steam_id(profileURL):
                steam_id = profileURL
            else:
                print("[-] Error in lib/steam.py get_player_info")
                raise ValueError("[-] Something went wrong processing the steam ID.")

            
            # With steam ID gathered, now query Steam Web API
            response = self._send_request(steam_id)
            
            # Handle no data returned
            players_list = response.get('response', {}).get('players', [])
            if not players_list:
                raise ValueError("[-] No player data found for given Steam ID.")

            player_data = players_list[0]
            
            # Store the results in a list
            results.append(player_data['steamid'])
            results.append(player_data['personaname'])
            
            # Return list of (steamID, username) values 
            return results
        except Exception as e:
            print(f"[-] stm_url_extrct ERROR: {e}")
    
    
