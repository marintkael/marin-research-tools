"""
Google Gemini 2.5-Flash with Search-Grounding tool enabled.
Routes via Cloudflare AI Gateway. Grounding adds web-search results inline.
"""
import os
import time
import json
import urllib.request
import urllib.error
from typing import List, Optional
from lm_eval.api.model import LM
from lm_eval.api.registry import register_model


@register_model("gemini_grounded")
class GeminiGrounded(LM):
    """
    Gemini 2.5-flash with google_search grounding tool.

    Args:
      model: "gemini-2.5-flash" (default)
      gateway: optional Cloudflare AI Gateway URL prefix
      max_tokens: 400 default
    """
    def __init__(self, model: str = "gemini-2.5-flash", gateway: Optional[str] = None,
                 max_tokens: int = 400, max_retries: int = 3, **kwargs):
        super().__init__()
        self.model = model
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.api_key = (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY / GOOGLE_GEMINI_API_KEY / GOOGLE_API_KEY env not set")
        if gateway:
            base = gateway.rstrip("/")
            self.url = f"{base}/google-ai-studio/v1beta/models/{model}:generateContent"
        else:
            self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    @property
    def eot_token_id(self): return None

    @property
    def max_length(self): return 8192

    @property
    def max_gen_toks(self): return self.max_tokens

    @property
    def batch_size(self): return 1

    @property
    def device(self): return "cpu"

    @property
    def tokenizer_name(self): return self.model

    def loglikelihood(self, requests, **kwargs):
        raise NotImplementedError()

    def loglikelihood_rolling(self, requests, **kwargs):
        raise NotImplementedError()

    def generate_until(self, requests, **kwargs) -> List[str]:
        results = []
        for req in requests:
            ctx, gen_kwargs = req.args if hasattr(req, 'args') else req
            answer = self._ask_one(ctx)
            results.append(answer or "")
        return results

    def _ask_one(self, prompt: str) -> Optional[str]:
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"googleSearch": {}}],  # the grounding tool
            "generationConfig": {
                "maxOutputTokens": self.max_tokens,
                "temperature": 0.3,
            },
        }
        # API key as query param for Google AI Studio
        url_with_key = f"{self.url}?key={self.api_key}"
        data = json.dumps(body).encode()
        backoff_s = [5, 15, 30]
        last_err = None
        for attempt in range(self.max_retries):
            req = urllib.request.Request(
                url_with_key, data=data, method="POST",
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "marin-research-harness/4.0",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    j = json.loads(r.read())
                    candidates = j.get("candidates") or []
                    if not candidates:
                        return ""
                    parts = (candidates[0].get("content") or {}).get("parts") or []
                    return "".join(p.get("text", "") for p in parts).strip()
            except urllib.error.HTTPError as e:
                last_err = f"HTTP {e.code}"
                if e.code == 429 and attempt < self.max_retries - 1:
                    wait = backoff_s[attempt]
                    print(f"[gemini-grounded] 429 → backoff {wait}s")
                    time.sleep(wait)
                    continue
                raise
            except Exception as e:
                last_err = str(e)
                raise
        raise RuntimeError(f"gemini-grounded retries exhausted: {last_err}")

    @classmethod
    def create_from_arg_string(cls, arg_string, additional_config=None):
        args = {}
        for pair in arg_string.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                args[k.strip()] = v.strip()
        if "max_retries" in args: args["max_retries"] = int(args["max_retries"])
        if "max_tokens" in args: args["max_tokens"] = int(args["max_tokens"])
        return cls(**args)
