"""
Inngest background functions for ticket classification.
"""

import logging
import inngest
from app.inngest.client import inngest_client
from app.classifier import TicketClassifier
from app.models import Ticket
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)


@inngest_client.create_function(
    fn_id="classify-ticket",
    trigger=inngest.TriggerEvent(event="ticket/classify")
)
async def classify_ticket_fn(ctx, step):
    """
    Background function to classify a single ticket

    Triggered by: ticket/classify event
    Payload: {ticket_id, subject, description, customer_email}
    """

    # Step 1: Extract ticket data
    ticket_data = await step.run(
        "extract-ticket-data",
        lambda: ctx.event.data
    )

    # Step 2: Classify ticket
    async def classify():
        try:
            classifier = TicketClassifier()
            ticket = Ticket(
                id=ticket_data["ticket_id"],
                subject=ticket_data["subject"],
                description=ticket_data["description"],
                customer_email=ticket_data.get("customer_email")
            )

            classification = classifier.classify(ticket)
            logger.info(f"✅ Classified ticket {ticket.id}: {classification.urgency}")

            return {
                "ticket_id": ticket.id,
                "classification": {
                    "urgency": classification.urgency,
                    "intent": classification.intent,
                    "product": classification.product,
                    "confidence": classification.confidence,
                    "reasoning": classification.reasoning
                }
            }
        except Exception as e:
            logger.error(f"❌ Error classifying ticket: {e}")
            raise

    result = await step.run("classify-with-gpt", classify)

    # Step 3: Store in vector database
    async def store_vector():
        try:
            await vector_service.add_ticket(
                ticket_id=ticket_data["ticket_id"],
                subject=ticket_data["subject"],
                description=ticket_data["description"],
                classification=result["classification"]
            )
            logger.info(f"✅ Stored ticket {ticket_data['ticket_id']} in Qdrant")
            return {"stored": True}
        except Exception as e:
            logger.error(f"⚠️  Failed to store in Qdrant: {e}")
            return {"stored": False, "error": str(e)}

    await step.run("store-in-qdrant", store_vector)

    return result


@inngest_client.create_function(
    fn_id="classify-ticket-batch",
    trigger=inngest.TriggerEvent(event="ticket/classify.batch")
)
async def classify_ticket_batch_fn(ctx, step):
    """
    Background function to classify multiple tickets

    Triggered by: ticket/classify.batch event
    Payload: {tickets: [{ticket_id, subject, description}]}
    """

    tickets_data = ctx.event.data["tickets"]

    # Process each ticket
    results = []
    for idx, ticket_data in enumerate(tickets_data):
        async def classify_one():
            try:
                classifier = TicketClassifier()
                ticket = Ticket(
                    id=ticket_data["ticket_id"],
                    subject=ticket_data["subject"],
                    description=ticket_data["description"],
                    customer_email=ticket_data.get("customer_email")
                )

                classification = classifier.classify(ticket)

                # Store in Qdrant
                await vector_service.add_ticket(
                    ticket_id=ticket.id,
                    subject=ticket.subject,
                    description=ticket.description,
                    classification={
                        "urgency": classification.urgency,
                        "intent": classification.intent,
                        "product": classification.product,
                        "confidence": classification.confidence,
                        "reasoning": classification.reasoning
                    }
                )

                return {
                    "ticket_id": ticket.id,
                    "classification": {
                        "urgency": classification.urgency,
                        "intent": classification.intent,
                        "product": classification.product,
                        "confidence": classification.confidence
                    }
                }
            except Exception as e:
                logger.error(f"❌ Error classifying ticket {ticket_data['ticket_id']}: {e}")
                return {"ticket_id": ticket_data["ticket_id"], "error": str(e)}

        result = await step.run(f"classify-ticket-{idx}", classify_one)
        results.append(result)

    return {
        "total": len(tickets_data),
        "processed": len(results),
        "results": results
    }
