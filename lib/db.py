# import psycopg2 # Handles Heroku postgres URL (not utilized)
import os # Handle Environment Variable querying for script secrets
from dotenv import load_dotenv # Handle Environment Variable querying for script secrets
from datetime import datetime

# Defined Necessary Imports for SQLAlchemy's ORM:
# SOURCE: https://docs.sqlalchemy.org/en/20/orm/quickstart.html
from sqlalchemy import create_engine # Handles connection to database
from typing import Optional # Necessary for specifying optional table entries
from sqlalchemy.orm import sessionmaker # Session # One or the other 
from sqlalchemy import String
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

    # [!] COLUMNS   
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
    steam_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    battle_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    date: Mapped[str] = mapped_column(String(255), nullable=True)

    # Define __repr__ function for python interpreter & usage
    def __repr__(self):
         return f"Group(id={self.id!r}, name={self.name!r}, member={self.member!r}, steam_id={self.steam_id}, battle_id={self.battle_id!r}, date={self.date!r})"

class database():
    def __init__(self):
        # Get secrets from environment  variables
        load_dotenv()       
        self.db_conn = os.getenv('DATABASE_URL')
        if not self.db_conn:
            raise EnvironmentError("[-] DATABASE_URL not found")
        
        if self.db_conn.startswith("postgres://"):
            self.db_conn = self.db_conn.replace("postgres://", "postgresql://", 1)

        # [!] Heroku Standard connection method (using SQLAlchemy instead):
        # https://devcenter.heroku.com/articles/connecting-heroku-postgres#connecting-in-python
        # self.conn = psycopg2.connect(self.db_url, sslmode='require')       
        
        # Connect to Heroku PostgreSQL Instance
        # The echo=True parameter indicates that SQL emitted by connections will be logged to standard out.
        self.engine = create_engine(self.db_conn, echo = True)

        # Define the session class
        self.Session = sessionmaker(bind=self.engine)
    
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

    # [!] Find what group member is a part of
    # executed if add_member fails b/c user is already part of a group
    def get_member_group(self, steam_id: str):
        # Context Manager to Handle PostgreSQL Operations
        with self.Session() as session:
            try:
                results = session.query(Group).filter_by(steam_id=steam_id).one()
                return results
            except Exception as e:
                print(f"[-] get_mem_grp Error: {e}")
                return None
    
    # [!] ADD GROUP MEMBER METHOD
    # *args is handling optional battlemetric's ID && future optional params
    def add_group_member(self, group_name, group_member, member_steam_id, *args):
        # Extract Additional Optional param(s):
        member_battle_id = args[0] if args else None # Unpack arguments
        timestamp = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # Context Manager to Handle PostgreSQL Operations
        with self.Session() as session: 
            # Prepare INSERT statement parameters:
            user = Group(
                    name=group_name,
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
    def delete_all_group_members(self, group_name: str, steam_url: str):
        with self.Session() as session:
            try:   
                pass
            except Exception as e:
                print(f"[-] del_all_grp_mem Error: {e}")

    # [!] CHCEK TARGET GROUP PLAYERS FOR THOSE THAT ARE ACTIVE
    def check_group_members(self, group_name: str):
        with self.Session() as session:
            try:
                results = session.query(Group.member, Group.steam_id).filter(Group.name == group_name).all()
                if not results:
                    raise Exception("[-] no group or members found")
                else:
                    return results
            except Exception as e:
                print(f"[-] clr_grp_mem Error: {e}")
    
    # [!] REMOVE A SINGLE GROUP MEMBER METHOD
    def rem_group_member(self, group_name: str, member_name: str):
        with self.Session() as session:
            try:
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
                    return f"```markdown\n[-] **{member_name}** not found **{group_name}**```"
            except Exception as e:
                print(f"[-] rem_grp_mem Error: {e}")
    
        


