"""Practice scenario API routes.

Provides CRUD operations for practice scenarios with authentication.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sage.graph.models import ScenarioDifficulty, StoredScenario

from ..auth import CurrentUser, get_current_user
from ..deps import Graph


router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ScenarioCreate(BaseModel):
    """Request to create a new scenario."""

    title: str
    description: Optional[str] = None
    sage_role: str
    user_role: str
    category: Optional[str] = None
    difficulty: ScenarioDifficulty = ScenarioDifficulty.MEDIUM


class ScenarioUpdate(BaseModel):
    """Request to update a scenario."""

    title: Optional[str] = None
    description: Optional[str] = None
    sage_role: Optional[str] = None
    user_role: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[ScenarioDifficulty] = None


class ScenarioResponse(BaseModel):
    """Response containing a scenario."""

    id: str
    title: str
    description: Optional[str] = None
    sage_role: str
    user_role: str
    category: Optional[str] = None
    difficulty: ScenarioDifficulty
    is_preset: bool
    learner_id: Optional[str] = None
    times_used: int


class ScenariosListResponse(BaseModel):
    """Response containing list of scenarios."""

    scenarios: list[ScenarioResponse]
    total: int


# =============================================================================
# Routes
# =============================================================================


@router.get("", response_model=ScenariosListResponse)
async def list_scenarios(
    graph: Graph,
    user: CurrentUser = Depends(get_current_user),
    include_presets: bool = True,
) -> ScenariosListResponse:
    """List all scenarios available to the current user."""
    scenarios = graph.store.get_scenarios_for_learner(
        user.learner_id, include_presets=include_presets
    )
    return ScenariosListResponse(
        scenarios=[_to_response(s) for s in scenarios],
        total=len(scenarios),
    )


@router.get("/presets", response_model=ScenariosListResponse)
async def list_preset_scenarios(
    graph: Graph,
) -> ScenariosListResponse:
    """List all preset scenarios (no auth required)."""
    scenarios = graph.store.get_preset_scenarios()
    return ScenariosListResponse(
        scenarios=[_to_response(s) for s in scenarios],
        total=len(scenarios),
    )


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: str,
    graph: Graph,
    user: CurrentUser = Depends(get_current_user),
) -> ScenarioResponse:
    """Get a specific scenario by ID."""
    scenario = graph.store.get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Allow access to preset scenarios or user's own scenarios
    if not scenario.is_preset and scenario.learner_id != user.learner_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _to_response(scenario)


@router.post("", response_model=ScenarioResponse, status_code=201)
async def create_scenario(
    data: ScenarioCreate,
    graph: Graph,
    user: CurrentUser = Depends(get_current_user),
) -> ScenarioResponse:
    """Create a new custom scenario for the current user."""
    scenario = StoredScenario(
        title=data.title,
        description=data.description,
        sage_role=data.sage_role,
        user_role=data.user_role,
        category=data.category,
        difficulty=data.difficulty,
        is_preset=False,
        learner_id=user.learner_id,
    )
    created = graph.store.create_scenario(scenario)
    return _to_response(created)


@router.patch("/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: str,
    data: ScenarioUpdate,
    graph: Graph,
    user: CurrentUser = Depends(get_current_user),
) -> ScenarioResponse:
    """Update a custom scenario (only the owner can update)."""
    scenario = graph.store.get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    if scenario.is_preset:
        raise HTTPException(status_code=403, detail="Cannot modify preset scenarios")

    if scenario.learner_id != user.learner_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Apply updates
    if data.title is not None:
        scenario.title = data.title
    if data.description is not None:
        scenario.description = data.description
    if data.sage_role is not None:
        scenario.sage_role = data.sage_role
    if data.user_role is not None:
        scenario.user_role = data.user_role
    if data.category is not None:
        scenario.category = data.category
    if data.difficulty is not None:
        scenario.difficulty = data.difficulty

    updated = graph.store.update_scenario(scenario)
    return _to_response(updated)


@router.delete("/{scenario_id}", status_code=204)
async def delete_scenario(
    scenario_id: str,
    graph: Graph,
    user: CurrentUser = Depends(get_current_user),
) -> None:
    """Delete a custom scenario (only the owner can delete)."""
    scenario = graph.store.get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    if scenario.is_preset:
        raise HTTPException(status_code=403, detail="Cannot delete preset scenarios")

    if scenario.learner_id != user.learner_id:
        raise HTTPException(status_code=403, detail="Access denied")

    deleted = graph.store.delete_scenario(scenario_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Scenario not found")


# =============================================================================
# Helpers
# =============================================================================


def _to_response(scenario: StoredScenario) -> ScenarioResponse:
    """Convert StoredScenario to API response."""
    return ScenarioResponse(
        id=scenario.id,
        title=scenario.title,
        description=scenario.description,
        sage_role=scenario.sage_role,
        user_role=scenario.user_role,
        category=scenario.category,
        difficulty=scenario.difficulty,
        is_preset=scenario.is_preset,
        learner_id=scenario.learner_id,
        times_used=scenario.times_used,
    )
