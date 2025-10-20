"""
AI-powered ticket classifier using OpenAI GPT-4o-mini.
"""

import os
import json
from openai import OpenAI
from app.models import Ticket, Classification, UrgencyLevel, IntentType, ProductArea


CLASSIFICATION_PROMPT = """You are an expert customer support ticket classifier for a B2B SaaS platform.

Analyze the following support ticket and classify it according to these dimensions:

**URGENCY LEVELS:**
- critical: System down, production blocker, revenue-impacting, immediate response needed
- high: Major functionality affected, multiple users impacted, workaround exists
- medium: Feature request, minor bug, single user affected, non-blocking
- low: General inquiry, documentation question, nice-to-have request

**INTENT TYPES:**
- bug_report: Technical malfunction or error
- feature_request: Request for new functionality
- account_issue: Account access, permissions, settings
- billing_inquiry: Payments, invoices, subscription issues
- how_to: How to use existing features, documentation questions
- integration: Third-party integrations, API connectivity
- performance: Slow response times, timeouts, latency issues
- security: Security concerns, vulnerabilities, compliance

**PRODUCT AREAS:**
- api: REST API, GraphQL, webhooks
- dashboard: Web interface, UI components
- mobile_app: iOS or Android applications
- integrations: Third-party integrations (Slack, Zapier, etc.)
- billing: Payment processing, invoices
- authentication: Login, SSO, OAuth
- analytics: Reports, data exports, metrics
- general: Multiple areas or unspecified

**TICKET:**
Subject: {subject}
Description: {description}

Respond ONLY with valid JSON in this exact format:
{{
  "urgency": "critical|high|medium|low",
  "intent": "bug_report|feature_request|account_issue|billing_inquiry|how_to|integration|performance|security",
  "product": "api|dashboard|mobile_app|integrations|billing|authentication|analytics|general",
  "confidence": 0.95,
  "reasoning": "Brief explanation of classification (1-2 sentences)"
}}
"""


class TicketClassifier:
    """AI-powered ticket classifier."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize classifier with OpenAI API key.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")

        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"

    def classify(self, ticket: Ticket) -> Classification:
        """
        Classify a support ticket.

        Args:
            ticket: Ticket to classify

        Returns:
            Classification result
        """
        # Create prompt with ticket data
        prompt = CLASSIFICATION_PROMPT.format(
            subject=ticket.subject,
            description=ticket.description
        )

        # Call OpenAI API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a technical support ticket classifier. Respond only with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Lower temperature for consistent classification
            max_tokens=300
        )

        # Parse JSON response
        content = response.choices[0].message.content

        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse GPT response as JSON: {content}") from e

        # Validate and create Classification object
        return Classification(
            urgency=UrgencyLevel(result["urgency"]),
            intent=IntentType(result["intent"]),
            product=ProductArea(result["product"]),
            confidence=result["confidence"],
            reasoning=result["reasoning"]
        )

    def classify_batch(self, tickets: list[Ticket]) -> list[Classification]:
        """
        Classify multiple tickets.

        Args:
            tickets: List of tickets to classify

        Returns:
            List of classifications
        """
        return [self.classify(ticket) for ticket in tickets]
