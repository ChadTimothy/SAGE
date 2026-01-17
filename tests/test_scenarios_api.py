"""Tests for SAGE Scenarios API endpoints.

Note: Fixtures for test_graph, client, test_learner, test_session, auth_headers,
and other_auth_headers are provided by conftest.py
"""

import pytest

from sage.graph.models import ScenarioDifficulty, StoredScenario


@pytest.fixture
def preset_scenario(test_graph):
    """Create a preset scenario."""
    scenario = StoredScenario(
        title="Client Pricing Negotiation",
        description="Practice handling pricing objections",
        sage_role="A potential client interested in your services but pushing back on price",
        user_role="A freelance designer trying to close a deal at your stated rate",
        category="business",
        difficulty=ScenarioDifficulty.MEDIUM,
        is_preset=True,
        learner_id=None,
    )
    return test_graph.store.create_scenario(scenario)


@pytest.fixture
def user_scenario(test_graph, test_learner):
    """Create a user-owned scenario."""
    scenario = StoredScenario(
        title="Technical Interview",
        description="Practice explaining technical concepts",
        sage_role="A hiring manager asking technical questions",
        user_role="A software developer interviewing for a senior position",
        category="career",
        difficulty=ScenarioDifficulty.HARD,
        is_preset=False,
        learner_id=test_learner.id,
    )
    return test_graph.store.create_scenario(scenario)


class TestPresetScenarios:
    """Test preset scenario endpoints (no auth required).

    Note: The graph store seeds preset scenarios on initialization,
    so we test that the presets exist and are accessible.
    """

    def test_list_preset_scenarios(self, client):
        """Test listing preset scenarios returns seeded presets."""
        response = client.get("/api/scenarios/presets")
        assert response.status_code == 200
        data = response.json()
        # Should have at least 6 seeded presets
        assert data["total"] >= 6
        assert len(data["scenarios"]) >= 6
        # All should be presets
        assert all(s["is_preset"] for s in data["scenarios"])
        assert all(s["learner_id"] is None for s in data["scenarios"])

    def test_preset_scenarios_includes_added_preset(self, client, preset_scenario):
        """Test that new preset scenarios are included in list."""
        response = client.get("/api/scenarios/presets")
        assert response.status_code == 200
        data = response.json()
        # Should include our fixture + seeded presets
        assert data["total"] >= 7
        # Find our fixture scenario
        ids = [s["id"] for s in data["scenarios"]]
        assert preset_scenario.id in ids

    def test_preset_scenarios_excludes_user_scenarios(
        self, client, preset_scenario, user_scenario
    ):
        """Test that preset endpoint only returns presets."""
        response = client.get("/api/scenarios/presets")
        assert response.status_code == 200
        data = response.json()
        assert all(s["is_preset"] for s in data["scenarios"])
        # User scenario should not be in list
        ids = [s["id"] for s in data["scenarios"]]
        assert user_scenario.id not in ids


class TestListScenarios:
    """Test listing scenarios with authentication."""

    def test_list_scenarios_unauthorized(self, client):
        """Test listing scenarios without auth."""
        response = client.get("/api/scenarios")
        assert response.status_code == 401

    def test_list_scenarios_with_presets(
        self, client, auth_headers, preset_scenario, user_scenario
    ):
        """Test listing all scenarios including presets."""
        response = client.get(
            "/api/scenarios", headers=auth_headers, params={"include_presets": True}
        )
        assert response.status_code == 200
        data = response.json()
        # Should include seeded presets + fixture preset + user scenario
        assert data["total"] >= 8
        # Check both fixture scenarios are in results
        ids = [s["id"] for s in data["scenarios"]]
        assert preset_scenario.id in ids
        assert user_scenario.id in ids

    def test_list_scenarios_without_presets(
        self, client, auth_headers, preset_scenario, user_scenario
    ):
        """Test listing only user scenarios."""
        response = client.get(
            "/api/scenarios", headers=auth_headers, params={"include_presets": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["scenarios"][0]["is_preset"] is False


class TestGetScenario:
    """Test getting a specific scenario."""

    def test_get_scenario_unauthorized(self, client, preset_scenario):
        """Test getting scenario without auth."""
        response = client.get(f"/api/scenarios/{preset_scenario.id}")
        assert response.status_code == 401

    def test_get_preset_scenario(self, client, auth_headers, preset_scenario):
        """Test getting a preset scenario."""
        response = client.get(
            f"/api/scenarios/{preset_scenario.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == preset_scenario.id
        assert data["title"] == "Client Pricing Negotiation"
        assert data["is_preset"] is True

    def test_get_user_scenario(self, client, auth_headers, user_scenario):
        """Test getting a user-owned scenario."""
        response = client.get(f"/api/scenarios/{user_scenario.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_scenario.id
        assert data["is_preset"] is False

    def test_get_scenario_not_found(self, client, auth_headers):
        """Test getting a non-existent scenario."""
        response = client.get("/api/scenarios/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404

    def test_get_other_users_scenario_forbidden(
        self, client, user_scenario, other_auth_headers
    ):
        """Test accessing another user's scenario."""
        response = client.get(
            f"/api/scenarios/{user_scenario.id}", headers=other_auth_headers
        )
        assert response.status_code == 403


class TestCreateScenario:
    """Test creating scenarios."""

    def test_create_scenario_unauthorized(self, client):
        """Test creating scenario without auth."""
        response = client.post(
            "/api/scenarios",
            json={
                "title": "New Scenario",
                "sage_role": "Test sage role",
                "user_role": "Test user role",
            },
        )
        assert response.status_code == 401

    def test_create_scenario(self, client, auth_headers, test_learner):
        """Test creating a custom scenario."""
        response = client.post(
            "/api/scenarios",
            headers=auth_headers,
            json={
                "title": "Job Interview Practice",
                "description": "Practice answering behavioral questions",
                "sage_role": "HR interviewer",
                "user_role": "Job candidate",
                "category": "career",
                "difficulty": "hard",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Job Interview Practice"
        assert data["sage_role"] == "HR interviewer"
        assert data["user_role"] == "Job candidate"
        assert data["is_preset"] is False
        assert data["learner_id"] == test_learner.id
        assert data["times_used"] == 0

    def test_create_scenario_minimal(self, client, auth_headers, test_learner):
        """Test creating scenario with minimal required fields."""
        response = client.post(
            "/api/scenarios",
            headers=auth_headers,
            json={
                "title": "Quick Practice",
                "sage_role": "Coach",
                "user_role": "Student",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Quick Practice"
        assert data["difficulty"] == "medium"  # Default value

    def test_create_scenario_invalid_data(self, client, auth_headers):
        """Test creating scenario with missing required fields."""
        response = client.post(
            "/api/scenarios",
            headers=auth_headers,
            json={
                "title": "Missing Roles",
            },
        )
        assert response.status_code == 422  # Validation error


class TestUpdateScenario:
    """Test updating scenarios."""

    def test_update_scenario_unauthorized(self, client, user_scenario):
        """Test updating scenario without auth."""
        response = client.patch(
            f"/api/scenarios/{user_scenario.id}",
            json={"title": "Updated Title"},
        )
        assert response.status_code == 401

    def test_update_user_scenario(self, client, auth_headers, user_scenario):
        """Test updating a user-owned scenario."""
        response = client.patch(
            f"/api/scenarios/{user_scenario.id}",
            headers=auth_headers,
            json={
                "title": "Updated Interview Practice",
                "difficulty": "easy",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Interview Practice"
        assert data["difficulty"] == "easy"
        # Unchanged fields remain
        assert data["sage_role"] == user_scenario.sage_role

    def test_update_preset_scenario_forbidden(
        self, client, auth_headers, preset_scenario
    ):
        """Test updating a preset scenario is forbidden."""
        response = client.patch(
            f"/api/scenarios/{preset_scenario.id}",
            headers=auth_headers,
            json={"title": "Should Not Work"},
        )
        assert response.status_code == 403

    def test_update_scenario_not_found(self, client, auth_headers):
        """Test updating a non-existent scenario."""
        response = client.patch(
            "/api/scenarios/nonexistent-id",
            headers=auth_headers,
            json={"title": "Should Not Work"},
        )
        assert response.status_code == 404

    def test_update_other_users_scenario_forbidden(
        self, client, user_scenario, other_auth_headers
    ):
        """Test updating another user's scenario."""
        response = client.patch(
            f"/api/scenarios/{user_scenario.id}",
            headers=other_auth_headers,
            json={"title": "Should Not Work"},
        )
        assert response.status_code == 403


class TestDeleteScenario:
    """Test deleting scenarios."""

    def test_delete_scenario_unauthorized(self, client, user_scenario):
        """Test deleting scenario without auth."""
        response = client.delete(f"/api/scenarios/{user_scenario.id}")
        assert response.status_code == 401

    def test_delete_user_scenario(self, client, auth_headers, user_scenario, test_graph):
        """Test deleting a user-owned scenario."""
        response = client.delete(
            f"/api/scenarios/{user_scenario.id}", headers=auth_headers
        )
        assert response.status_code == 204

        # Verify deletion
        deleted = test_graph.store.get_scenario(user_scenario.id)
        assert deleted is None

    def test_delete_preset_scenario_forbidden(
        self, client, auth_headers, preset_scenario
    ):
        """Test deleting a preset scenario is forbidden."""
        response = client.delete(
            f"/api/scenarios/{preset_scenario.id}", headers=auth_headers
        )
        assert response.status_code == 403

    def test_delete_scenario_not_found(self, client, auth_headers):
        """Test deleting a non-existent scenario."""
        response = client.delete("/api/scenarios/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_other_users_scenario_forbidden(
        self, client, user_scenario, other_auth_headers
    ):
        """Test deleting another user's scenario."""
        response = client.delete(
            f"/api/scenarios/{user_scenario.id}", headers=other_auth_headers
        )
        assert response.status_code == 403


class TestScenarioFields:
    """Test scenario field validation and responses."""

    def test_scenario_response_fields(self, client, auth_headers, user_scenario):
        """Test all expected fields are in response."""
        response = client.get(
            f"/api/scenarios/{user_scenario.id}", headers=auth_headers
        )
        data = response.json()

        expected_fields = [
            "id",
            "title",
            "description",
            "sage_role",
            "user_role",
            "category",
            "difficulty",
            "is_preset",
            "learner_id",
            "times_used",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_scenario_difficulty_values(self, client, auth_headers):
        """Test all difficulty values are accepted."""
        for difficulty in ["easy", "medium", "hard"]:
            response = client.post(
                "/api/scenarios",
                headers=auth_headers,
                json={
                    "title": f"{difficulty.title()} Scenario",
                    "sage_role": "Test role",
                    "user_role": "Test role",
                    "difficulty": difficulty,
                },
            )
            assert response.status_code == 201
            assert response.json()["difficulty"] == difficulty

    def test_scenario_invalid_difficulty(self, client, auth_headers):
        """Test invalid difficulty value is rejected."""
        response = client.post(
            "/api/scenarios",
            headers=auth_headers,
            json={
                "title": "Invalid Difficulty Scenario",
                "sage_role": "Test role",
                "user_role": "Test role",
                "difficulty": "impossible",
            },
        )
        assert response.status_code == 422
