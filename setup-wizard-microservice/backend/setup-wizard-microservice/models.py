from sqlalchemy import (Column, Integer, String, Text, DateTime, Float,
                        Boolean, ForeignKey, Time)
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

def now():
    return datetime.datetime.utcnow()

class Company(Base):
    __tablename__ = "company"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    address = Column(String(255))
    city = Column(String(50))
    country = Column(String(50))
    phone = Column(String(50))
    email = Column(String(100))
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime)

    zones = relationship("Zone", back_populates="company")

class Zone(Base):
    __tablename__ = "zone"
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("company.id"), nullable=False)
    area_id = Column(String, nullable=True)  # NOT UNIQUE anymore
    name = Column(String(100), nullable=False)
    description = Column(Text)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime)

    company = relationship("Company", back_populates="zones")
    devices = relationship("Device", back_populates="zone")

class Device(Base):
    __tablename__ = "device"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ha_device_id = Column(String(150))   # can be NULL
    zone_id = Column(Integer, ForeignKey("zone.id"), nullable=True)
    name = Column(String(150), nullable=False)
    type = Column(String(50))
    last_sync = Column(DateTime)

    zone = relationship("Zone", back_populates="devices")
    entities = relationship("Entity", back_populates="device")

class Entity(Base):
    __tablename__ = "entity"
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("device.id"), nullable=True)
    entity_id = Column(String(150), unique=True, nullable=False)
    friendly_name = Column(String(150))
    unit = Column(String(10))
    min_value = Column(Float)
    max_value = Column(Float)
    step = Column(Float)
    mode = Column(String(50))
    selected = Column(Boolean, default=False)
    last_state = Column(String(50))
    last_updated = Column(DateTime)

    device = relationship("Device", back_populates="entities")

class Setup(Base):
    __tablename__ = "setup"
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("company.id"), nullable=False)
    config_name = Column(String(100))
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)
    status = Column(String(20), default="draft")

    schedules = relationship("SetupSchedule", back_populates="setup")

class SetupSchedule(Base):
    __tablename__ = "setup_schedule"
    id = Column(Integer, primary_key=True, autoincrement=True)
    setup_id = Column(Integer, ForeignKey("setup.id"), nullable=False)
    zone_id = Column(Integer, ForeignKey("zone.id"), nullable=False)
    days = Column(String(10), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    temp_min = Column(Float, nullable=False)
    temp_max = Column(Float, nullable=False)
    active = Column(Boolean, default=True)

    setup = relationship("Setup", back_populates="schedules")
    
class TemperatureRule(Base):
    __tablename__ = "temperature_rule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Integer, ForeignKey("zone.id"))
    temp_min = Column(Float)
    temp_max = Column(Float)
    days = Column(Text)             # JSON string: ["mon","tue","wed"]
    start_time = Column(String(10)) # "08:00"
    end_time = Column(String(10))   # "17:00"
    
class Decision(Base):
    __tablename__ = "decisions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    goal = Column(Text)
    reasoning = Column(Text)
    decision_package_json = Column(Text)
    action_summary = Column(Text)
    status = Column(String(20), nullable=False, default='PENDING')
    executed_action = Column(Text)
    target_entity = Column(Text)
    action_result = Column(Text)
    confidence = Column(Float)
    notes = Column(Text)
    created_at = Column(Text, nullable=False, default=lambda: datetime.datetime.utcnow().isoformat())

