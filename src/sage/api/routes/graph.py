"""Graph-related API routes including voice filter extraction."""

from typing import Any

from fastapi import APIRouter
from openai import OpenAI
from pydantic import BaseModel

from sage.core.config import get_settings
from sage.orchestration.intent_extractor import SemanticIntentExtractor

router = APIRouter(prefix="/api/graph", tags=["graph"])


class FilterRequest(BaseModel):
    """Request to extract filter intent from text."""

    text: str


class FilterResponse(BaseModel):
    """Response with extracted filter state."""

    success: bool
    filters: dict[str, Any] | None = None
    confidence: float = 0.0


@router.post("/extract-filters", response_model=FilterResponse)
async def extract_filters(request: FilterRequest) -> FilterResponse:
    """Extract graph filter intent from natural language text.

    Used by the graph page to interpret voice commands like:
    - "Show only proven concepts"
    - "Hide outcomes"
    - "Filter by pricing"
    - "Show everything"
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    extractor = SemanticIntentExtractor(client, model=settings.llm_model)

    result = extractor.extract_sync(request.text)

    if result.intent != "filter_graph" or result.confidence < 0.5:
        return FilterResponse(success=False, confidence=result.confidence)

    # Map extracted data to filter state
    filters: dict[str, Any] = {}

    if result.data.get("reset_filters"):
        # Reset to default state
        filters = {
            "showProvenOnly": False,
            "showConcepts": True,
            "showOutcomes": True,
            "textFilter": "",
            "resetFilters": True,
        }
    else:
        # Apply individual filter changes
        if "show_proven_only" in result.data:
            filters["showProvenOnly"] = result.data["show_proven_only"]
        if "show_concepts" in result.data:
            filters["showConcepts"] = result.data["show_concepts"]
        if "show_outcomes" in result.data:
            filters["showOutcomes"] = result.data["show_outcomes"]
        if "text_filter" in result.data:
            filters["textFilter"] = result.data["text_filter"]

    return FilterResponse(
        success=True,
        filters=filters,
        confidence=result.confidence,
    )
