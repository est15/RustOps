# import psycopg2 # Handles Heroku postgres URL (not utilized)
import os # Handle Environment Variable querying for script secrets
from dotenv import load_dotenv # Handle Environment Variable querying for script secrets
from datetime import datetime, date
import unicodedata

# Defined Necessary Imports for SQLAlchemy's ORM:
# SOURCE: https://docs.sqlalchemy.org/en/20/orm/quickstart.html
from sqlalchemy import create_engine # Handles connection to database
from typing import Optional # Necessary for specifying optional table entries
from sqlalchemy.orm import sessionmaker # Session # One or the other 
from sqlalchemy.sql import func # Handles querying encoded member name rows
from sqlalchemy import String, DateTime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationships
from sqlalchemy import select

# Decalarative Base Class 
class Base(DeclarativeBase):
    pass

# Group's Declarative Mapping (defines the table)
class Group(Base):
    # Table Name
    __tablename__ = 'groups'

    # [!] TABLE COLUMNS
    # id --> Unique ID Value
    # name --> Group Name 
    # member --> Player username
    # steam_id --> Player steam ID (unique)
    # battle_id --> Player BattleMetric ID (unique && nullable)
    # date --> Timestamp when added
    # Nullability derives from whether or not the Optional[] type modifier is used
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=False, nullable=False)
    member: Mapped[str] = mapped_column(String(255), unique=False, nullable=False)
    steam_id: Mapped[str] = mapped_column(String(64), unique=False, nullable=False)
    battle_id: Mapped[Optional[str]] = mapped_column(String(64), unique=False, nullable=True)
    date: Mapped[str] = mapped_column(String(255), nullable=True)

    # Define __repr__ function for python interpreter & usage
    def __repr__(self):
         return f"Group(id={self.id!r}, name={self.name!r}, member={self.member!r}, steam_id={self.steam_id}, battle_id={self.battle_id!r}, date={self.date!r})"

# Group last time checked table
class LastCheck(Base):
    # Table name
    __tablename__ = 'last_checked'
    
    # [!] TABLE COLUMNS
    # id --> Unique ID Value
    # group --> Group name (unique)
    # active --> Count of active players when last chcked
    # totla_player --> Totla count of players when last checked
    # date --> last date group was scanned for active players
    id: Mapped[int] = mapped_column(primary_key=True)
    group_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    active_count: Mapped[str] = mapped_column(String(5), nullable=False)
    total_count: Mapped[str] = mapped_column(String(5), nullable=False)
    date: Mapped[str] = mapped_column(String(128), nullable=True)


# Stores currently active server (replaces file method)
class active_server_table(Base):
    # Table name
    __tablename__ = "active_server"

    # [!] TABLE COLUMNS
    # server_id --> Active Server's ID
    # server_name --> Active Server's Name
    # date --> Date when active server set
    server_id: Mapped[str] = mapped_column(String(32), primary_key=True, nullable=False)
    server_name: Mapped[str] = mapped_column(String(128), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=date.today())

# SQLAlchemy Session (utilized by both database() and activeServer() classes)
# Load environment variables
try:
    # Get postgres URL from environment variable
    load_dotenv()       
    db_conn = os.getenv('DATABASE_URL')

    if not db_conn:
        raise EnvironmentError("[-] DATABASE_URL not found")

    if db_conn.startswith("postgres://"):
        db_conn = db_conn.replace("postgres://", "postgresql://", 1)

    # [!] Heroku Standard connection method (using SQLAlchemy instead):
    # https://devcenter.heroku.com/articles/connecting-heroku-postgres#connecting-in-python
    # self.conn = psycopg2.connect(self.db_url, sslmode='require')       
    
    # Connect to Heroku PostgreSQL Instance
    # The echo=True parameter indicates that SQL executions will be logged to standard out.
    engine = create_engine(db_conn, echo=True, 
                           client_encoding="utf8", 
                           pool_pre_ping=True) # pool_pre_ping handles postgres sessions becoming stale  (https://stackoverflow.com/questions/66692243/does-the-pre-ping-feature-in-sqlalchemy-db-pools-automatically-reconnect-and-sen)
    
    SQLSession = sessionmaker(bind=engine)
except Exception as e:
    print("[-] Unable to create SQLAlchemy session to Postgres backend.")


class database():
    def __init__(self):
        # Define the SQL session
        self.Session = SQLSession
    
    # [!] GET GROUP NAMES
    def get_all_groups(self):
        with self.Session() as session:
            # Return iterable item of groups
            try:
                # filter() offers more flexability when filtering, should use this as standard filtering method employed:
                # https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html#sqlalchemy.orm.Query.filter
                #   distinct() --> ensure no duplicate results
                #   all() --> returns the result of the query as a list of tuples.
                #   .scalars() --> returns list of strings 
                stmt = select(Group.name).distinct()
                results = session.execute(stmt).scalars().all() 
                return results
            except Exception as e:
                print(f"[-] get_grps Error: {e}")

    # [!] Find what group member is a part of --> used in previous version
    def get_member_group(self, steam_id: str):
        # Context Manager to Handle PostgreSQL Operations
        with self.Session() as session:
            try:
                results = session.query(Group).filter_by(steam_id=steam_id).one()
                if not results:
                    return None
                else:
                    return results
            except Exception as e:
                print(f"[-] get_mem_grp Error: {e}")
                return None
    
    # [!] ADD GROUP MEMBER METHOD
    def add_group_member(self, group_name, group_member, member_steam_id, member_battle_id):
        # Extract Additional Optional param(s):
        timestamp = f"{datetime.now().strftime('%Y-%m-%d')}"

        # Context Manager to Handle PostgreSQL Operations
        with self.Session() as session: 
            # Prepare INSERT statement parameters:
            user = Group(
                    name=group_name.lower(), # Ensure case insensitivity
                    member=group_member,
                    steam_id=member_steam_id,
                    battle_id=member_battle_id,
                    date=timestamp
                )
            
            # Add this to session
            session.add(user)

            # Commit to DB
            session.commit()
    
    # [!] CLEAR GROUP MEMBER METHOD
    def delete_group(self, group_name: str):
        with self.Session() as session:
            try:
                # Delete all members from the group
                group_members_deleted = session.query(Group).filter(func.lower(Group.name) == func.lower(group_name)).delete()

                # Delete the entry from group_last_checked
                last_checked_deleted = session.query(LastCheck).filter(func.lower(LastCheck.group_name) == func.lower(group_name)).delete()

                # Commit the transaction if any rows were deleted
                if group_members_deleted or last_checked_deleted:
                    # Push the changes the database
                    session.commit()
                    return f"```[+] Group '{group_name}' removed```"
                else:
                    return f"```[-] Group '{group_name}' not found```"
            except Exception as e:
                # If an error occurred make sure to rollback to previous state
                session.rollback()
                print(f"[-] del_all_grp_mem Error: {e}")
                return f"[-] Error deleting group '{group_name}'."
    
    # [!] GET GROUP MEMBERS
    def check_group_members(self, group_name: str):
        with self.Session() as session:
            return session.query(Group.member, Group.steam_id, Group.battle_id).filter(func.lower(Group.name) == func.lower(group_name)).all()

    # [!] ENSURE USER IS NOT ALREADY IN THE GRUOP ATTEMPTING TO ADD THEM TO
    def check_duplicate_group_member(self, group_name: str, member_name: str = None, steam_id: str = None, battle_id: str = None):
        with self.Session() as session:
            try:
                # Filter by group name
                query = session.query(Group).filter(Group.name == group_name)

                if member_name:
                    normalized_name = unicodedata.normalize("NFKC", member_name.strip())  # Normalize Unicode & remove spaces
                    query = query.filter(func.lower(Group.member) == func.lower(normalized_name))

                # Handle steam_id and battle_id conditions
                if steam_id:
                    query = query.filter(Group.steam_id == steam_id)
                if battle_id:
                    query = query.filter(Group.battle_id == battle_id)
                if not steam_id and not battle_id:
                    return None  # No identifiers to check against

                # Execute the query and return the result
                result = query.first()
                return result
            except Exception as e:
                print(f"[-] chk_dup_grp_mem Error: {e}")
                return None
    
    # [!] REMOVE A SINGLE GROUP MEMBER METHOD
    def rem_group_member(self, group_name: str, member_name: str):
        with self.Session() as session:
            try:
                # Trim whitespace & normalize casing
                member_name = member_name.strip()
                member_name = unicodedata.normalize("NFKC", member_name)  # Normalize Unicode

                # Debugging Output (REMOVE AFTER TESTING)
                print(f"Received input from Discord: '{member_name}'")
                
                # GET THE ROW TO DELETE
                # [!] This does assume that the first occurrence of the first user in the group will be deleted
                member_to_delete = session.query(Group).filter(Group.name == group_name, Group.member == member_name).first()
                
                # If member found then delete
                if member_to_delete:
                    session.delete(member_to_delete)
                    # Commit the changes the database:
                    session.commit()
                    return(False) # Returns False since the error output will return True (since its not an empty string), easy way to tell the outcome
                # else error
                else:
                    return f"```markdown\n[-] '{member_name}' not found '{group_name}'```"
            except Exception as e:
                print(f"[-] rem_grp_mem Error: {e}")


    # [!] UPDATE GROUP'S LAST CHECKED VALUES
    def update_group_last_checked(self, group_name: str, active_player_count, total_player_count):
        """Takes parameters from /group command(s) to update a groups's variables in the group_last_check table"""
        with self.Session() as session:
            try:
                # Retrieve the group's current values
                entry = session.query(LastCheck).filter_by(group_name=group_name).first()
                
                # Get the current time stamp
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Check group_name against groups table to see if it actually exists
                group_exists = session.query(Group).filter(func.lower(Group.name) == func.lower(group_name)).first()

                # Group in last_checked, update rows
                if entry:
                    entry.active_count = str(active_player_count)
                    entry.total_count = str(total_player_count)
                    entry.date = current_time
                # Group not in last_checked, but exists, add to last_checked
                elif group_exists:
                    new_entry = LastCheck(
                        group_name = group_name,
                        active_count = str(active_player_count),
                        total_count = str(total_player_count),
                        date = current_time
                    )
                    session.add(new_entry)
                
                # Commit the changes
                session.commit()
            except Exception as e:
                print(f"[-] grp_lst_chk Error: {e}")
                session.rollback()


    # [!] GET GROUP'S LAST CHECKED VALUE(S)
    def get_group_last_checked(self, group_name: str):
        """Takes parameters from /group command(s) to retrieves a groups's variables in the group_last_check table"""
        with self.Session() as session:
            try:
                # Retreieve the group's current values
                entry = session.query(LastCheck).filter_by(group_name=group_name).first()
                return entry # list of tuples [(column_name, column, value)]
            except Exception as e:
                print(f"[-] grp_lst_chk Error: {e}")
                return f"[-] grp_lst_chk Error: {e}"
    
    # [!] CHANGE A GROUP'S NAME
    # changed in both groups & last_checked tables
    def change_group_name(self, current_name: str, new_name: str):
        with self.Session() as session:
            try:
                # Update group name in the groups table
                group_update_count = (
                    session.query(Group)
                    .filter(func.lower(Group.name) == func.lower(current_name))
                    .update({Group.name: new_name.lower()})
                )

                # Update group name in the last_checked table
                last_checked_update_count = (
                    session.query(LastCheck)
                    .filter(func.lower(LastCheck.group_name) == func.lower(current_name))
                    .update({LastCheck.group_name: new_name.lower()})
                )

                # Commit if any rows were updated
                if group_update_count > 0 or last_checked_update_count > 0:
                    session.commit()
                    return f"```[+] Group name changed from '{current_name}' to '{new_name}'```"
                else:
                    return f"```[-] Group '{current_name}' not found```"
            except Exception as e:
                print(f"[-] chng_grp_nme Error: {e}")
                return
            
# Contains guild's active server set, get, and clear methods
class activeServer:
    def __init__(self):
        # Define the SQL session
        self.Session = SQLSession

    # [!] GET ACTIVE SERVER
    def get_server(self):
        with self.Session() as session:
            try:
                # Query the currently set 
                stmt = select(active_server_table.server_id, active_server_table.server_name)
                server_result = session.execute(stmt).first()
                
                if server_result: 
                    server_id, server_name = server_result
                    return [server_id, server_name]           
                else:
                    return None
            except Exception as e:
                print(f"[-] get_actv_srv Error: {e}")

    # [!] SET ACTIVE SERVER
    def set_server(self, server_id:str,  server_name:str):
        with self.Session() as session:
            try:
                # Get Currently Active Server
                existing_server = session.query(active_server_table).first()

                # If server set, then update
                if existing_server: 
                    existing_server.server_id = server_id
                    existing_server.server_name = server_name
                    existing_server.date = date.today()
                # if no server set, then add 
                else:
                    # Populate active server if one does not exists
                    new_server = active_server_table(server_id=server_id, server_name=server_name, date=date.today())
                    session.add(new_server)

                session.commit()
                return f"```[+] Server Set to {server_name} (Server ID: {server_id})```"

            except Exception as e:
                print(f"[-] set_actv_srv Error: {e}")
                session.rollback()

    # [!] CLEAR ACTIVE SERVER
    def clear_server(self):
        with self.Session() as session:
            try:
                # See if a server is set
                existing_server = session.query(active_server_table).first()
                if existing_server:
                    session.delete(existing_server)
                    session.commit()
                    return "```[+] Active server cleared```"
                # Notify server not set yet
                else:
                    return f"```[-] no server set:\nSet Server with: /server set <Server ID>```"
                                    
            except Exception as e:
                print(f"[-] clear_actv_srv Error: {e}")
                session.rollback()


