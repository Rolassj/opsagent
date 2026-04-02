"""Modelo SQLAlchemy para la tabla diagnoses."""

from datetime import datetime
from sqlalchemy import Column, String, Text, Float, JSON, DateTime, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False, default="")
    status = Column(String, nullable=False)
    detected_domain = Column(String, nullable=False)
    executive_summary = Column(Text, nullable=False, default="")
    kpis = Column(JSON, nullable=False, default=dict)
    anomalies = Column(JSON, nullable=False, default=list)
    trends = Column(JSON, nullable=False, default=list)
    diagnosis = Column(Text, nullable=False, default="")
    recommendations = Column(JSON, nullable=False, default=list)
    data_quality_report = Column(JSON, nullable=False, default=dict)
    processing_time_seconds = Column(Float, nullable=False, default=0.0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
