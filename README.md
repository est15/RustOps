# RustOps
RustOps is a Discord bot that tracks player activity on Rust servers, organizing them into groups and monitoring who is currently online and when offline members were last active. 

### Bot Demo:
[![Watch the video](https://img.youtube.com/vi/NeKdC2AVGo0/maxresdefault.jpg)](https://www.youtube.com/watch?v=NeKdC2AVGo0)

### Requirements:
1. Discord Bot
2. Steam Web API Token (Requires a domain, so the price can range)
3. BattleMetric's API Token (Premium is required for session tracking, $5/month)
4. Server
    4a. (paid) Heroku Application & PostgreSQL Addon (Roughly $12/month)
    4b. (free) Locally running the bot and hosting a local PostgreSQL database. 
> Blog post for installing and setting up necessary infrastructure coming soon.

## **Version 2 Release Features:**
- Manage active server settings with commands to `set`, `get`, and `clear` the active server.
- Check if players are currently active on the tracked server using their `username`, `Steam profile URL`, or `BattleMetrics ID`.
- Automatically extract and convert Steam profile URLs into usernames for easy player checks.
- Retain active server information across bot restarts through persistent configuration.
- Organize players into groups with commands to `list`, `add`, `remove`, `check`, `rename`, and `delete` groups.
- Track players by the group to see how many members are active and how long ago the offline members were prevsiouly active.
---
# **Commands**
## 1. SERVER COMMANDS
### 1.1 - Get Active Server
- **`/server get`** : Returns the current active server.
### 1.2 - Set Active Server
- **`/server set <server name>`** : Sets the active server. If multiple found, prompts selection.
### 1.3 - Clear Active Server
- **`/server clear`** : Clears the currently set active server.

---

## 2. GROUP COMMANDS
### 2.1 - Display All Groups
- **`/group list`** : Lists all groups created, their member count, and last time checked.
### 2.2 - Add Player to Group
- **`/group add <group name> <steam_profile_url, battlemetrics_id, or username>`** : Adds a player to the specified group (preferably BattleMetrics ID).  
  *The same player can be in multiple groups.*
### 2.3 - Remove Player From Group
- **`/group remove <group name> <player's name>`** : Removes a player from the specified group.  
### 2.4 - Query Group Server Status
- **`/group check <group name>`** : Checks the status of all members in a group against the active server.  
### 2.5 - Delete Group (Permanent)
- **`/group del <group name>`** : Deletes an entire group (non-recoverable).
### 2.6 - Change Group Name
- **`/group change <group name> <new group name>`** : Changes a group's name.
### 2.7 - Update Group
- **`/group update <group name>`** : Re-checks & updates each target group member’s username.

---

## 3. PLAYER COMMANDS
### 3.1 - Query Single User's Status
- **`/player check <steam_profile_url, battlemetrics_id, or username>`** : Checks for the player’s last session on the active server.  

---

## 4. SESSION TRACKING
- Utilize BattleMetric's session tracking for players to parse through their `start & end times` to determine:
  - **Average playtime**
  - **Most likely start time**
- Extract player's BattleMetrics ID.
- Add `last_login_date` and `last_scan_date` to the `groups` table for better tracking.
---
## **Usage Examples**
1. **Set the active server:**  
   ```
   /server set Rusty Moose
   ```
2. **Check if a player is active:**  
   ```
   /player check https://steamcommunity.com/profiles/76561198437932502
   ```
3. **Add a player to a group:**  
   ```
   /group add YuhBoy <battle id>
   ```
4. **List all defined groups:**  
   ```
   /group list
   ```
5. **Check active members in a group:**  
   ```
   /group check YuhBoy
   ```
---
## To Do:
- Session Tracking Enhancements : Improve session analysis using player's session history (i.e. most likely time(s) to be active). 
- Deployment Guide : Create a blog post detailing setup instructions. This should include both paid infrastructure route (Heroku) and free route (locally hosting). 
