# RustOps
Python discord.py bot to track active players on a given Rust server.

### Requirements:
1. Discord bot
2. Steam Web API Token
3. BattleMetric's API Token
4. Heroku Application
5. Heroku PostgreSQL Addon
> Blog post for installing and setting up necessary infrastructure coming soon.

# Version 1 Release Features:
- Manage active server settings with commands to `set`, `get`, and `clear` the active server
- Check if players are currently active on the tracked server using their `username` or `Steam profile URL`
- Automatically extract and convert Steam profile URLs into usernames for easy player checks
- Retain active server information across bot restarts through persistent configuration
- Organize players into groups with commands to `list`, `add`, `remove`, and `check` groups

# **To Do:**
### 1. Add `Group` Command Group: 
- `/group del <groupname>` --> Deletes group entirely (non-recoverable).
- `/group change <groupname> <new groupname>` --> Changes group name to new group name.
- `/group update <groupname>` --> Re-check & update each target group member's usernam.
### 3. Create routine check of players in groups
- Scheduled task to periodically re-check group(s)
### 4. Session Tracking
- Utilize BattleMetric's Session tracking for players to parse through their start & end times to determine: average time played and most likely start time.
- Extract player's battlemetric's player ID.
- Add `last_login_date` (column) and `last_scan_date` (column) to `groups` table.

# **Completed** 
- Implemented PostgreSQL backend (2/3/2025)
- Implemented `/group add` command  (2/3/2025)
- `/group list` List all groups name (2/3/2025)
- `/group check <group name>` Checks group for active players   (2/3/2025)
- `/group remove <groupname> <steamprofile-url>` Removes player from group (2/3/2025)