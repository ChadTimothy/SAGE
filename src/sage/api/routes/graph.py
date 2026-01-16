"""Graph-related API routes including voice filter extraction."""

from typing import Any

from fastapi import APIRouter, Depends
from openai import OpenAI
from pydantic import BaseModel

from sage.core.config import get_settings
from sage.orchestration.intent_extractor import SemanticIntentExtractor

from ..auth import CurrentUser, get_current_user

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
async def extract_filters(
    request: FilterRequest,
    user: CurrentUser = Depends(get_current_user),
) -> FilterResponse:
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

    if result.data.get("reset_filters"):
        filters = {
            "showProvenOnly": False,
            "showConcepts": True,
            "showOutcomes": True,
            "textFilter": "",
            "resetFilters": True,
        }
    else:
        # Map snake_case API fields to camelCase frontend fields
        field_mapping = {
            "show_proven_only": "showProvenOnly",
            "show_concepts": "showConcepts",
            "show_outcomes": "showOutcomes",
            "text_filter": "textFilter",
        }
        filters = {
            camel: result.data[snake]
            for snake, camel in field_mapping.items()
            if snake in result.data
        }

    return FilterResponse(
        success=True,
        filters=filters,
        confidence=result.confidence,
    )
