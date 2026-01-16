"""
Tests for stub pages (#64) - Settings, Goals, Proofs

These tests document the page requirements and ensure
the stub pages are properly structured.
"""

import pytest
from pathlib import Path


class TestStubPageStructure:
    """Test that stub pages exist and have proper structure."""

    @pytest.fixture
    def web_app_dir(self) -> Path:
        """Get the web app directory."""
        return Path(__file__).parent.parent / "web" / "app"

    def test_settings_page_exists(self, web_app_dir: Path) -> None:
        """Settings page should exist at /settings."""
        settings_page = web_app_dir / "settings" / "page.tsx"
        assert settings_page.exists(), "Settings page.tsx should exist"

    def test_goals_page_exists(self, web_app_dir: Path) -> None:
        """Goals page should exist at /goals."""
        goals_page = web_app_dir / "goals" / "page.tsx"
        assert goals_page.exists(), "Goals page.tsx should exist"

    def test_proofs_page_exists(self, web_app_dir: Path) -> None:
        """Proofs page should exist at /proofs."""
        proofs_page = web_app_dir / "proofs" / "page.tsx"
        assert proofs_page.exists(), "Proofs page.tsx should exist"


class TestStubPageContent:
    """Test that stub pages have appropriate content."""

    @pytest.fixture
    def web_app_dir(self) -> Path:
        """Get the web app directory."""
        return Path(__file__).parent.parent / "web" / "app"

    def test_settings_page_has_coming_soon(self, web_app_dir: Path) -> None:
        """Settings page should indicate it's coming soon."""
        content = (web_app_dir / "settings" / "page.tsx").read_text()
        assert "Coming Soon" in content

    def test_goals_page_has_coming_soon(self, web_app_dir: Path) -> None:
        """Goals page should indicate it's coming soon."""
        content = (web_app_dir / "goals" / "page.tsx").read_text()
        assert "Coming Soon" in content

    def test_proofs_page_has_coming_soon(self, web_app_dir: Path) -> None:
        """Proofs page should indicate it's coming soon."""
        content = (web_app_dir / "proofs" / "page.tsx").read_text()
        assert "Coming Soon" in content

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

    @pytest.fixture
    def sidebar_content(self) -> str:
        """Get sidebar component content."""
        sidebar_path = (
            Path(__file__).parent.parent
            / "web"
            / "components"
            / "layout"
            / "Sidebar.tsx"
        )
        return sidebar_path.read_text()

    def test_sidebar_links_to_settings(self, sidebar_content: str) -> None:
        """Sidebar should have link to /settings."""
        assert 'href: "/settings"' in sidebar_content

    def test_sidebar_links_to_goals(self, sidebar_content: str) -> None:
        """Sidebar should have link to /goals."""
        assert 'href: "/goals"' in sidebar_content

    def test_sidebar_links_to_proofs(self, sidebar_content: str) -> None:
        """Sidebar should have link to /proofs."""
        assert 'href: "/proofs"' in sidebar_content
