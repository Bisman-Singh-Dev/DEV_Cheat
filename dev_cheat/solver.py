import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from pathlib import Path
from .config import config, HISTORY_FILE

class SolverEngine:
    def __init__(self):
        self.history = self._load_history()

    def _load_history(self) -> list:
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Solver] Error saving history: {e}")

    def solve(self, question_text: str, q_type: str = "general", options: Optional[list] = None) -> Dict[str, Any]:
        """
        Solves the given question using Gemini AI or fallback engine.
        Returns a structured solution dictionary.
        """
        prompt = self._build_prompt(question_text, q_type, options)
        solution = None

        if config.gemini_api_key:
            solution = self._solve_with_gemini(prompt)

        if not solution or "error" in solution:
            # Fallback local solver
            solution = self._solve_fallback(question_text, q_type, options)

        # Enhance with metadata
        solution["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        solution["question_text"] = question_text
        solution["q_type"] = q_type

        # Save to history
        self.history.insert(0, solution)
        # Keep last 200 items
        if len(self.history) > 200:
            self.history = self.history[:200]
        self._save_history()

        return solution

    def _build_prompt(self, question_text: str, q_type: str, options: Optional[list]) -> str:
        options_text = ""
        if options:
            options_text = "\nOptions:\n" + "\n".join(options)

        return f"""You are an elite competitive exam and technical interview solver.
Solve the following question with rigorous correctness (physics, mathematics, computer science, or general multiple choice).
Provide the precise answer, exact option if given, and clear step-by-step reasoning.

[QUESTION]:
{question_text}
{options_text}

Respond in the following STRICT JSON format only:
{{
  "direct_answer": "Precise final answer, e.g. 'Option (B) 0.7 ms^-1' or 'n = 3'",
  "key_points": ["Key step 1", "Key step 2"],
  "code": "Code if programming question, else empty string",
  "time_complexity": "e.g. O(1) or N/A",
  "space_complexity": "e.g. O(1) or N/A",
  "explanation": "Clear, accurate step-by-step derivation or proof"
}}
"""

    def _solve_with_gemini(self, prompt: str) -> Optional[Dict[str, Any]]:
        # Fast responsive models in priority order
        models_to_try = [
            config.gemini_model,
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash",
            "gemini-3-flash-preview"
        ]
        # Remove duplicates while preserving order
        seen = set()
        models = [m for m in models_to_try if m and not (m in seen or seen.add(m))]
        api_key = config.gemini_api_key

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1024
            }
        }
        req_data = json.dumps(payload).encode("utf-8")

        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                req = urllib.request.Request(
                    url,
                    data=req_data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=8.0) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    candidate = result["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = self._parse_json_response(candidate)
                    parsed["model_used"] = model
                    return parsed
            except Exception as e:
                # Try next model in chain immediately
                continue

        return {"error": "All AI models timed out or quota exceeded."}

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        import re
        cleaned = text.strip()

        # Try to locate JSON block if embedded in markdown
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return {
                    "direct_answer": data.get("direct_answer", "Answer identified"),
                    "key_points": data.get("key_points", []),
                    "code": data.get("code", ""),
                    "time_complexity": data.get("time_complexity", "N/A"),
                    "space_complexity": data.get("space_complexity", "N/A"),
                    "explanation": data.get("explanation", cleaned),
                    "source": "gemini"
                }
            except Exception:
                pass

        # If not structured JSON, extract the primary answer line and explanation directly
        lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
        first_line = lines[0] if lines else cleaned[:100]
        # Look for lines with 'Answer:' or option letters like (b) or (B)
        ans_line = first_line
        for l in lines:
            if re.search(r'(?:Answer|Option|\([A-Da-d]\))\s*[:\-]?\s*', l, re.IGNORECASE):
                ans_line = l
                break

        return {
            "direct_answer": ans_line[:120],
            "key_points": lines[1:4] if len(lines) > 1 else [],
            "code": "",
            "time_complexity": "N/A",
            "space_complexity": "N/A",
            "explanation": cleaned,
            "source": "gemini-text"
        }

    def _solve_fallback(self, question_text: str, q_type: str, options: Optional[list]) -> Dict[str, Any]:
        """Fallback when API is temporarily unreachable."""
        return {
            "direct_answer": "AI Connection Paused",
            "key_points": ["Could not reach AI provider", "Check internet connection or API quota"],
            "code": "",
            "time_complexity": "N/A",
            "space_complexity": "N/A",
            "explanation": "Please check your network connection or verify that GEMINI_API_KEY in .env has active quota.",
            "source": "network-error"
        }

    def get_history(self) -> list:
        return self.history

    def clear_history(self):
        self.history = []
        self._save_history()

solver = SolverEngine()
