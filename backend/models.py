"""SQLAlchemy models for sensors, measurements, and alert rules."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.db import Base
from backend.utils import utcnow


class Sensor(Base):
    """Represents a physical sensor device or probe in the terrarium."""

    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    model = Column(String, nullable=True)
    location = Column(String, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    poll_interval_sec = Column(Integer, default=60, nullable=False)
    unit_preference = Column(String, default="f", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    measurements = relationship("Measurement", back_populates="sensor", lazy="selectin")


class Measurement(Base):
    """Represents a single recorded reading from a sensor metric."""

    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False, index=True)
    metric = Column(String, nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    sensor = relationship("Sensor", back_populates="measurements", lazy="joined")


class AlertRule(Base):
    """Represents a simple threshold alert configuration for a metric."""

    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True)
    metric = Column(String, nullable=False, index=True)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    channel = Column(String, nullable=False)
    target = Column(String, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
