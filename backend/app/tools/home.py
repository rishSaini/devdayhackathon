from ..schemas import ToolResult


async def set_lights(level_percent: int = 30) -> ToolResult:
    level = max(0, min(100, level_percent))
    return ToolResult(ok=True, source="mock", detail=f"Simulated device: lights at {level}%.")


async def smart_lock_grant_access() -> ToolResult:
    return ToolResult(
        ok=True, source="mock", detail="Simulated lock: 15-minute emergency access window."
    )
