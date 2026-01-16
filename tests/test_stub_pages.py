"""
Tests for stub pages (#64) - Settings, Goals, Proofs

These tests document the page requirements and ensure
the stub pages are properly structured.
"""

import pytest
from pathlib import Path


@pytest.fixture
def web_app_dir() -> Path:
    """Get the web app directory."""
    return Path(__file__).parent.parent / "web" / "app"


@pytest.fixture
def sidebar_content() -> str:
    """Get sidebar component content."""
    sidebar_path = (
        Path(__file__).parent.parent / "web" / "components" / "layout" / "Sidebar.tsx"
    )
    return sidebar_path.read_text()


class TestStubPageStructure:
    """Test that stub pages exist and have proper structure."""

    @pytest.mark.parametrize("page_name", ["settings", "goals", "proofs"])
    def test_page_exists(self, web_app_dir: Path, page_name: str) -> None:
        """Each stub page should exist."""
        page_file = web_app_dir / page_name / "page.tsx"
        assert page_file.exists(), f"{page_name.title()} page.tsx should exist"


class TestStubPageContent:
    """Test that stub pages have appropriate content."""

    @pytest.mark.parametrize("page_name", ["settings", "goals", "proofs"])
    def test_page_has_coming_soon(self, web_app_dir: Path, page_name: str) -> None:
        """Each stub page should indicate it's coming soon."""
        content = (web_app_dir / page_name / "page.tsx").read_text()
        assert "Coming Soon" in content or "StubPage" in content

    def test_settings_lists_planned_features(self, web_app_dir: Path) -> None:
        """Settings page should list planned features."""
        content = (web_app_dir / "settings" / "page.tsx").read_text()
        assert "Dark mode" in content
        assert "Voice preferences" in content
        assert "API configuration" in content
        assert "Learner profile" in content

    def test_goals_lists_planned_features(self, web_app_dir: Path) -> None:
        """Goals page should list planned features."""
        content = (web_app_dir / "goals" / "page.tsx").read_text()
        assert "learning goals" in content
        assert "completed outcomes" in content

    def test_proofs_lists_planned_features(self, web_app_dir: Path) -> None:
        """Proofs page should list planned features."""
        content = (web_app_dir / "proofs" / "page.tsx").read_text()
        assert "earned proofs" in content
        assert "confidence" in content


class TestSidebarNavigation:
    """Test that sidebar navigation links to stub pages."""

    @pytest.mark.parametrize("page_name", ["settings", "goals", "proofs"])
    def test_sidebar_links_to_page(self, sidebar_content: str, page_name: str) -> None:
        """Sidebar should have link to each stub page."""
        assert f'href: "/{page_name}"' in sidebar_content
