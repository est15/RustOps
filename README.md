# RustOps
Python discord.py bot to track active players on Rust a given rust server. This will run and be accessible / testable in discord by running from CLI. However, the intended purpose is to run in the cloud. I specifically implemented this bot using Heroku. I plan on making a blog post that creates the installation and setup steps for this.

# Added in Version 2:
- Registered server command groups (`/server <get/set/clear>` and `/player check <username or steam proifle>`)
- Combined previous /find command into /server set command
- Added ability to extract steam profile URL into username, then perform same check against battlemtrics API 
- Add `.activeServer` config file to track active server even across bot restart

# To do:
1. Update README to include installation / usage
2. Implement `/group` subcommand
3. Implement PostgreSQL database to track groups and users in gruops
4. `/group create <groupname>` Creates group to track
5. `/group add <groupname> <steamprofile-url>` Adds player to group to track
6. `/group check <groupname or all>` Checks each group's member for active players