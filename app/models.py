import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from .db import Base

class Record(Base):
    __tablename__ = "records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    title = Column(Text)
    abstract = Column(Text)
    year = Column(Integer)
    url = Column(Text)
    raw_json = Column(JSONB)
    text_hash = Column(String)
    topic = Column(String)
    summary_scientific = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
