"""
FastAPI application for ticket classification.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.models import Ticket, TicketWithClassification
from app.classifier import TicketClassifier
from app.examples import get_example_tickets

# Load environment variables from .env file
load_dotenv()

# Templates configuration
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Initialize FastAPI
app = FastAPI(
    title="Customer Support Ticket Classifier",
    description="AI-powered ticket classification using GPT-4o-mini",
    version="0.1.0"
)

# Initialize classifier
try:
    classifier = TicketClassifier()
except ValueError as e:
    print(f"⚠️  Warning: {e}")
    print("Set OPENAI_API_KEY environment variable to enable classification")
    classifier = None


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


@app.get("/examples")
async def get_examples() -> list[Ticket]:
    """
    Get 5 example support tickets (without classification).

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
async def classify_examples_view(request: Request):
    """
    Classify all 5 example tickets and display in HTML.

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
