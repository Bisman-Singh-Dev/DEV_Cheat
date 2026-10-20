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

        return f"""You are Dev_Cheat, an elite speed-coding and technical exam problem solver.
Directly and concisely solve the following problem:

[QUESTION TYPE: {q_type.upper()}]
{question_text}
{options_text}

Respond in the following STRICT JSON format only (no markdown quotes outside JSON):
{{
  "direct_answer": "Direct answer or chosen option letter and text (e.g. 'B) O(log n)')",
  "key_points": ["Point 1", "Point 2"],
  "code": "Clean, optimal code if applicable, else empty string",
  "time_complexity": "e.g. O(n)",
  "space_complexity": "e.g. O(1)",
  "explanation": "Concise 2-sentence explanation of why this solution is correct"
}}
"""

    def _solve_with_gemini(self, prompt: str) -> Optional[Dict[str, Any]]:
        model = config.gemini_model or "gemini-3.8-flash"
        api_key = config.gemini_api_key
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024
            }
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as response:
                result = json.loads(response.read().decode("utf-8"))
                candidate = result["candidates"][0]["content"]["parts"][0]["text"]
                return self._parse_json_response(candidate)
        except Exception as e:
            # Fallback immediately without hanging the monitor loop
            return {"error": str(e)}

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            return {
                "direct_answer": data.get("direct_answer", "Answer identified"),
                "key_points": data.get("key_points", []),
                "code": data.get("code", ""),
                "time_complexity": data.get("time_complexity", ""),
                "space_complexity": data.get("space_complexity", ""),
                "explanation": data.get("explanation", cleaned),
                "source": "gemini"
            }
        except Exception:
            return {
                "direct_answer": cleaned[:120],
                "key_points": [],
                "code": "",
                "time_complexity": "",
                "space_complexity": "",
                "explanation": cleaned,
                "source": "gemini-raw"
            }

    def _solve_fallback(self, question_text: str, q_type: str, options: Optional[list]) -> Dict[str, Any]:
        """Local offline rule-based responder when API key is missing or offline."""
        q_lower = question_text.lower()

        # Math evaluation heuristic
        import re
        math_match = re.search(r'(\d+)\s*([\+\-\*\/])\s*(\d+)', question_text)
        if math_match:
            try:
                a, op, b = math_match.groups()
                val = eval(f"{a} {op} {b}")
                return {
                    "direct_answer": f"Result: {val}",
                    "key_points": [f"Calculated {a} {op} {b} = {val}"],
                    "code": f"result = {a} {op} {b}",
                    "time_complexity": "O(1)",
                    "space_complexity": "O(1)",
                    "explanation": f"Arithmetic evaluation of {a} {op} {b}.",
                    "source": "local-math"
                }
            except Exception:
                pass

        # MCQ heuristic
        if options and len(options) > 0:
            return {
                "direct_answer": f"Recommended Choice: {options[0]}",
                "key_points": ["Detected MCQ pattern", "Review highlighted options"],
                "code": "",
                "time_complexity": "N/A",
                "space_complexity": "N/A",
                "explanation": "Identified multiple choice question. (Configure GEMINI_API_KEY for advanced AI reasoning).",
                "source": "local-heuristic"
            }

        return {
            "direct_answer": "Question detected",
            "key_points": ["Analyzed query parameters", "Ready for submission"],
            "code": "# Dev_Cheat: optimal solution stub\ndef solution():\n    pass",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "explanation": "Question captured from screen. Add GEMINI_API_KEY to .env for full real-time neural solutions.",
            "source": "local-fallback"
        }

    def get_history(self) -> list:
        return self.history

    def clear_history(self):
        self.history = []
        self._save_history()

solver = SolverEngine()
