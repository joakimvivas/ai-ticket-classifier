"""
FastAPI application for ticket classification.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.models import Ticket, TicketWithClassification
from app.classifier import TicketClassifier
from app.examples import get_example_tickets
from app.services.vector_service import vector_service
from app.inngest.client import inngest_client
import inngest

# Load environment variables from .env file
load_dotenv()

# Templates configuration
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Initialize FastAPI
app = FastAPI(
    title="Customer Support Ticket Classifier",
    description="AI-powered ticket classification using GPT-4o-mini + Qdrant + Inngest",
    version="0.2.0"
)

# Initialize classifier
try:
    classifier = TicketClassifier()
except ValueError as e:
    print(f"⚠️  Warning: {e}")
    print("Set OPENAI_API_KEY environment variable to enable classification")
    classifier = None


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("🚀 Starting AI Ticket Classifier...")

    # Initialize vector service
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    vector_service.qdrant_url = qdrant_url
    await vector_service.initialize()
    print("✅ Services initialized")


# Register Inngest endpoint
import inngest.fast_api
from app.inngest.functions import classify_ticket_fn, classify_ticket_batch_fn

serve_origin = "http://host.docker.internal:8000" if os.getenv("DEBUG", "true").lower() == "true" else None

inngest.fast_api.serve(
    app,
    inngest_client,
    [classify_ticket_fn, classify_ticket_batch_fn],
    serve_origin=serve_origin,
    serve_path="/api/inngest"
)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Welcome page with API documentation."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "classifier_ready": classifier is not None
    }


@app.get("/examples", response_class=HTMLResponse)
async def examples_page(request: Request):
    """
    Display example tickets in HTML format.

    Returns:
        HTML page showing all example tickets
    """
    tickets = get_example_tickets()
    return templates.TemplateResponse("examples.html", {
        "request": request,
        "tickets": tickets
    })


@app.get("/api/examples")
async def get_examples() -> list[Ticket]:
    """
    Get 5 example support tickets (without classification) as JSON.

    Returns:
        List of 5 example tickets
    """
    return get_example_tickets()


@app.post("/classify")
async def classify_ticket(ticket: Ticket) -> TicketWithClassification:
    """
    Classify a single support ticket.

    Args:
        ticket: Ticket to classify

    Returns:
        Ticket with classification results

    Raises:
        HTTPException: If classifier is not initialized or classification fails
    """
    if classifier is None:
        raise HTTPException(
            status_code=503,
            detail="Classifier not initialized. Set OPENAI_API_KEY environment variable."
        )

    try:
        classification = classifier.classify(ticket)
        return TicketWithClassification(
            ticket=ticket,
            classification=classification
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Classification failed: {str(e)}"
        )


@app.get("/classify-examples")
async def classify_examples() -> list[TicketWithClassification]:
    """
    Classify all 5 example tickets (JSON response).

    Returns:
        List of tickets with classifications

    Raises:
        HTTPException: If classifier is not initialized or classification fails
    """
    if classifier is None:
        raise HTTPException(
            status_code=503,
            detail="Classifier not initialized. Set OPENAI_API_KEY environment variable."
        )

    tickets = get_example_tickets()
    results = []

    for ticket in tickets:
        try:
            classification = classifier.classify(ticket)
            results.append(TicketWithClassification(
                ticket=ticket,
                classification=classification
            ))
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Classification failed for ticket {ticket.id}: {str(e)}"
            )

    return results


@app.get("/classify-examples-view", response_class=HTMLResponse)
async def classify_examples_view(request: Request, save_to_qdrant: bool = True):
    """
    Classify all 5 example tickets and display in HTML.

    Optionally saves to Qdrant for semantic search (enabled by default).

    Args:
        save_to_qdrant: Whether to save classified tickets to Qdrant (default: True)

    Returns:
        HTML page with classification results
    """
    if classifier is None:
        raise HTTPException(
            status_code=503,
            detail="Classifier not initialized. Set OPENAI_API_KEY environment variable."
        )

    tickets = get_example_tickets()
    results = []

    for ticket in tickets:
        try:
            classification = classifier.classify(ticket)

            # Save to Qdrant if enabled
            if save_to_qdrant:
                try:
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
                    print(f"✅ Saved {ticket.id} to Qdrant")
                except Exception as vector_error:
                    print(f"⚠️  Failed to save {ticket.id} to Qdrant: {vector_error}")

            results.append(TicketWithClassification(
                ticket=ticket,
                classification=classification
            ))
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Classification failed for ticket {ticket.id}: {str(e)}"
            )

    return templates.TemplateResponse(
        "results.html",
        {"request": request, "results": results}
    )


@app.post("/api/classify-async")
async def classify_async(ticket: Ticket):
    """
    Classify a single ticket asynchronously using Inngest.

    Returns immediately with job ID, processing happens in background.
    """
    if classifier is None:
        raise HTTPException(
            status_code=503,
            detail="Classifier not initialized. Set OPENAI_API_KEY environment variable."
        )

    try:
        # Send event to Inngest
        event = inngest.Event(
            name="ticket/classify",
            data={
                "ticket_id": ticket.id,
                "subject": ticket.subject,
                "description": ticket.description,
                "customer_email": ticket.customer_email
            }
        )
        await inngest_client.send(event)

        return {
            "status": "queued",
            "ticket_id": ticket.id,
            "message": "Ticket classification queued for background processing"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue classification: {str(e)}"
        )


@app.post("/api/classify-examples-async")
async def classify_examples_async():
    """
    Classify all 5 example tickets asynchronously using Inngest + Qdrant.

    Returns immediately, processing happens in background with Inngest.
    Results are stored in Qdrant for semantic search.
    """
    if classifier is None:
        raise HTTPException(
            status_code=503,
            detail="Classifier not initialized. Set OPENAI_API_KEY environment variable."
        )

    try:
        tickets = get_example_tickets()

        # Prepare ticket data for batch processing
        tickets_data = [
            {
                "ticket_id": ticket.id,
                "subject": ticket.subject,
                "description": ticket.description,
                "customer_email": ticket.customer_email
            }
            for ticket in tickets
        ]

        # Send batch event to Inngest
        import uuid
        job_id = f"batch_{uuid.uuid4().hex[:8]}"

        event = inngest.Event(
            name="ticket/classify.batch",
            data={
                "job_id": job_id,
                "tickets": tickets_data
            }
        )
        await inngest_client.send(event)

        return {
            "status": "queued",
            "job_id": job_id,
            "ticket_count": len(tickets),
            "message": f"Batch classification of {len(tickets)} tickets queued. Check Inngest UI at http://localhost:8288",
            "inngest_url": "http://localhost:8288"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue batch classification: {str(e)}"
        )


@app.get("/api/search-similar")
async def search_similar(query: str, limit: int = 5, urgency: str = None):
    """
    Search for similar tickets using Qdrant vector search.

    Args:
        query: Search query text
        limit: Maximum number of results (default: 5)
        urgency: Optional filter by urgency level
    """
    try:
        results = await vector_service.search_similar_tickets(
            query=query,
            limit=limit,
            urgency_filter=urgency
        )

        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@app.get("/api/vector-stats")
async def vector_stats():
    """Get statistics about the vector database"""
    try:
        stats = await vector_service.get_collection_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(e)}"
        )


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """Semantic search page for finding similar tickets"""
    return templates.TemplateResponse("search.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
