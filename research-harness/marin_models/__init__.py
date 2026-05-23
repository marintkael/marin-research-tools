"""
Marin Custom Models for lm-evaluation-harness.

Three adapters not in default harness:
  1. OpenAI-Search-Preview with retry-backoff (handles tight rate-limits)
  2. Gemini-Grounded (Google Search grounding tool enabled)
  3. Claude-Web-Importer (replays existing JSON snapshots from claude.ai sweeps)
"""
from .openai_search import OpenAISearchPreview
from .gemini_grounded import GeminiGrounded
from .claude_web_importer import ClaudeWebImporter

__all__ = ["OpenAISearchPreview", "GeminiGrounded", "ClaudeWebImporter"]
