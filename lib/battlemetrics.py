import requests  # Handle Web Requests
import os  # Handle loading environment variables
from dotenv import load_dotenv  # Handle loading environment variables
from datetime import datetime, timezone  # Handle date time formats
import pytz  # Handles timezone conversions
import re
import asyncio # Handle retrieving any timeout based errors

# Class to handle BattleMetrics API Requests & Data Parsing
class ApiClient:
    def __init__(self):
        # Get Bearer Token from environment variable
        load_dotenv()
        self.token = os.getenv('BATTLEMETTRIC_TOKEN')
        self.base_url = "https://api.battlemetrics.com/"
        if not self.token:
            raise EnvironmentError("[-] BATTLEMETRIC_TOKEN not found")
        # Authorization Header & Content Type
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    # [!] Internal Function
    # Handles converting BattleMetrics date/time format into a human-readable format
    @staticmethod
    def _format_datetime(last_seen_time):
        """Format the time difference between now and the last seen time."""
        last_seen = datetime.strptime(last_seen_time, '%Y-%m-%dT%H:%M:%S.%fZ')

        # Convert to EST timezone for consistency
        est_tz = pytz.timezone("America/New_York")
        last_seen = last_seen.replace(tzinfo=timezone.utc).astimezone(est_tz)

        # Get the current time in EST and calculate the difference
        now = datetime.now(tz=est_tz)
        time_diff = now - last_seen

        if time_diff.days >= 365:
            years = time_diff.days // 365
            return f"{years}yr{'s' if years > 1 else ''} ago"
        elif time_diff.days >= 30:
            months = time_diff.days // 30
            return f"{months}mth{'s' if months > 1 else ''} ago"
        elif time_diff.days >= 7:
            weeks = time_diff.days // 7
            return f"{weeks}wk{'s' if weeks > 1 else ''} ago"
        elif time_diff.days >= 1:
            return f"{time_diff.days}d ago"
        else:
            total_seconds = time_diff.total_seconds()
            hours, remainder = divmod(total_seconds, 3600)
            minutes = remainder // 60
            if hours >= 1:
                return f"{int(hours)}h {int(minutes)}m ago"
            else:
                return f"{int(minutes)}m ago"

    # Searches for target server
    def find_server(self, server_id: str):
        """Search for a server using the BattleMetrics API given a name parameter and returns the serverID"""
        updated_url = self.base_url + f"/servers?filter[search]={server_id}"
        servers = {}  # {"Server Name":"Server ID"} Key/Value pairs
        count = 0  # Server result 
        try:
            while count < 25:  # Handling Parsing through results
                response = requests.get(updated_url, headers=self.headers)
                response_json = response.json()  # Convert to JSON
                for server in response_json['data']:
                    servers[server['attributes']['name']] = server['attributes']['id']
                    count += 1
                if len(response_json['data']) < 10:  # No pagination
                    break
                updated_url = response_json['links']['next']  # Pagination next page link
            return servers
        except Exception as e:
            return f"```[-] BM_FND_SRV Error: {e}```"


    # [!] Handles Identifying players based on username (either directly or steam ID)
    #      - if multiple found then prints them out with their battle IDs and last 
    #       time seen on the active server.
    def single_player_check(self, server_id, server_name, trgt_player, sort="-lastSeen"):
        search_url = self.base_url + "/players"
        search_value = f"\"{trgt_player}\""
        search_params = {
            "filter[search]": search_value,
            "filter[servers]": server_id,
            "sort": sort
        }
        search_response = requests.get(search_url, headers=self.headers, params=search_params)
        players = search_response.json().get('data', [])

        if not players:
            return [f"```[ ] {trgt_player} : not found on server {server_name}```"]

        recent_players = [
            p for p in players
            if ("mth" not in self._format_datetime(p['attributes']['updatedAt']))
            and ("yr" not in self._format_datetime(p['attributes']['updatedAt']))
        ]

        # If multiple players found matching name iterate through them, store their battle id and username. 
        # Additionally gathers the player's session data 
        if len(recent_players) > 1:
            results_dict = {}
            for i, player in enumerate(recent_players[:10], start=1):
                # [ADDED] For each matched player, do a separate /sessions call
                battle_id = player['id']
                battle_username = self.sanitize_player_name(player['attributes']['name'])
                last_seen = ""

                # Check if currently active or last time active on server 
                session_url = f"{self.base_url}/sessions"
                session_params = {
                    "filter[players]": battle_id,
                    "filter[servers]": server_id
                }
                resp = requests.get(session_url, headers=self.headers, params=session_params)
                if resp.status_code != 200:
                    last_seen = "FAILED TO GET SESSION"
                    continue

                session_data = resp.json().get('data', [])
                if not session_data:
                    # No session data => never joined or BM doesn't have record
                    last_seen = "no session data available"
                    continue

                latest_session = session_data[0]
                stop_time = latest_session['attributes'].get('stop')
                if stop_time is None:
                    # Active
                    last_seen = "ACTIVE"
                else:
                    # Last seen => format
                    last_seen_time_formatted = self._format_datetime(stop_time)
                    last_seen = last_seen_time_formatted

                # Add Player's battle_id, battle_username, and last_seen values to dictionary
                results_dict[battle_id] = [battle_username, last_seen]
            
            # Return list [None, None, dictionary_of_player_data]
            return [
                None, 
                None, 
                results_dict
            ]
        
        # If only one "recent" match, return the final active/last-seen message
        return self._get_player_status(server_id, recent_players[0])
    
     # [!] Internal Method to Handle Selecting Correct Player if Multiple Players Found Matching username
    async def handle_multi_players_found(self, interaction, recent_players):
        if not recent_players:
            await interaction.followup.send("```[-] Multiple playes check ran but was passed empty list.```")
            return None

        # 1) Build the listing of players
        listing_lines = []
        for i, (battle_id, [battle_username, last_seen]) in enumerate(recent_players.items(), start=1):
            listing_lines.append(f"[{i}]. {battle_username} (battle id: {battle_id}) : {last_seen}")

        user_player_prompt = (
            "```[+] SELECT A PLAYER:\n"
            + "-"*20
            + "\n"
            + "\n".join(listing_lines)
            + "\n[0]. None of Them"
            + "```"
        )

        # 2) Send the listing message
        prompt_message = await interaction.followup.send(user_player_prompt)

        # 3) Define a check function that ensures correct user input
        def valid_msg(msg):
            return (
                msg.author == interaction.user
                and msg.channel == interaction.channel
                and msg.content.isdigit()
                and 1 <= int(msg.content) <= len(recent_players) or int(msg.content) == 0
            )

        user_choice_msg = None
        chosen_player = None

        try:
            # 4) Wait 30s for a valid digit
            user_choice_msg = await interaction.client.wait_for(
                "message",
                check=valid_msg,
                timeout=30
            )
            # If valid, pick the correct player
            choice_index = int(user_choice_msg.content)

            # Store all battle_ids in a list
            dict_keys = list(recent_players.keys())
            
            # If user selected 0 then delete the messages & dont perform anything
            if choice_index == 0:
                await interaction.followup.send("```[-] Target player not in list.```")
                chosen_player = None
            else:
                # otherwise pick the correct player from the list (1..N)
                chosen_player = dict_keys[choice_index - 1]
        except asyncio.TimeoutError:
            await interaction.followup.send("```[-] You didn't reply in time. Please try again.```")
        finally:
            # Cleanup: attempt to delete both the listing & the user’s choice
            try:
                await prompt_message.delete()
            except:
                pass
            if user_choice_msg:
                try:
                    await user_choice_msg.delete()
                except:
                    pass

        # Returns battle_id for target player; treated as unique identifier for calling method
        return chosen_player
    
    # [!] Handles identifying activity status for a player when a battlemetrics ID is passeed as input
    def check_player_using_battle_id(self, server_id: str, bm_player_id: str, fallback_name: str) -> str:
        try:
            if not bm_player_id:
                return f"[ ] {fallback_name} : BattleMetrics ID for user not found but executed check_player_using_battle_id." # This should not execute, fallback error
 
            session_url = f"{self.base_url}/sessions"
            session_params = {
                "filter[players]": bm_player_id,
                "filter[servers]": server_id
            }
            resp = requests.get(session_url, headers=self.headers, params=session_params)
            if resp.status_code != 200:
                return f"[-] BM_CHK_SGL Error: Sessions request failed (HTTP {resp.status_code})."

            data = resp.json().get('data', [])
            if not data:
                return f"[ ] {fallback_name} : no session data available"

            latest_sess = data[0]
            stop_time = latest_sess['attributes'].get('stop')
            if stop_time is None:
                return f"[X] {fallback_name} : ACTIVE"
            else:
                last_seen_str = self._format_datetime(stop_time)
                return f"[ ] {fallback_name} : last seen {last_seen_str}"

        except Exception as e:
            return f"[-] check_player_using_battle_id Error: {e}"


    # Handle names that contain unprintable characters in the bytes
    # that make up the encoded string (Ex: '\u1cbc')
    #
    # This will make the character unprintable, and we'll use an alais 
    # for the user in the format: "\u1cbc"	would become "Player_1cbc"
    def sanitize_player_name(self, username):
        """Ensure name is printable and not an unkown / unprintable string"""
        
        # Check if playername is already sanitized:
        # looking for base-16 characters since itll be a string version of raw bytes
        if re.fullmatch(r"Player_[0-9a-fA-F]+", username):
            return username

        # Ensure each character is printable
        if all(x.isprintable() for x in username):
            return username

        # Convert the name into the alias format:
        user_bytes = "".join(f"{ord(c):04x}" for c in username)
        return f"Player_{user_bytes}"
    
    # [!] Queries Sessions based on BattleMetrics Player ID
    def get_player_by_id(self, battle_id):
        """Query the BattleMetrics API to get player details by ID."""
        player_url = f"{self.base_url}/players/{battle_id}"
        response = requests.get(player_url, headers=self.headers)
        if response.status_code == 200:
            player_data = response.json().get('data', {})

            # Ensure no unprintable encodiing characters in string
            player_data['attributes']['name'] = self.sanitize_player_name(player_data['attributes']['name'])
            return player_data
        else:
            return None
    

# [!] Executed when checking player status
    def _get_player_status(self, server_id, player_data):
        """
        Server-specific status check for one user (called by single_player_check if exactly one match).
        Replaces usage of 'updatedAt' with sessions for accurate 'ACTIVE' or 'last seen X'.
        """
        player_id = player_data['id']
        player_name = self.sanitize_player_name(player_data['attributes']['name'])

        sessions_url = f"{self.base_url}/sessions"
        sessions_params = {
            "filter[players]": player_id,
            "filter[servers]": server_id,
            # "sort": "-start"
        }

        sessions_response = requests.get(sessions_url, headers=self.headers, params=sessions_params)
        if sessions_response.status_code != 200:
            return [player_id, player_name, f"```[-] Unable to get session data (HTTP {sessions_response.status_code}).```"]

        session_data = sessions_response.json().get('data', [])
        if not session_data:
            return [player_id, player_name, f"```[ ] {player_name} : no session data available```"]

        latest_session = session_data[0]
        stop_time = latest_session['attributes'].get('stop')

        if stop_time is None:
            return [player_id, player_name, f"```[X] {player_name} : ACTIVE```"]
        else:
            formatted_last_seen = self._format_datetime(stop_time)
            return [player_id, player_name, f"```[ ] {player_name} : last seen {formatted_last_seen}```"]