"""Plugin loader and discovery"""

import importlib.util
import json
import logging
import sys
from pathlib import Path

from .types import Plugin, PluginAPI, PluginManifest

logger = logging.getLogger(__name__)


class PluginLoader:
    """Loads and manages plugins"""

    def __init__(self):
        self.plugins: dict[str, Plugin] = {}
        self._plugin_apis: dict[str, PluginAPI] = {}

    def discover_plugins(self) -> list[Path]:
        """Discover plugins from standard locations"""
        plugin_dirs = []

        # Extensions directory (bundled plugins)
        bundled_dir = Path(__file__).parent.parent.parent / "extensions"
        if bundled_dir.exists():
            for item in bundled_dir.iterdir():
                if item.is_dir() and (item / "plugin.json").exists():
                    plugin_dirs.append(item)

        # User plugins
        user_dir = Path.home() / ".openclaw" / "extensions"
        if user_dir.exists():
            for item in user_dir.iterdir():
                if item.is_dir() and (item / "plugin.json").exists():
                    plugin_dirs.append(item)

        logger.info(f"Discovered {len(plugin_dirs)} plugins")
        return plugin_dirs

    def load_plugin(self, plugin_dir: Path) -> Plugin | None:
        """Load a single plugin"""
        try:
            # Load manifest
            manifest_file = plugin_dir / "plugin.json"
            if not manifest_file.exists():
                logger.warning(f"No plugin.json in {plugin_dir}")
                return None

            with open(manifest_file) as f:
                manifest_data = json.load(f)

            manifest = PluginManifest(**manifest_data)

            # Create plugin instance
            plugin = Plugin(manifest, str(plugin_dir))

            # Load plugin module
            main_file = plugin_dir / manifest.main
            if main_file.exists():
                self._load_plugin_module(plugin, main_file)

            self.plugins[manifest.id] = plugin
            logger.info(f"Loaded plugin: {manifest.id} v{manifest.version}")

            return plugin

        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_dir}: {e}", exc_info=True)
            return None

    def _load_plugin_module(self, plugin: Plugin, module_file: Path) -> None:
        """Load plugin Python module"""
        try:
            # Create module spec
            spec = importlib.util.spec_from_file_location(
                f"openclaw_plugin_{plugin.manifest.id}", module_file
            )

            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)

                # Look for register() or activate() function
                if hasattr(module, "register"):
                    api = PluginAPI(plugin.manifest.id)
                    self._plugin_apis[plugin.manifest.id] = api
                    module.register(api)
                elif hasattr(module, "activate"):
                    api = PluginAPI(plugin.manifest.id)
                    self._plugin_apis[plugin.manifest.id] = api
                    module.activate(api)

        except Exception as e:
            logger.error(f"Failed to load plugin module {module_file}: {e}", exc_info=True)

    def load_all_plugins(self) -> dict[str, Plugin]:
        """Discover and load all plugins"""
        plugin_dirs = self.discover_plugins()

        for plugin_dir in plugin_dirs:
            self.load_plugin(plugin_dir)

        return self.plugins

    def get_plugin(self, plugin_id: str) -> Plugin | None:
        """Get a loaded plugin"""
        return self.plugins.get(plugin_id)

    def get_plugin_api(self, plugin_id: str) -> PluginAPI | None:
        """Get plugin API instance"""
        return self._plugin_apis.get(plugin_id)


# Global plugin loader
_global_loader = PluginLoader()


def get_plugin_loader() -> PluginLoader:
    """Get global plugin loader"""
    return _global_loader
