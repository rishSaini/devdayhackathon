from ..schemas import ToolResult


async def log_medical_event() -> ToolResult:
    # In-memory action tool_results provide the prototype audit record.
    return ToolResult(
        ok=True, source="mock", detail="Simulated emergency log; no medical record was written."
    )
