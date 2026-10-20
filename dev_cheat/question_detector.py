import re
from typing import List, Dict, Any, Optional

class QuestionBlock:
    def __init__(self, q_id: str, title: str, text: str, bbox: List[float], q_type: str = "general"):
        self.id = q_id
        self.title = title
        self.text = text
        self.bbox = bbox  # [x, y, width, height]
        self.q_type = q_type  # 'mcq', 'math', 'theory', 'coding'
        self.options: List[str] = []
        self.solution: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "bbox": self.bbox,
            "type": self.q_type,
            "options": self.options,
            "solution": self.solution
        }


class QuestionDetector:
    def __init__(self):
        # Specific patterns strictly for Physics & Math exam questions
        self.stem_question_starts = [
            # Standalone numbered questions: "8.", "8)", "Q8.", "Question 8:"
            re.compile(r'^\s*(?:Q(?:uestion)?\s*[\d#]+[\.:\)]?|\d{1,3}[\.\)\:])\s*', re.IGNORECASE),
            # Physics / Math entity phrases
            re.compile(r'^\s*(?:The\s+(?:distance|displacement|speed|velocity|acceleration|force|mass|momentum|energy|work|potential|kinetic|power|frequency|wavelength|current|resistance|capacitance|voltage|field|charge|pressure|temperature|heat|efficiency|torque|angle|vector|matrix|integral|derivative|limit|root|function|curve|equation|sum|product|value|ratio))\b', re.IGNORECASE),
            re.compile(r'^\s*(?:A\s+(?:particle|bullet|block|body|car|projectile|ball|train|wire|cylinder|sphere|pendulum|spring|piston|capacitor|resistor|inductor|dipole|charge|solid|liquid|gas|wave|ray|beam|photon|electron|proton|satellite))\b', re.IGNORECASE),
            re.compile(r'^\s*(?:Calculate|Evaluate|Find|Determine|Solve)\s+(?:the|all|value|derivative|integral|equation)\b', re.IGNORECASE),
        ]

        # STEM keywords that must be present in the block for it to qualify as a physics/math question
        self.stem_keywords = [
            "velocity", "acceleration", "speed", "particle", "mass", "friction",
            "force", "momentum", "kinetic", "potential", "energy", "wavelength",
            "frequency", "distance", "displacement", "resistance", "current",
            "voltage", "charge", "electric", "magnetic", "gravitational", "gravity",
            "torque", "pendulum", "oscillation", "shm", "wave", "refraction",
            "reflection", "focal", "lens", "mirror", "vector", "matrix", "integral",
            "derivative", "dy/dx", "limit", "polynomial", "cosine", "sine", "tangent",
            "logarithm", "equation", "root", "probability", "permutation", "combination",
            "ms-1", "ms^-1", "m/s", "km/h", "rad/s", "joule", "newton", "tesla",
            "cm", "kg", "x^2", "t^2", "at^2", "dx/dt", "d2x/dt2", "dimen", "integer"
        ]

        # Options pattern: (a), (b), (c), (d) or A), B), C), D)
        self.option_pattern = re.compile(r'(?:[\(\[]?[A-Da-d1-4][\)\.\:\-]|(?:Option\s+[A-D1-4]))', re.IGNORECASE)

    def detect(self, ocr_data: Dict[str, Any]) -> List[QuestionBlock]:
        """
        Scans OCR lines, clusters them column-by-column, and extracts ONLY genuine
        physics and maths questions with tight bounding boxes.
        """
        raw_lines = ocr_data.get("lines", [])
        if not raw_lines:
            return []

        # Filter out IDE chrome, browser chrome, and non-content noise
        clean_lines = []
        for l in raw_lines:
            txt = l["text"].strip()
            txt_lower = txt.lower()
            if len(txt) < 2:
                continue
            # Skip code editor chrome, browser tabs, terminal text
            if any(ui in txt_lower for ui in [
                "file edit selection", "run terminal help", "antigravity ide",
                "dashboardpage", "package.json", "localhost", "close x", "powershell",
                "cmd.exe", "changes", "source control", "git commit", "dev_cheat solution"
            ]):
                continue
            clean_lines.append(l)

        if not clean_lines:
            return []

        # COLUMN-AWARE SEPARATION:
        # Check if the page has a two-column or multi-column layout by examining X coordinates
        x_centers = [l["bbox"][0] + l["bbox"][2] / 2 for l in clean_lines]
        min_x = min(l["bbox"][0] for l in clean_lines)
        max_r = max(l["bbox"][0] + l["bbox"][2] for l in clean_lines)
        page_width = max_r - min_x

        columns = []
        if page_width > 500:
            # Detect two-column split
            midpoint = min_x + page_width / 2
            left_col = [l for l in clean_lines if (l["bbox"][0] + l["bbox"][2] / 2) < midpoint]
            right_col = [l for l in clean_lines if (l["bbox"][0] + l["bbox"][2] / 2) >= midpoint]
            if left_col and right_col:
                columns = [
                    sorted(left_col, key=lambda l: l["bbox"][1]),
                    sorted(right_col, key=lambda l: l["bbox"][1])
                ]
            else:
                columns = [sorted(clean_lines, key=lambda l: l["bbox"][1])]
        else:
            columns = [sorted(clean_lines, key=lambda l: l["bbox"][1])]

        question_candidates = []
        q_count = 1

        for col_lines in columns:
            current_block_lines = []
            for line in col_lines:
                text = line["text"].strip()
                is_start = False

                # Check question start
                for pat in self.stem_question_starts:
                    if pat.search(text):
                        is_start = True
                        break

                # Pure option lines belong to current question
                is_pure_option = bool(re.match(r'^\s*[\(\[]?[A-Da-d1-4][\)\.\:\-]', text))

                # Split into new question block when a new question start appears
                if is_start and current_block_lines and not is_pure_option:
                    block = self._create_stem_block(current_block_lines, q_count)
                    if block:
                        question_candidates.append(block)
                        q_count += 1
                    current_block_lines = [line]
                else:
                    current_block_lines.append(line)

            # Flush column's final block
            if current_block_lines:
                block = self._create_stem_block(current_block_lines, q_count)
                if block:
                    question_candidates.append(block)
                    q_count += 1

        return question_candidates

    def _create_stem_block(self, lines: List[Dict[str, Any]], index: int) -> Optional[QuestionBlock]:
        if not lines:
            return None

        full_text = " ".join([l["text"] for l in lines]).strip()
        full_text_lower = full_text.lower()

        # Must have sufficient length
        if len(full_text) < 30:
            return None

        # CRITICAL FILTER: Must contain authentic physics or math keywords!
        matching_keywords = [kw for kw in self.stem_keywords if kw in full_text_lower]
        if len(matching_keywords) < 2 and not any(kw in full_text_lower for kw in ["ms-1", "ms^-1", "m/s", "acceleration", "particle", "velocity", "integral", "derivative"]):
            return None

        # Determine if MCQ or numerical value
        has_options = bool(self.option_pattern.search(full_text))
        q_type = "mcq" if has_options else "math"

        # Calculate accurate, tightly fitted bounding box strictly for this column's question
        valid_boxes = [l["bbox"] for l in lines if l["bbox"][2] > 0 and l["bbox"][3] > 0]
        if not valid_boxes:
            return None

        min_x = min(b[0] for b in valid_boxes)
        min_y = min(b[1] for b in valid_boxes)
        max_r = max(b[0] + b[2] for b in valid_boxes)
        max_b = max(b[1] + b[3] for b in valid_boxes)

        # Precise 5px padding to tightly frame only this question
        padding = 5
        bbox = [
            max(0, min_x - padding),
            max(0, min_y - padding),
            (max_r - min_x) + (padding * 2),
            (max_b - min_y) + (padding * 2)
        ]

        # Extract clean title from question number & first line
        first_meaningful = next((l["text"].strip() for l in lines if len(l["text"].strip()) > 6), full_text)
        title = first_meaningful[:60].strip()
        if len(first_meaningful) > 60:
            title += "..."

        block = QuestionBlock(
            q_id=f"q_{index}",
            title=f"Q{index}: {title}",
            text=full_text,
            bbox=bbox,
            q_type=q_type
        )

        if has_options:
            options = []
            for l in lines:
                l_text = l["text"].strip()
                if self.option_pattern.search(l_text):
                    options.append(l_text)
            block.options = options

        return block

question_detector = QuestionDetector()
