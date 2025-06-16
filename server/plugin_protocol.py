from typing import Protocol, Dict, Any, List

class PluginProtocol(Protocol):
    PLUGIN_NAME: str
    PLUGIN_DESCRIPTION: str
    PLUGIN_VERSION: str
    PLUGIN_AUTHOR: str
    PLUGIN_DEPENDENCIES: List[str]

    def get_functions() -> List[Dict[str, Any]]: ...
    async def execute_function(self, function_name: str, parameters: Dict[str, Any], user_id: int) -> Dict[str, Any]: ...
