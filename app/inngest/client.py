"""
Inngest client configuration for ticket classification.
"""

import os
from inngest import Inngest

# Initialize Inngest client
inngest_client = Inngest(
    app_id="ticket-classifier",
    is_production=os.getenv("FASTAPI_ENV") == "production"
)
