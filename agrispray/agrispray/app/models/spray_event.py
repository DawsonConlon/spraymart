from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.db.base import Base


class SprayDecision(str, enum.Enum):
    SPRAY_NOW = "spray_now"
    WAIT = "wait"
    DO_NOT_SPRAY = "do_not_spray"


class SprayEvent(Base):
    """Records every recommendation generated + what the farmer actually did."""
    __tablename__ = "spray_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id = Column(UUID(as_uuid=True), ForeignKey("fields.id"), nullable=False)

    # What the engine decided and why
    decision = Column(Enum(SprayDecision), nullable=False)
    reason_summary = Column(String(500))              # Human-readable: "Wind forecast 8 km/h, 6hr window opens 7am"
    score_breakdown = Column(JSONB)                   # Full scoring JSON for debugging/ML training later

    # Conditions at time of recommendation
    gdd_accumulated = Column(Float)
    plant_stage_estimate = Column(String(50))         # e.g. "3-leaf", "bolting", "flowering"
    wind_speed_kmh = Column(Float)
    temperature_c = Column(Float)
    humidity_pct = Column(Float)
    forecast_rain_24h = Column(Boolean)
    wind_direction = Column(String(5))

    # Farmer action (filled in later — valuable training data)
    farmer_sprayed = Column(Boolean)
    farmer_sprayed_at = Column(DateTime(timezone=True))
    farmer_notes = Column(Text)

    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    field = relationship("Field", back_populates="spray_events")
