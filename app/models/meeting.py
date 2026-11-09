from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.core.database import Base


class MeetingORM(Base):
    __tablename__ = "room_live_meetings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    title = Column(String(120), nullable=False)
    created_by = Column(Integer, nullable=False, index=True)
    is_closed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)


class MeetingMemberORM(Base):
    __tablename__ = "room_live_meeting_members"
    __table_args__ = (UniqueConstraint("meeting_id", "user_id", name="uq_room_live_meeting_member"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    meeting_id = Column(Integer, ForeignKey("room_live_meetings.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)
