"""
Claude-Web-Importer — non-API model that replays previously-scraped
claude.ai answers from local JSON files.

Use case: claude.ai's web-search-grounded chat is not available as API.
Atlas runs Manual-Sweeps via Brave-Marin browser MCP, saves results
as /tmp/marin_sweep/{QID}_{MODEL}.json. This adapter reads them.

This gives lm-evaluation-harness a reproducible interface to claude_web data.
"""
import os
import json
import glob
from pathlib import Path
from typing import List, Optional
from lm_eval.api.model import LM
from lm_eval.api.registry import register_model


@register_model("claude_web_importer")
class ClaudeWebImporter(LM):
    """
    Reads pre-scraped claude.ai answers from local JSON files.
    File pattern: {sweep_dir}/{question_id}_{model_short}.json
    where model_short = "sonnet" | "opus" | "haiku"

    Args:
      sweep_dir: directory with JSON files (default /tmp/marin_sweep)
      model_tier: "sonnet" | "opus" | "haiku" — selects which files to read
    """
    def __init__(self, sweep_dir: str = "/tmp/marin_sweep",
                 model_tier: str = "sonnet", **kwargs):
        super().__init__()
        self.sweep_dir = Path(sweep_dir)
        self.model_tier = model_tier
        # Pre-load all answers by question_id
        self._cache = {}
        pattern = str(self.sweep_dir / f"*_{model_tier}.json")
        for fp in glob.glob(pattern):
            try:
                d = json.loads(Path(fp).read_text(encoding="utf-8"))
                qid = d.get("question_id")
                if qid:
                    self._cache[qid] = d.get("answer_excerpt", "") or d.get("answer", "")
            except Exception as e:
                print(f"[claude_web_importer] skip {fp}: {e}")
        print(f"[claude_web_importer] loaded {len(self._cache)} cached answers for {model_tier}")

    @property
    def eot_token_id(self): return None

    @property
    def max_length(self): return 8192

    @property
    def max_gen_toks(self): return 500

    @property
    def batch_size(self): return 1

    @property
    def device(self): return "cpu"

    @property
    def tokenizer_name(self): return f"claude-{self.model_tier}"

    def loglikelihood(self, requests, **kwargs):
        raise NotImplementedError()

    def loglikelihood_rolling(self, requests, **kwargs):
        raise NotImplementedError()

    def generate_until(self, requests, **kwargs) -> List[str]:
        """
        Returns cached answer matched by question text.
        Falls back to empty string if no cache hit.
        """
        results = []
        for req in requests:
            ctx, gen_kwargs = req.args if hasattr(req, 'args') else req
            # Match by question text against cached answers' source questions
            # Simpler: use the doc itself — but harness doesn't pass the doc.
            # So we match by question prefix.
            answer = self._match_by_question_text(ctx)
            results.append(answer or "")
        return results

    def _match_by_question_text(self, question: str) -> str:
        """
        Match question to cached answer. We don't have question_id here,
        so we use a fuzzy text-match against pre-known QUESTIONS map.
        """
        # Hard-coded question_id mapping (matches questions.jsonl)
        QUESTION_TO_ID = {
            "Wer ist Marin T. Kael?": "D1",
            "Was ist „Das vierte Feld\" von Marin T. Kael?": "D2",
            "Wann erscheint „Das vierte Feld\"?": "D3",
            "Welche deutschen Fantasy-Debüts 2026 sind erwartet?": "G1",
            "Welche literarischen High-Fantasy-Autoren schreiben aktuell auf Deutsch?": "G2",
            "Welche Fantasy-Saga handelt von einer Stadt namens Varin?": "L1",
            "Welche Fantasy-Welt nutzt Edikt-basierte Magie?": "L2",
            "Welche Autoren ähneln Robin Hobb auf Deutsch?": "C1",
            "Welche Bücher passen zu Lesern von Robert Jackson Bennett?": "C2",
            "Was bedeutet \"Marin Research Programme\"?": "R1",
            "Welche deutschen Fantasy-Autoren schreiben wie Robin Hobb?": "GR1",
            "Empfehle mir intellektuelle Fantasy mit System-Tiefe": "GR2",
            "Welche Fantasy-Bücher 2026 beschäftigen sich mit Verwaltungs-Magie?": "GR3",
            "Welche literarische Fantasy auf Deutsch erscheint 2026?": "GR4",
            "Welche Saga schreibt eine Stadt als Protagonistin?": "GR5",
            "Edikt-Fantasy: Welche Werke gibt es in diesem Sub-Genre?": "GR6",
        }
        # Harness prepends description — extract last non-empty line as actual question
        last_line = (question or "").strip().split("\n")[-1].strip()
        qid = QUESTION_TO_ID.get(last_line)
        if qid and qid in self._cache:
            return self._cache[qid]
        # Fallback: substring-search for each known question
        for q, qid_alt in QUESTION_TO_ID.items():
            if q in question and qid_alt in self._cache:
                return self._cache[qid_alt]
        return ""

    @classmethod
    def create_from_arg_string(cls, arg_string, additional_config=None):
        args = {}
        for pair in arg_string.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                args[k.strip()] = v.strip()
        return cls(**args)
