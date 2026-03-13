from sqlalchemy import Column, String, Float, Date, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.db.base import Base


class CropType(str, enum.Enum):
    CANOLA = "canola"
    WHEAT = "wheat"
    BARLEY = "barley"
    LENTILS = "lentils"
    PEAS = "peas"
    FLAX = "flax"
    OATS = "oats"


class Farm(Base):
    __tablename__ = "farms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    owner_email = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    fields = relationship("Field", back_populates="farm", cascade="all, delete-orphan")


class Field(Base):
    __tablename__ = "fields"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id"), nullable=False)

    name = Column(String, nullable=False)

    # LSD location — the core geographic identifier in Saskatchewan
    lsd = Column(String(20), nullable=False)          # e.g. "NE-12-34-21-W3"
    legal_subdivision = Column(String(4))             # e.g. "NE"
    section = Column(String(4))
    township = Column(String(4))
    range_num = Column(String(4))
    meridian = Column(String(4))                      # W2, W3 etc.

    # Approx center coords derived from LSD (for weather lookup)
    latitude = Column(Float)
    longitude = Column(Float)

    # Current season
    crop_type = Column(Enum(CropType), nullable=False)
    plant_date = Column(Date, nullable=False)
    last_spray_date = Column(Date)
    last_fertilization_date = Column(Date)

    # Previous season (crop rotation)
    previous_crop_type = Column(Enum(CropType))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    farm = relationship("Farm", back_populates="fields")
    spray_events = relationship("SprayEvent", back_populates="field", cascade="all, delete-orphan")
