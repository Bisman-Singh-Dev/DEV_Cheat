import json
import io
import time
import base64
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from PIL import Image

from .config import config
from .question_detector import QuestionBlock

class GeminiVisionEngine:
    def __init__(self):
        self.models_to_try = [
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite"
        ]

    def detect_and_solve(self, screen_image: Image.Image) -> List[QuestionBlock]:
        """
        Uses Gemini Vision to detect all physics and mathematics questions directly
        from the screen image, calculates precise bounding boxes, and generates
        step-by-step derivations.
        """
        if not config.gemini_api_key:
            return []

        screen_w, screen_h = screen_image.size

        # Optimize image size for fast vision processing (max dimension 1280px)
        max_dim = 1280
        ratio = min(max_dim / screen_w, max_dim / screen_h)
        new_w = max(1, int(screen_w * ratio))
        new_h = max(1, int(screen_h * ratio))

        thumb = screen_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        if thumb.mode != "RGB":
            thumb = thumb.convert("RGB")

        buf = io.BytesIO()
        thumb.save(buf, format="JPEG", quality=85)
        b64_image = base64.b64encode(buf.getvalue()).decode("utf-8")

        prompt = """You are an expert exam vision AI specialized in Physics and Mathematics.
Analyze this screen containing an exam, worksheet, or problem set.
Strictly detect each individual Physics and Mathematics question on the page.

For each detected question, provide:
1. "id": e.g. "q_1", "q_2", "q_4"
2. "title": Short descriptive title with question number (e.g. "Q4: Velocity of a particle")
3. "box_2d": [ymin, xmin, ymax, xmax] tightly bounding ONLY this specific question, its formulas, diagrams, and options.
   Coordinates MUST be normalized to a 0-1000 integer scale.
   Do NOT include taskbars, browser bars, or other unrelated questions.
4. "question_text": The complete, accurate text of the problem including mathematical expressions.
5. "options": List of options (e.g. ["(a) 40 km/h", "(b) 45 km/h", "(c) 48 km/h", "(d) 60 km/h"]) or empty list if numerical.
6. "direct_answer": Precise final answer / option (e.g. "Option (c) 48 km/h" or "Option (a) t^2").
7. "explanation": A systematic, numbered step-by-step derivation:
   Step 1: Identify Given Data & Underlying Physics/Math Principle
   Step 2: Set up Governing Formulas & Differential Equations
   Step 3: Step-by-Step Mathematical Derivation / Integration
   Step 4: Final Conclusion matching the correct option
   (Do NOT write one dense paragraph. Use clean newlines between every step).

Return strictly a valid JSON object matching this schema:
{
  "questions": [
    {
      "id": "q_4",
      "title": "Q4: Velocity of a particle",
      "box_2d": [323, 203, 597, 831],
      "question_text": "The velocity of a particle is v = v0 + gt + ft^2...",
      "options": ["(a) ...", "(b) ...", "(c) ...", "(d) ..."],
      "direct_answer": "Option (c) v0 + g/2 + f/3",
      "explanation": "Step 1: Given velocity v(t)...\\nStep 2: Displacement x = integral(v dt)...\\nStep 3: Integrate from 0 to 1...\\nFinal Result: Option (c)"
    }
  ]
}"""

        for model in self.models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={config.gemini_api_key}"
                payload = {
                    "contents": [{
                        "parts": [
                            {"inlineData": {"mimeType": "image/jpeg", "data": b64_image}},
                            {"text": prompt}
                        ]
                    }],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 2500,
                        "responseMimeType": "application/json"
                    }
                }

                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )

                with urllib.request.urlopen(req, timeout=14) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(text)
                    raw_questions = parsed.get("questions", [])

                    question_blocks = []
                    for idx, q in enumerate(raw_questions):
                        box = q.get("box_2d", [0, 0, 1000, 1000])
                        ymin, xmin, ymax, xmax = box

                        # Scale normalized 0-1000 coordinates to actual screen pixels
                        px_x = int((xmin / 1000.0) * screen_w)
                        px_y = int((ymin / 1000.0) * screen_h)
                        px_w = max(40, int(((xmax - xmin) / 1000.0) * screen_w))
                        px_h = max(30, int(((ymax - ymin) / 1000.0) * screen_h))

                        # Safe padding
                        padding = 4
                        bbox = [
                            max(0, px_x - padding),
                            max(0, px_y - padding),
                            min(screen_w, px_w + padding * 2),
                            min(screen_h, px_h + padding * 2)
                        ]

                        q_id = q.get("id") or f"q_{idx + 1}"
                        title = q.get("title") or f"Question {idx + 1}"
                        q_text = q.get("question_text") or ""
                        options = q.get("options", [])
                        q_type = "mcq" if options else "math"

                        block = QuestionBlock(
                            q_id=q_id,
                            title=title,
                            text=q_text,
                            bbox=bbox,
                            q_type=q_type
                        )
                        block.options = options

                        # Pre-packaged solution from vision
                        block.solution = {
                            "question_id": q_id,
                            "question_text": q_text,
                            "direct_answer": q.get("direct_answer", "Solved"),
                            "explanation": q.get("explanation", ""),
                            "key_points": [f"Direct: {q.get('direct_answer', '')}"],
                            "time_complexity": "N/A",
                            "space_complexity": "N/A",
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        }

                        question_blocks.append(block)

                    if question_blocks:
                        print(f"[Gemini Vision] Successfully detected and solved {len(question_blocks)} question(s) via {model}.")
                        return question_blocks

            except Exception as e:
                print(f"[Gemini Vision] Model {model} attempt notice: {e}")
                continue

        return []

gemini_vision = GeminiVisionEngine()
