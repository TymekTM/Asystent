# Plugin Manager - Zarządza dynamicznym ładowaniem i testowaniem pluginów.

import os
import importlib.util
import logging

logger = logging.getLogger(__name__)

class PluginManager:
    def __init__(self, plugin_dir="plugins"):
        self.plugin_dir = plugin_dir
        self.plugins = []

    async def load_plugins(self, assistant):
        """
        Ładuje wszystkie pluginy znajdujące się w folderze plugin_dir.
        """
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = filename[:-3]
                file_path = os.path.join(self.plugin_dir, filename)
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # Szukamy klas dziedziczących po AssistantPlugin
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    try:
                        from plugins.base import AssistantPlugin
                        if isinstance(attr, type) and issubclass(attr, AssistantPlugin) and attr is not AssistantPlugin:
                            plugin_instance = attr()
                            await plugin_instance.initialize(assistant)
                            self.plugins.append(plugin_instance)
                            logger.info("Załadowano plugin: %s", attr_name)
                    except Exception as e:
                        logger.error("Błąd ładowania pluginu %s: %s", attr_name, e)

    async def test_plugins(self):
        """
        Testuje wszystkie załadowane pluginy.
        """
        results = {}
        for plugin in self.plugins:
            try:
                result = await plugin.test()
                results[plugin.__class__.__name__] = result
            except Exception as e:
                results[plugin.__class__.__name__] = f"Test nie powiódł się: {e}"
        return results
