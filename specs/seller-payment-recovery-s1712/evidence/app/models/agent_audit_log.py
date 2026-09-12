"""
Append-only audit log for agent-facing discovery and purchase actions.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.core.database import Base


class AgentAuditLog(Base):
    """Append-only audit trail for public agent-facing tool calls."""

    __tablename__ = "agent_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # FK to agent_api_keys is deferred until M2, when that table exists.
    api_key_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    tool_name = Column(String(128), nullable=False, index=True)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=True, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True, index=True)
    client_ip = Column(INET, nullable=True)
    request_payload = Column(JSONB, nullable=True)
    response_payload = Column(JSONB, nullable=True)
    http_status = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, index=True)
    error_message = Column(String, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
