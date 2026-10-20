import asyncio
import sys
from typing import List, Dict, Any, Optional
from PIL import Image, ImageGrab
import winocr

try:
    import win32service, win32gui, win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class OcrEngine:
    def __init__(self, lang: str = "en"):
        self.lang = lang
        self._ensure_desktop_access()

    def _ensure_desktop_access(self):
        """Attaches to default window station if running in a detached context."""
        if HAS_WIN32 and sys.platform == "win32":
            try:
                hwinsta = win32service.OpenWindowStation("winsta0", False, win32con.MAXIMUM_ALLOWED)
                hwinsta.SetProcessWindowStation()
                hdesk = win32service.OpenDesktop("default", 0, False, win32con.MAXIMUM_ALLOWED)
                hdesk.SetThreadDesktop()
            except Exception:
                pass

    def capture_screen(self, bbox: Optional[tuple] = None) -> Image.Image:
        """Captures the active screen or a specific region."""
        self._ensure_desktop_access()
        try:
            return ImageGrab.grab(bbox=bbox, all_screens=True)
        except Exception:
            # Fallback
            return ImageGrab.grab(bbox=bbox)

    async def recognize(self, image: Image.Image) -> Dict[str, Any]:
        """
        Runs OCR on the given image and extracts lines with computed bounding boxes.
        Each line has:
          - text: str
          - bbox: [x, y, width, height]
          - words: list of word bounding boxes
        """
        try:
            result = await winocr.recognize_pil(image, self.lang)
        except Exception as e:
            return {
                "text": "",
                "lines": [],
                "error": str(e)
            }

        extracted_lines = []
        for line in result.lines:
            line_text = line.text.strip()
            if not line_text:
                continue

            words_data = []
            min_x = float("inf")
            min_y = float("inf")
            max_r = 0.0
            max_b = 0.0

            for word in line.words:
                rect = word.bounding_rect
                w_x, w_y, w_w, w_h = rect.x, rect.y, rect.width, rect.height
                words_data.append({
                    "text": word.text,
                    "bbox": [round(w_x, 1), round(w_y, 1), round(w_w, 1), round(w_h, 1)]
                })
                min_x = min(min_x, w_x)
                min_y = min(min_y, w_y)
                max_r = max(max_r, w_x + w_w)
                max_b = max(max_b, w_y + w_h)

            if min_x == float("inf"):
                line_bbox = [0, 0, 0, 0]
            else:
                line_bbox = [
                    round(min_x, 1),
                    round(min_y, 1),
                    round(max_r - min_x, 1),
                    round(max_b - min_y, 1)
                ]

            extracted_lines.append({
                "text": line_text,
                "bbox": line_bbox,
                "words": words_data
            })

        return {
            "text": result.text,
            "lines": extracted_lines,
            "width": image.width,
            "height": image.height
        }

ocr_engine = OcrEngine()
