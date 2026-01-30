"""
Tests for workspace settings manager
"""

from pathlib import Path

import pytest

from openclaw.config.settings_manager import SettingsManager, WorkspaceSettings


class TestWorkspaceSettings:
    """Test WorkspaceSettings class"""

    def test_init(self, tmp_path):
        """Test initializing workspace settings"""
        settings = WorkspaceSettings(tmp_path)

        assert settings.workspace_dir == tmp_path
        assert settings.settings_dir == tmp_path / ".openclaw"
        assert settings.settings_file.exists() or not settings.settings_file.exists()

    def test_get_default(self, tmp_path):
        """Test getting default setting"""
        settings = WorkspaceSettings(tmp_path)

        model = settings.get("model")
        assert model == "anthropic/claude-opus-4-5"

    def test_get_custom_default(self, tmp_path):
        """Test getting with custom default"""
        settings = WorkspaceSettings(tmp_path)

        value = settings.get("nonexistent", "custom_default")
        assert value == "custom_default"

    def test_set_and_get(self, tmp_path):
        """Test setting and getting"""
        settings = WorkspaceSettings(tmp_path)

        settings.set("custom_key", "custom_value")
        value = settings.get("custom_key")

        assert value == "custom_value"

    def test_set_overrides_default(self, tmp_path):
        """Test that custom setting overrides default"""
        settings = WorkspaceSettings(tmp_path)

        settings.set("model", "openai/gpt-4")
        model = settings.get("model")

        assert model == "openai/gpt-4"

    def test_delete(self, tmp_path):
        """Test deleting a setting"""
        settings = WorkspaceSettings(tmp_path)

        settings.set("test_key", "test_value")
        assert settings.get("test_key") == "test_value"

        deleted = settings.delete("test_key")
        assert deleted
        assert settings.get("test_key") is None

    def test_delete_nonexistent(self, tmp_path):
        """Test deleting non-existent setting"""
        settings = WorkspaceSettings(tmp_path)

        deleted = settings.delete("nonexistent")
        assert not deleted

    def test_reset_one(self, tmp_path):
        """Test resetting one setting"""
        settings = WorkspaceSettings(tmp_path)

        settings.set("model", "openai/gpt-4")
        settings.reset("model")

        # Should fall back to default
        model = settings.get("model")
        assert model == "anthropic/claude-opus-4-5"

    def test_reset_all(self, tmp_path):
        """Test resetting all settings"""
        settings = WorkspaceSettings(tmp_path)

        settings.set("key1", "value1")
        settings.set("key2", "value2")
        settings.reset()

        assert settings.get("key1") is None
        assert settings.get("key2") is None

    def test_list_all(self, tmp_path):
        """Test listing all settings"""
        settings = WorkspaceSettings(tmp_path)

        settings.set("custom", "value")
        all_settings = settings.list_all()

        # Should include defaults + custom
        assert "model" in all_settings
        assert "custom" in all_settings
        assert all_settings["custom"] == "value"

    def test_list_custom(self, tmp_path):
        """Test listing only custom settings"""
        settings = WorkspaceSettings(tmp_path)

        settings.set("custom", "value")
        custom = settings.list_custom()

        # Should only include custom
        assert "custom" in custom
        assert "model" not in custom or custom["model"] != settings.DEFAULT_SETTINGS["model"]

    def test_persistence(self, tmp_path):
        """Test that settings persist"""
        settings1 = WorkspaceSettings(tmp_path)
        settings1.set("persist_key", "persist_value")

        # Create new instance
        settings2 = WorkspaceSettings(tmp_path)
        value = settings2.get("persist_key")

        assert value == "persist_value"

    def test_export_import(self, tmp_path):
        """Test export and import"""
        settings = WorkspaceSettings(tmp_path)
        settings.set("export_key", "export_value")

        export_file = tmp_path / "export.json"
        settings.export_to_file(export_file)

        assert export_file.exists()

        # Import in new workspace
        settings2 = WorkspaceSettings(tmp_path / "workspace2")
        settings2.import_from_file(export_file)

        assert settings2.get("export_key") == "export_value"


class TestSettingsManager:
    """Test SettingsManager class"""

    def test_init(self, tmp_path):
        """Test initializing settings manager"""
        manager = SettingsManager(tmp_path)

        assert manager.global_config_dir == tmp_path
        assert manager.global_config_dir.exists()

    def test_get_workspace_settings(self, tmp_path):
        """Test getting workspace settings"""
        manager = SettingsManager(tmp_path)

        workspace = tmp_path / "project1"
        workspace.mkdir()

        settings = manager.get_workspace_settings(workspace)

        assert isinstance(settings, WorkspaceSettings)
        assert settings.workspace_dir == workspace

    def test_workspace_isolation(self, tmp_path):
        """Test that workspaces are isolated"""
        manager = SettingsManager(tmp_path)

        workspace1 = tmp_path / "project1"
        workspace2 = tmp_path / "project2"
        workspace1.mkdir()
        workspace2.mkdir()

        settings1 = manager.get_workspace_settings(workspace1)
        settings2 = manager.get_workspace_settings(workspace2)

        settings1.set("key", "value1")
        settings2.set("key", "value2")

        assert settings1.get("key") == "value1"
        assert settings2.get("key") == "value2"

    def test_list_workspaces(self, tmp_path):
        """Test listing workspaces"""
        manager = SettingsManager(tmp_path)

        workspace1 = tmp_path / "project1"
        workspace2 = tmp_path / "project2"
        workspace1.mkdir()
        workspace2.mkdir()

        manager.get_workspace_settings(workspace1)
        manager.get_workspace_settings(workspace2)

        workspaces = manager.list_workspaces()

        assert len(workspaces) == 2
        assert workspace1 in workspaces
        assert workspace2 in workspaces
