from inspect_ai._util.content import (
    Content,
    ContentAudio,
    ContentImage,
    ContentText,
    ContentVideo,
)
from inspect_ai._util.deprecation import relocated_module_attribute

from ._tool import Tool, ToolError, ToolResult, tool
from ._tool_call import (
    ToolCall,
    ToolCallContent,
    ToolCallError,
    ToolCallModelInput,
    ToolCallView,
    ToolCallViewer,
)
from ._tool_choice import ToolChoice, ToolFunction
from ._tool_def import ToolDef
from ._tool_info import ToolInfo
from ._tool_params import JSONType, ToolParam, ToolParams
from ._tool_with import tool_with
from ._tools._computer import computer
from ._tools._execute import bash, python
from ._tools._web_browser import web_browser
from ._tools._web_search import web_search

__all__ = [
    "bash",
    "computer",
    "python",
    "web_browser",
    "web_search",
    "tool",
    "tool_with",
    "Tool",
    "ToolCallError",
    "ToolError",
    "ToolResult",
    "Content",
    "ContentAudio",
    "ContentImage",
    "ContentText",
    "ContentVideo",
    "ToolCall",
    "ToolCallContent",
    "ToolCallModelInput",
    "ToolCallView",
    "ToolCallViewer",
    "ToolChoice",
    "ToolDef",
    "ToolFunction",
    "ToolInfo",
    "ToolParam",
    "ToolParams",
    "JSONType",
]

_UTIL_MODULE_VERSION = "0.3.19"
_REMOVED_IN = "0.4"


relocated_module_attribute(
    "ToolEnvironment",
    "inspect_ai.util.SandboxEnvironment",
    _UTIL_MODULE_VERSION,
    _REMOVED_IN,
)
relocated_module_attribute(
    "ToolEnvironments",
    "inspect_ai.util.SandboxEnvironments",
    _UTIL_MODULE_VERSION,
    _REMOVED_IN,
)
relocated_module_attribute(
    "ToolEnvironmentSpec",
    "inspect_ai.util.SandboxEnvironmentSpec",
    _UTIL_MODULE_VERSION,
    _REMOVED_IN,
)
relocated_module_attribute(
    "tool_environment",
    "inspect_ai.util.sandbox",
    _UTIL_MODULE_VERSION,
    _REMOVED_IN,
)
relocated_module_attribute(
    "toolenv", "inspect_ai.util.sandboxenv", _UTIL_MODULE_VERSION, _REMOVED_IN
)
relocated_module_attribute(
    "web_browser_tools",
    "inspect_ai.tool.web_browser",
    "0.3.19",
    _REMOVED_IN,
)
