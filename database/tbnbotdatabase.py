from datetime import datetime
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, create_engine
from sqlalchemy.orm import declarative_base, Session
from pathlib import Path

database_path = Path(__file__).parent.parent.joinpath(
    'resources/tbn-bot-database.db')

Base = declarative_base()


class TbnMember(Base):
    __tablename__ = 'tbn_member'

    def __init__(self, id: int, birthday: datetime):
        self.id = id
        self.birthday = birthday
        self.created_at = datetime.now()

    id = Column(Integer, primary_key=True)
    birthday = Column(Date)
    created_at = Column(DateTime)

class TbnMemberAudit(Base):
    __tablename__ = "tbn_member_audit"

    def __init__(self, member: TbnMember):
        self.member_id = member.id
        self.birthday = member.birthday
        self.created_at = datetime.now()

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey('tbn_member.id'))
    birthday = Column(Date)
    created_at = Column(DateTime)    

def database_session() -> Session:
    engine = create_engine('sqlite:///' + database_path.as_posix())
    Base.metadata.create_all(engine)
    return Session(engine)
    