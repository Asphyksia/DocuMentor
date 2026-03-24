"""
Shared error types and codes for DocuMentor backend.
"""


class ErrorCode:
    """Error codes returned to the frontend via WebSocket."""
    INVALID_JSON = "INVALID_JSON"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNKNOWN_TYPE = "UNKNOWN_TYPE"
    MCP_ERROR = "MCP_ERROR"
    MCP_UNREACHABLE = "MCP_UNREACHABLE"
    UPLOAD_TOO_LARGE = "UPLOAD_TOO_LARGE"
    UPLOAD_DECODE_FAILED = "UPLOAD_DECODE_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    MISSING_ARGUMENT = "MISSING_ARGUMENT"


class DocuMentorError(Exception):
    """Base exception for DocuMentor backend."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class ToolNotFoundError(DocuMentorError):
    def __init__(self, tool_name: str):
        super().__init__(ErrorCode.TOOL_NOT_FOUND, f"Unknown tool: {tool_name}")


class MissingArgumentError(DocuMentorError):
    def __init__(self, arg_name: str):
        super().__init__(ErrorCode.MISSING_ARGUMENT, f"Missing required argument: {arg_name}")
