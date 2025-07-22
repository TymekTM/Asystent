import ast
from pathlib import Path


def test_status_stream_async():
    # Path relative to the root directory
    file_path = Path(__file__).parent.parent / "web_ui" / "routes" / "api_routes.py"
    source = file_path.read_text(encoding="utf-8")
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "setup_api_routes":
            # search inside this function for AsyncFunctionDef named status_stream
            for n in ast.walk(node):
                if isinstance(n, ast.AsyncFunctionDef) and n.name == "status_stream":
                    return
    raise AssertionError("status_stream should be async")
