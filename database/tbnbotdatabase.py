from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, create_engine, inspect, text
from sqlalchemy.orm import declarative_base, Session
from pathlib import Path

database_path = Path(__file__).parent.parent.joinpath(
    'resources/tbn-bot-database.db')

Base = declarative_base()

class TbnMember(Base):
    __tablename__ = 'tbn_member'

    def __init__(self, 
                 id: int, 
                 birthday: datetime = None, 
                 last_stream_announcement_timestamp: datetime = None, 
                 is_naughty_listed = False):
        self.id = id
        self.birthday = birthday
        self.created_at = datetime.now()
        self.last_stream_announcement_timestamp = last_stream_announcement_timestamp
        self.is_naughty_listed = is_naughty_listed

    id = Column(Integer, primary_key=True)
    birthday = Column(Date)
    created_at = Column(DateTime)
    last_stream_announcement_timestamp = Column(DateTime)
    is_naughty_listed = Column(Boolean)

class TbnMemberAudit(Base):
    __tablename__ = 'tbn_member_audit'

    def __init__(self, member: TbnMember):
        self.member_id = member.id
        self.birthday = member.birthday
        self.created_at = datetime.now()
        self.is_naughty_listed = False

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey('tbn_member.id'))
    birthday = Column(Date)
    created_at = Column(DateTime)    
    is_naughty_listed = Column(Boolean)

class JoinTime(Base):
    __tablename__ = 'join_time'

    def __init__(self, member_id: int, channel_id: int, join_time: datetime):
        self.member_id = member_id
        self.channel_id = channel_id
        self.join_time = join_time

    member_id = Column(Integer, primary_key=True)
    channel_id = Column(Integer)
    join_time = Column(DateTime)

def database_session() -> Session:
    engine = create_engine('sqlite:///' + database_path.as_posix())
    Base.metadata.create_all(engine)
    
    # db migrations? no thank you
    add_column_if_not_exists(engine, TbnMember.__tablename__, TbnMember.is_naughty_listed, 'BOOLEAN')
    return Session(engine)

def add_column_if_not_exists(engine, table_name, column_property, column_type):
    # Get the actual column name from the property
    if hasattr(column_property, 'key'):
        # If it's a SQLAlchemy column/property
        column_name = column_property.key
    elif hasattr(column_property, '__name__'):
        # If it's a function or property
        column_name = column_property.__name__
    else:
        # Fallback to string representation
        column_name = str(column_property)
    
    # Create an inspector
    inspector = inspect(engine)
    
    # Get the columns for the table
    columns = inspector.get_columns(table_name)
    
    # Check if the column already exists
    column_exists = any(col['name'] == column_name for col in columns)
    
    # Add the column if it doesn't exist
    if not column_exists:
        # Use only the column name, not the full reference
        sql = text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}')
        with engine.connect() as conn:
            conn.execute(sql)
            conn.commit()
        print(f"Column '{column_name}' added to table '{table_name}'")
    else:
        print(f"Column '{column_name}' already exists in table '{table_name}'")
