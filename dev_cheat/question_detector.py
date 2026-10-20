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
            re.compile(r'^\s*\d{1,3}[\.\)\:]\s+', re.IGNORECASE),
            re.compile(r'^\s*(?:What|Which|Why|How|When|Where|Who|Whose|Whom)\b', re.IGNORECASE),
            re.compile(r'^\s*(?:Given\s+(?:an?|two|the)|Implement\s+|Write\s+(?:a|an)\s+|Find\s+(?:the|all)|Return\s+(?:the|all)|Calculate\s+|Determine\s+|Explain\s+)', re.IGNORECASE),
            re.compile(r'^\s*Problem\s*[\d#]+[\.:\)]?', re.IGNORECASE),
        ]

        # Option patterns
        self.option_pattern = re.compile(r'^\s*(?:[\(\[]?[A-Da-d1-4][\)\.\:\-]|(?:Option\s+[A-D1-4]))\s+', re.IGNORECASE)

        # Coding / Leetcode markers
        self.coding_markers = [
            "example 1:", "constraints:", "input:", "output:", "explanation:",
            "def ", "class Solution", "function ", "public class", "std::vector",
            "time complexity", "space complexity"
        ]

    def detect(self, ocr_data: Dict[str, Any]) -> List[QuestionBlock]:
        """
        Takes OCR lines and clusters them into distinct Question Blocks with bounding boxes.
        """
        lines = ocr_data.get("lines", [])
        if not lines:
            return []

        question_candidates = []
        current_block_lines = []
        current_type = "general"
        q_count = 1

        for i, line in enumerate(lines):
            text = line["text"].strip()
            if not text:
                continue

            is_start = False
            detected_type = "general"

            # Check question start patterns
            for pat in self.question_start_patterns:
                if pat.search(text):
                    is_start = True
                    break

            # Check if line contains a question mark and starts like a sentence
            if not is_start and "?" in text and len(text) > 15:
                # If first word is capitalized or interrogative
                if text[0].isupper():
                    is_start = True

            # Check for coding markers
            text_lower = text.lower()
            if any(marker in text_lower for marker in self.coding_markers):
                detected_type = "coding"

            # If current line is an option, it belongs to the previous question
            is_option = bool(self.option_pattern.search(text))

            if is_start and current_block_lines and not is_option:
                # Save previous block if it looks like a valid question
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

        # Fallback heuristic: If no structured numbered questions detected,
        # but there is an obvious problem statement (like LeetCode or a question mark)
        if not question_candidates and lines:
            full_text = ocr_data.get("text", "")
            if "?" in full_text or any(marker in full_text.lower() for marker in self.coding_markers):
                # Filter out pure UI headers (File, Edit, etc.)
                sub_lines = [
                    l for l in lines 
                    if not any(ui in l["text"].lower() for ui in ["file edit", "antigravity", "terminal help", "close x"])
                ]
                if sub_lines:
                    block = self._create_block(sub_lines, 1, "coding" if any(m in full_text.lower() for m in self.coding_markers) else "general")
                    if block:
                        question_candidates.append(block)

        return question_candidates

    def _create_block(self, lines: List[Dict[str, Any]], index: int, initial_type: str) -> Optional[QuestionBlock]:
        if not lines:
            return None

        full_text = " ".join([l["text"] for l in lines]).strip()
        if len(full_text) < 10:
            return None

        # Check if this text actually has any question indicators
        has_qm = "?" in full_text
        has_options = bool(re.search(r'[\(\[]?[A-D][\)\.\:]', full_text))
        has_coding = any(m in full_text.lower() for m in self.coding_markers)
        has_numbered = bool(re.search(r'^\s*(?:Q\d+|\d+[\.:\)])', full_text, re.IGNORECASE))

        if not (has_qm or has_options or has_coding or has_numbered):
            # Probably normal paragraph / UI chrome, not a question
            return None

        # Determine type
        q_type = initial_type
        if has_options:
            q_type = "mcq"
        elif has_coding:
            q_type = "coding"
        elif has_qm:
            q_type = "theory"

        # Calculate bounding box encompassing all constituent lines
        min_x = min(l["bbox"][0] for l in lines if l["bbox"][2] > 0)
        min_y = min(l["bbox"][1] for l in lines if l["bbox"][3] > 0)
        max_r = max(l["bbox"][0] + l["bbox"][2] for l in lines if l["bbox"][2] > 0)
        max_b = max(l["bbox"][1] + l["bbox"][3] for l in lines if l["bbox"][3] > 0)

        # Add slight padding for visual aesthetics
        padding = 8
        bbox = [
            max(0, min_x - padding),
            max(0, min_y - padding),
            (max_r - min_x) + (padding * 2),
            (max_b - min_y) + (padding * 2)
        ]

        title = lines[0]["text"][:60].strip()
        if len(lines[0]["text"]) > 60:
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
