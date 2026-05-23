"""
OpenAI gpt-4o-search-preview / gpt-4o-mini-search-preview adapter.
Routes via Cloudflare AI Gateway (cache 7200s) + retry-backoff bei 429.
"""
import os
import time
import json
import urllib.request
import urllib.error
from typing import List, Optional
from lm_eval.api.model import LM
from lm_eval.api.registry import register_model


@register_model("openai_search_preview")
class OpenAISearchPreview(LM):
    """
    Model adapter for OpenAI search-preview models with proper rate-limit handling.

    Args:
      model: gpt-4o-search-preview-2025-03-11 or gpt-4o-mini-search-preview-2025-03-11
      gateway: optional Cloudflare AI Gateway URL prefix
      max_retries: default 3, exponential backoff 5s/15s/30s
    """
    def __init__(self, model: str, gateway: Optional[str] = None,
                 max_retries: int = 3, max_tokens: int = 400, **kwargs):
        super().__init__()
        self.model = model
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY env not set")
        # If gateway given, use it. Else direct OpenAI.
        if gateway:
            self.url = f"{gateway.rstrip('/')}/openai/chat/completions"
        else:
            self.url = "https://api.openai.com/v1/chat/completions"

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
        raise NotImplementedError("Search-preview only supports generate_until")

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
        # search-preview accepts NO temperature
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
        }
        data = json.dumps(body).encode()
        backoff_s = [5, 15, 30]
        last_err = None
        for attempt in range(self.max_retries):
            req = urllib.request.Request(
                self.url, data=data, method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "marin-research-harness/4.0",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    j = json.loads(r.read())
                    return (j.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
            except urllib.error.HTTPError as e:
                last_err = f"HTTP {e.code}"
                if e.code == 429 and attempt < self.max_retries - 1:
                    wait = backoff_s[attempt]
                    print(f"[openai-search-preview] 429 → backoff {wait}s (attempt {attempt+1}/{self.max_retries})")
                    time.sleep(wait)
                    continue
                # Other HTTP errors: re-raise so harness logs it
                raise
            except Exception as e:
                last_err = str(e)
                raise
        # All retries exhausted
        raise RuntimeError(f"openai_search_preview retries exhausted: {last_err}")

    @classmethod
    def create_from_arg_string(cls, arg_string, additional_config=None):
        # Parse "model=X,gateway=Y,max_retries=3"
        args = {}
        for pair in arg_string.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                args[k.strip()] = v.strip()
        # Convert numerics
        if "max_retries" in args: args["max_retries"] = int(args["max_retries"])
        if "max_tokens" in args: args["max_tokens"] = int(args["max_tokens"])
        return cls(**args)
