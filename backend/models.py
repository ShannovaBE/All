from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, Float, Integer, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DatasetRecord(Base):
    __tablename__ = "dataset_records"

    file_hash = Column(Text, primary_key=True)
    schema_version = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    filename = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    file_type = Column(Text, nullable=True)
    quality_score = Column(Float, nullable=True)
    quality_scores = Column(JSON, nullable=False)
    category_verification = Column(JSON, nullable=False)
    status = Column(Text, nullable=True)
    details = Column(JSON, nullable=False)
    description = Column(Text, nullable=False, default="")
    extra = Column(JSON, nullable=True)
    owner = Column(Text, nullable=True)
    storage_provider = Column(Text, nullable=True)
    object_key = Column(Text, nullable=True)
    bytes = Column(BigInteger, nullable=True)
    mime = Column(Text, nullable=True)
    provenance = Column(JSON, nullable=False, default=dict)
    compliance_evidence = Column(JSON, nullable=False, default=dict)
    access_policy = Column(JSON, nullable=False, default=dict)
    restriction_status = Column(Text, nullable=False, default="active", index=True)
    retention_policy = Column(JSON, nullable=False, default=dict)
    retention_expires_at = Column(DateTime(timezone=True), nullable=True, index=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Text, primary_key=True)
    username = Column(Text, nullable=False, unique=True, index=True)
    email = Column(Text, nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    plan = Column(Text, nullable=False, default="free", index=True)
    kyb_status = Column(Text, nullable=False, default="pending", index=True)
    restricted = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False, unique=True, index=True)
    review_text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)
    status = Column(Text, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="reviews_rating_range"),
        CheckConstraint(
            "status IN ('pending','approved','rejected')",
            name="reviews_status_allowed",
        ),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Text, primary_key=True)
    actor_id = Column(Text, nullable=True, index=True)
    action = Column(Text, nullable=False, index=True)
    resource = Column(Text, nullable=True, index=True)
    purpose = Column(Text, nullable=True)
    result = Column(Text, nullable=False, index=True)
    ip = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
