import re
from typing import List, Dict, Any, Optional

class QuestionBlock:
    def __init__(self, q_id: str, title: str, text: str, bbox: List[float], q_type: str = "general"):
        self.id = q_id
        self.title = title
        self.text = text
        self.bbox = bbox  # [x, y, width, height]
        self.q_type = q_type  # 'mcq', 'coding', 'theory', 'math', 'general'
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
        # Patterns that strongly signal a question start
        self.question_start_patterns = [
            re.compile(r'^\s*(?:Q(?:uestion)?\s*[\d#]+[\.:\)]?)\s*', re.IGNORECASE),
            re.compile(r'^\s*\d{1,3}[\.\)\:]\s*', re.IGNORECASE),
            re.compile(r'^\s*(?:What|Which|Why|How|When|Where|Who|Whose|Whom)\b', re.IGNORECASE),
            re.compile(r'^\s*(?:The\s+(?:distance|speed|velocity|acceleration|force|mass|energy|ratio|value|work|workdone|potential|current|charge|magnitude|equation|number))\b', re.IGNORECASE),
            re.compile(r'^\s*(?:A\s+(?:particle|bullet|block|body|car|ball|train|wire|cylinder|sphere|charge|solid|liquid|gas))\b', re.IGNORECASE),
            re.compile(r'^\s*(?:Given\s+(?:an?|two|the)|Implement\s+|Write\s+(?:a|an)\s+|Find\s+(?:the|all)|Return\s+(?:the|all)|Calculate\s+|Determine\s+|Explain\s+)', re.IGNORECASE),
            re.compile(r'^\s*Problem\s*[\d#]+[\.:\)]?', re.IGNORECASE),
        ]

        # Option patterns (a) (b) (c) (d) or A) B) C) D) or 1) 2)
        self.option_pattern = re.compile(r'(?:[\(\[]?[A-Da-d1-4][\)\.\:\-]|(?:Option\s+[A-D1-4]))', re.IGNORECASE)

        # Coding / Leetcode markers
        self.coding_markers = [
            "example 1:", "constraints:", "input:", "output:", "explanation:",
            "def ", "class Solution", "function ", "public class", "std::vector",
            "time complexity", "space complexity"
        ]

        # UI words to ignore so IDE/Chrome browser chrome doesn't get boxed
        self.ignore_ui_words = [
            "file", "edit", "selection", "view", "terminal", "antigravity",
            "pdf_previews", "dashboardpage", "package.json", "close x", "localhost",
            "http://", "powershell", "cmd.exe", "source control", "changes"
        ]

    def detect(self, ocr_data: Dict[str, Any]) -> List[QuestionBlock]:
        """
        Takes OCR lines and clusters them into distinct Question Blocks with bounding boxes.
        """
        raw_lines = ocr_data.get("lines", [])
        if not raw_lines:
            return []

        # Filter out UI menu chrome lines
        lines = []
        for l in raw_lines:
            txt_lower = l["text"].strip().lower()
            if not txt_lower or len(txt_lower) < 2:
                continue
            # Skip if line is pure UI menu header
            if any(ui in txt_lower for ui in ["file edit selection", "run terminal help", "antigravity ide", "close x"]):
                continue
            lines.append(l)

        if not lines:
            return []

        question_candidates = []
        current_block_lines = []
        current_type = "general"
        q_count = 1

        for i, line in enumerate(lines):
            text = line["text"].strip()
            is_start = False
            detected_type = "general"

            # Check question start patterns
            for pat in self.question_start_patterns:
                if pat.search(text):
                    is_start = True
                    break

            # Standalone question number (e.g. "8." or "9." on its own line)
            if re.match(r'^\d{1,3}[\.\)]$', text):
                is_start = True

            # Sentence ending with question mark
            if not is_start and "?" in text and len(text) > 20:
                if text[0].isupper():
                    is_start = True

            # Coding markers
            text_lower = text.lower()
            if any(marker in text_lower for marker in self.coding_markers):
                detected_type = "coding"

            # Check if this line is just multiple choice options for current question
            is_pure_option = bool(re.match(r'^\s*[\(\[]?[A-Da-d1-4][\)\.\:\-]', text))

            # Break into new question block if a new question starts
            if is_start and current_block_lines and not is_pure_option:
                block = self._create_block(current_block_lines, q_count, current_type)
                if block:
                    question_candidates.append(block)
                    q_count += 1
                current_block_lines = [line]
                current_type = detected_type
            else:
                if is_start:
                    current_type = detected_type
                current_block_lines.append(line)

        # Flush final block
        if current_block_lines:
            block = self._create_block(current_block_lines, q_count, current_type)
            if block:
                question_candidates.append(block)

        return question_candidates

    def _create_block(self, lines: List[Dict[str, Any]], index: int, initial_type: str) -> Optional[QuestionBlock]:
        if not lines:
            return None

        full_text = " ".join([l["text"] for l in lines]).strip()
        # Must have reasonable length to be a genuine question
        if len(full_text) < 25:
            return None

        # Check for question characteristics
        has_qm = "?" in full_text
        has_options = bool(self.option_pattern.search(full_text))
        has_coding = any(m in full_text.lower() for m in self.coding_markers)
        has_numbered = bool(re.search(r'(?:^\d{1,3}[\.\)]|Q(?:uestion)?\s*\d+)', full_text, re.IGNORECASE))
        has_stem_terms = any(t in full_text.lower() for t in ["particle", "speed", "velocity", "acceleration", "calculate", "find", "determine", "integer", "value of", "close to"])

        if not (has_qm or has_options or has_coding or has_numbered or has_stem_terms):
            return None

        # Determine type
        q_type = initial_type
        if has_options:
            q_type = "mcq"
        elif has_coding:
            q_type = "coding"
        elif has_stem_terms or "calculate" in full_text.lower():
            q_type = "math"
        elif has_qm:
            q_type = "theory"

        # Calculate bounding box encompassing all constituent lines
        valid_boxes = [l["bbox"] for l in lines if l["bbox"][2] > 0 and l["bbox"][3] > 0]
        if not valid_boxes:
            return None

        min_x = min(b[0] for b in valid_boxes)
        min_y = min(b[1] for b in valid_boxes)
        max_r = max(b[0] + b[2] for b in valid_boxes)
        max_b = max(b[1] + b[3] for b in valid_boxes)

        padding = 10
        bbox = [
            max(0, min_x - padding),
            max(0, min_y - padding),
            (max_r - min_x) + (padding * 2),
            (max_b - min_y) + (padding * 2)
        ]

        # Extract title from the first line that has substantial text
        first_meaningful = next((l["text"].strip() for l in lines if len(l["text"].strip()) > 5), full_text)
        title = first_meaningful[:65].strip()
        if len(first_meaningful) > 65:
            title += "..."

        block = QuestionBlock(
            q_id=f"q_{index}",
            title=f"Q{index}: {title}",
            text=full_text,
            bbox=bbox,
            q_type=q_type
        )

        # Extract options if MCQ
        if q_type == "mcq":
            options = []
            for l in lines:
                l_text = l["text"].strip()
                if self.option_pattern.search(l_text):
                    options.append(l_text)
            block.options = options

        return block

question_detector = QuestionDetector()
