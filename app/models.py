"""
Pydantic models for ticket classification.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


class UrgencyLevel(str, Enum):
    """Urgency classification levels."""
    CRITICAL = "critical"  # System down, blocker
    HIGH = "high"          # Major functionality affected
    MEDIUM = "medium"      # Feature request or minor issue
    LOW = "low"            # General inquiry


class IntentType(str, Enum):
    """Customer intent categories."""
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    ACCOUNT_ISSUE = "account_issue"
    BILLING_INQUIRY = "billing_inquiry"
    HOW_TO = "how_to"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"


class ProductArea(str, Enum):
    """Product areas affected."""
    API = "api"
    DASHBOARD = "dashboard"
    MOBILE_APP = "mobile_app"
    INTEGRATIONS = "integrations"
    BILLING = "billing"
    AUTHENTICATION = "authentication"
    ANALYTICS = "analytics"
    GENERAL = "general"


class Classification(BaseModel):
    """Classification result for a ticket."""
    urgency: UrgencyLevel
    intent: IntentType
    product: ProductArea
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    reasoning: str = Field(..., description="Explanation of classification")


class Ticket(BaseModel):
    """Customer support ticket."""
    id: str
    subject: str
    description: str
    customer_email: Optional[str] = None


class TicketWithClassification(BaseModel):
    """Ticket with classification results."""
    ticket: Ticket
    classification: Classification
