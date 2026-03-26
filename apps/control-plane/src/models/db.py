from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, JSON, Text, ForeignKey, UniqueConstraint
from database import Base

class OpportunityModel(Base):
    __tablename__ = "opportunities"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    external_id = Column(String, nullable=False)
    source = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    title = Column(String, nullable=False)
    value_estimate = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    captured_at = Column(DateTime(timezone=True), nullable=False)
    score_total = Column(Float, nullable=True)
    score_confidence = Column(Float, nullable=True)
    score_factors = Column(JSON, nullable=True)
    verification_status = Column(String, nullable=False, default="pending")
    
    __table_args__ = (UniqueConstraint("external_id", "source", name="uix_ext_source"),)

class VerificationEventModel(Base):
    __tablename__ = "verification_events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    opportunity_id = Column(String, nullable=False)
    actor_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

class WatchlistItemModel(Base):
    __tablename__ = "watchlist_items"
    
    user_id = Column(String, primary_key=True)
    opportunity_id = Column(String, primary_key=True)

class ActionItemModel(Base):
    __tablename__ = "action_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    opportunity_id = Column(String, nullable=False)
    owner_id = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    due_date = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")

class GrantScanResultModel(Base):
    __tablename__ = "grant_scan_results"
    
    # Composite PK or single PK
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, default="global")
    source_id = Column(String, nullable=False)
    source_name = Column(String, nullable=False)
    title = Column(Text, nullable=False, default="")
    published_at = Column(String, nullable=False, default="")
    location = Column(String, nullable=False, default="")
    industry = Column(String, nullable=False, default="")
    details = Column(Text, nullable=False, default="")
    funder = Column(String, nullable=False, default="")
    program = Column(String, nullable=False, default="")
    max_amount = Column(String, nullable=False, default="")
    eligibility_criteria = Column(Text, nullable=False, default="")
    open_date = Column(String, nullable=False, default="")
    close_date = Column(String, nullable=False, default="")
    application_url = Column(Text, nullable=False, default="")
    target_sectors = Column(Text, nullable=False, default="")
    url = Column(Text, nullable=False)
    due_date = Column(String, nullable=False, default="")
    grant_amount = Column(String, nullable=False, default="")
    match_score = Column(Integer, nullable=False, default=0)
    eligible = Column(Integer, nullable=False, default=0)
    eligibility_reason = Column(Text, nullable=False, default="")
    recommended = Column(Integer, nullable=False, default=0)
    deadline_soon = Column(Integer, nullable=False, default=0)
    manual_check_needed = Column(Integer, nullable=False, default=0)
    workflow_status = Column(String, nullable=False, default="New")
    notes = Column(Text, nullable=False, default="")
    contact_names = Column(Text, nullable=False, default="")
    reference_numbers = Column(Text, nullable=False, default="")
    submission_date = Column(String, nullable=False, default="")
    outcome = Column(String, nullable=False, default="Pending")
    external_key = Column(String, nullable=False, default="")
    status = Column(String, nullable=False, default="new")
    scanned_at = Column(String, nullable=False, default="")
