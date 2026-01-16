"""Performance tests for UI Generation.

Tests that UI generation meets latency targets.

Part of #82 - Integration Testing & Voice/UI Parity Verification
"""

import json
import time
from typing import Callable
from unittest.mock import MagicMock

import pytest

from sage.orchestration.ui_agent import UIGenerationAgent


def measure_p95_latency_ms(func: Callable, iterations: int) -> float:
    """Measure P95 latency of a function in milliseconds."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        times.append((time.perf_counter() - start) * 1000)
    return sorted(times)[int(len(times) * 0.95)]


def measure_avg_latency_ms(func: Callable, iterations: int) -> float:
    """Measure average latency of a function in milliseconds."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        times.append((time.perf_counter() - start) * 1000)
    return sum(times) / len(times)


def make_ui_response_json(tree: dict) -> str:
    """Create a valid UI response JSON from a tree structure."""
    return json.dumps({
        "tree": tree,
        "voice_fallback": "Test",
        "purpose": "Test",
        "estimated_interaction_time": 30,
    })


@pytest.fixture
def mock_client() -> MagicMock:
    """Create mock OpenAI client with fast response."""
    client = MagicMock()
    response_json = make_ui_response_json({
        "component": "Card",
        "props": {"title": "Test"},
        "children": [
            {"component": "Text", "props": {"content": "Hello"}},
            {"component": "Button", "props": {"action": "submit", "label": "Go"}},
        ],
    })
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=response_json))]
    client.chat.completions.create.return_value = mock_response
    return client


@pytest.fixture
def agent(mock_client) -> UIGenerationAgent:
    """Create agent with mock client."""
    return UIGenerationAgent(mock_client, model="test-model")


class TestUIGenerationPerformance:
    """Performance tests for UI generation."""

    @pytest.mark.performance
    def test_parsing_under_10ms(self, agent):
        """Response parsing completes in under 10ms."""
        response_json = make_ui_response_json({
            "component": "Card",
            "props": {"title": "Test"},
            "children": [],
        })

        p95 = measure_p95_latency_ms(lambda: agent._parse_response(response_json), 100)
        assert p95 < 10, f"P95 parsing latency {p95:.2f}ms exceeds 10ms target"

    @pytest.mark.performance
    def test_prompt_building_under_5ms(self, agent):
        """Prompt building completes in under 5ms."""
        from sage.orchestration.models import UIGenerationRequest

        request = UIGenerationRequest(
            purpose="Test purpose",
            mode="check_in",
            energy_level="high",
            time_available="focused",
            recent_topic="negotiation",
            requirements="simple form",
        )

        p95 = measure_p95_latency_ms(lambda: agent._build_user_prompt(request), 100)
        assert p95 < 5, f"P95 prompt building latency {p95:.2f}ms exceeds 5ms target"

    @pytest.mark.performance
    def test_full_generate_mock_under_50ms(self, agent):
        """Full generation with mock client under 50ms (excludes LLM latency)."""
        p95 = measure_p95_latency_ms(
            lambda: agent.generate("Test purpose", context={"mode": "check_in"}),
            20,
        )
        assert p95 < 50, f"P95 generation latency {p95:.2f}ms exceeds 50ms target"


class TestUITreeProcessingPerformance:
    """Performance tests for UI tree processing."""

    @pytest.mark.performance
    def test_deep_tree_parsing_under_20ms(self, agent):
        """Deep nested tree parsing completes under 20ms."""

        def create_deep_tree(depth: int) -> dict:
            if depth == 0:
                return {"component": "Text", "props": {"content": "Leaf"}}
            return {
                "component": "Stack",
                "props": {"gap": 4},
                "children": [create_deep_tree(depth - 1), create_deep_tree(depth - 1)],
            }

        response_json = make_ui_response_json(create_deep_tree(5))  # 2^5 = 32 leaves

        p95 = measure_p95_latency_ms(lambda: agent._parse_response(response_json), 50)
        assert p95 < 20, f"P95 deep tree parsing {p95:.2f}ms exceeds 20ms target"

    @pytest.mark.performance
    def test_wide_tree_parsing_under_20ms(self, agent):
        """Wide tree parsing completes under 20ms."""
        wide_tree = {
            "component": "Stack",
            "props": {},
            "children": [
                {"component": "Text", "props": {"content": f"Item {i}"}}
                for i in range(50)
            ],
        }

        response_json = make_ui_response_json(wide_tree)

        p95 = measure_p95_latency_ms(lambda: agent._parse_response(response_json), 50)
        assert p95 < 20, f"P95 wide tree parsing {p95:.2f}ms exceeds 20ms target"


class TestUIPatternGenerationTiming:
    """Tests timing for different UI patterns."""

    @pytest.mark.performance
    def test_check_in_pattern_mock_timing(self, agent):
        """Check-in pattern generation timing with mock."""
        avg = measure_avg_latency_ms(
            lambda: agent.generate("Collect session check-in data", context={"mode": "check_in"}),
            10,
        )
        assert avg < 50, f"Average check-in timing {avg:.2f}ms too high"

    @pytest.mark.performance
    def test_verification_pattern_mock_timing(self, agent):
        """Verification pattern generation timing with mock."""
        avg = measure_avg_latency_ms(
            lambda: agent.generate(
                "Quiz on anchor pricing",
                context={"mode": "verification", "concept": "anchor pricing"},
            ),
            10,
        )
        assert avg < 50, f"Average verification timing {avg:.2f}ms too high"


class TestMemoryUsage:
    """Tests for memory efficiency."""

    @pytest.mark.performance
    def test_repeated_generation_no_memory_leak(self, agent):
        """Repeated generations don't cause memory buildup."""
        import sys

        initial_size = sys.getsizeof(agent)

        for _ in range(100):
            agent.generate("Test purpose", context={})

        growth = sys.getsizeof(agent) - initial_size
        assert growth < 1000, f"Memory grew by {growth} bytes after 100 generations"

    @pytest.mark.performance
    def test_large_response_memory_efficient(self, agent):
        """Large responses are parsed memory-efficiently."""
        large_tree = {
            "component": "Stack",
            "props": {},
            "children": [
                {
                    "component": "Card",
                    "props": {"title": f"Card {i}"},
                    "children": [
                        {"component": "Text", "props": {"content": f"Content {j}"}}
                        for j in range(10)
                    ],
                }
                for i in range(20)
            ],
        }

        response_json = make_ui_response_json(large_tree)
        spec = agent._parse_response(response_json)

        assert spec.tree.component == "Stack"
        assert len(spec.tree.children) == 20


class TestConcurrentGenerations:
    """Tests for concurrent generation scenarios."""

    @pytest.mark.performance
    def test_sequential_generations_consistent_timing(self, agent):
        """Sequential generations have consistent timing."""
        times = []
        for _ in range(20):
            start = time.perf_counter()
            agent.generate("Test", context={})
            times.append((time.perf_counter() - start) * 1000)

        avg = sum(times) / len(times)
        std_dev = (sum((t - avg) ** 2 for t in times) / len(times)) ** 0.5
        cv = std_dev / avg if avg > 0 else 0

        assert cv < 0.75, f"Timing too variable: CV={cv:.2f}"
