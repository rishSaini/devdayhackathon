"""Ripple's single-process prototype backend."""

import os

# Set before the Agents SDK is imported. Pydantic .env loading does not set os.environ.
os.environ["OPENAI_AGENTS_DONT_LOG_MODEL_DATA"] = "1"
os.environ["OPENAI_AGENTS_DONT_LOG_TOOL_DATA"] = "1"
