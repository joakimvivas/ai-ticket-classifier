"""
5 realistic customer support ticket examples for testing classification.
"""

from app.models import Ticket


EXAMPLE_TICKETS = [
    Ticket(
        id="TICKET-001",
        subject="API returning 500 errors - Production down!",
        description="""
        Our production system is completely down. We're getting 500 Internal Server Errors
        on all API endpoints since 2 hours ago. This is affecting all our customers and we're
        losing revenue. We need immediate assistance!

        Error message: "Internal Server Error - Contact Support"
        Endpoint: /api/v2/users
        Timestamp: 2025-01-20 14:32 UTC

        This is URGENT - our SLA requires 99.9% uptime.
        """,
        customer_email="cto@acmecorp.com"
    ),

    Ticket(
        id="TICKET-002",
        subject="How to export data to CSV?",
        description="""
        Hi team,

        I'm trying to export our analytics data to CSV format but can't find the option
        in the dashboard. I've checked the documentation but it's not clear where this
        feature is located.

        Could you guide me through the steps? Our team needs this for monthly reporting.

        Thanks!
        """,
        customer_email="analyst@smallbiz.com"
    ),

    Ticket(
        id="TICKET-003",
        subject="Request: Dark mode for mobile app",
        description="""
        Hello,

        We've received feedback from 30+ users requesting a dark mode option for the
        mobile app. This would greatly improve usability during nighttime usage.

        Is this feature on your roadmap? Our users would really appreciate it.

        Current app version: 2.4.1
        Platform: Both iOS and Android

        Best regards
        """,
        customer_email="product@techstartup.io"
    ),

    Ticket(
        id="TICKET-004",
        subject="Charged twice this month - billing error",
        description="""
        I noticed I was charged twice for my Pro subscription this month:

        - Charge 1: $49.99 on Jan 5th
        - Charge 2: $49.99 on Jan 15th

        My subscription should only charge once per month. Can you please investigate
        and refund the duplicate charge?

        Account ID: acc_7892341
        Payment method: Visa ending in 4242
        """,
        customer_email="finance@enterprise.com"
    ),

    Ticket(
        id="TICKET-005",
        subject="Slack integration not syncing messages",
        description="""
        Our Slack integration stopped syncing messages to the dashboard since yesterday.

        Setup:
        - Connected via OAuth 2 weeks ago
        - Was working perfectly until Jan 19th
        - Workspace: techcorp.slack.com
        - Channels connected: #support, #sales, #general

        When I check the integration status it shows "Connected" with a green indicator,
        but no new messages appear in the dashboard. Last synced message is from Jan 18th.

        We rely on this for our support workflow. Not critical but important to fix soon.
        """,
        customer_email="support-lead@techcorp.com"
    )
]


def get_example_tickets() -> list[Ticket]:
    """Return list of example tickets."""
    return EXAMPLE_TICKETS
