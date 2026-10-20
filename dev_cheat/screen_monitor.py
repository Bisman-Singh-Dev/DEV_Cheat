import time
import asyncio
import hashlib
import threading
from typing import List, Dict, Any, Optional, Callable
from PIL import Image

from .config import config
from .ocr_engine import ocr_engine
from .question_detector import question_detector, QuestionBlock
from .solver import solver
from .overlay import desktop_overlay

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

class ScreenMonitor:
    def __init__(self):
        self.is_running = False
        self.is_paused = False
        self._thread: Optional[threading.Thread] = None
        self._last_hash = ""
        self._last_solved_question_hash = ""
        self.last_screenshot: Optional[Image.Image] = None
        self.current_questions: List[QuestionBlock] = []
        self.last_solution: Optional[Dict[str, Any]] = None
        self.status = "stopped"  # 'idle', 'scanning', 'solving', 'stopped'

        # Event callbacks
        self.listeners: List[Callable[[str, Any], None]] = []

        # Hook overlay solve request
        desktop_overlay.on_solve_request = self.solve_question

        # Setup keyboard listener
        self._setup_hotkeys()

    def _setup_hotkeys(self):
        if not HAS_PYNPUT:
            return

        def on_press(key):
            try:
                char = getattr(key, 'char', None)
                if char in ('q', 'Q'):
                    self.handle_q_key()
                elif char in ('s', 'S'):
                    print("[Dev_Cheat] Manual Scan triggered via 'S' hotkey.")
                    self.trigger_scan_now()
                elif char in ('c', 'C'):
                    print("[Dev_Cheat] Cleared highlights via 'C' hotkey.")
                    self.clear_all()
            except Exception:
                pass

        try:
            self._kb_listener = keyboard.Listener(on_press=on_press)
            self._kb_listener.daemon = True
            self._kb_listener.start()
        except Exception as e:
            print(f"[Dev_Cheat] Keyboard listener notice: {e}")

    def handle_q_key(self):
        """User pressed 'Q': Hide all active responses."""
        print("[Dev_Cheat] 'Q' pressed -> Hiding responses and resetting overlays.")
        self.last_solution = None
        desktop_overlay.hide_responses()
        self._emit("hide_responses", {})

    def add_listener(self, callback: Callable[[str, Any], None]):
        self.listeners.append(callback)

    def _emit(self, event_type: str, data: Any):
        for cb in self.listeners:
            try:
                cb(event_type, data)
            except Exception as e:
                print(f"[Monitor] Callback error: {e}")

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.status = "idle"
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

        if config.enable_desktop_overlay:
            desktop_overlay.start()

    def stop(self):
        self.is_running = False
        self.status = "stopped"
        desktop_overlay.stop()

    def pause(self):
        self.is_paused = True
        self.status = "paused"
        self._emit("status_change", {"status": self.status})

    def resume(self):
        self.is_paused = False
        self.status = "idle"
        self._emit("status_change", {"status": self.status})

    def clear_all(self):
        self.current_questions = []
        self.last_solution = None
        self._last_solved_question_hash = ""
        desktop_overlay.clear()
        self._emit("clear", {})

    def trigger_scan_now(self):
        self._last_hash = ""  # Force re-scan

    def _monitor_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self.is_running:
            if not self.is_paused:
                try:
                    loop.run_until_complete(self._perform_scan())
                except Exception as e:
                    print(f"[Monitor Loop Error]: {e}")
            time.sleep(config.scan_interval)

    async def _perform_scan(self):
        # 1. Grab screen
        screen = ocr_engine.capture_screen()
        self.last_screenshot = screen

        # 2. Check if screen changed significantly (fast thumbnail hash)
        thumb = screen.resize((120, 75))
        curr_hash = hashlib.md5(thumb.tobytes()).hexdigest()
        if curr_hash == self._last_hash:
            return  # No change on screen
        self._last_hash = curr_hash

        self.status = "scanning"
        self._emit("status_change", {"status": "scanning"})

        # 3. Perform OCR
        ocr_result = await ocr_engine.recognize(screen)

        # 4. Detect Questions
        detected = question_detector.detect(ocr_result)
        self.current_questions = detected

        questions_dict = [q.to_dict() for q in detected]

        # 5. Handle Single vs Multiple questions
        q_count = len(detected)
        self._emit("questions_detected", {
            "count": q_count,
            "questions": questions_dict
        })

        # Update overlay with red bounding boxes
        desktop_overlay.update_questions(questions_dict)

        if q_count == 0:
            self.status = "idle"
            self._emit("status_change", {"status": "idle"})
            return

        if q_count == 1:
            # Single Question -> Instantly solve
            q = detected[0]
            q_hash = hashlib.md5(q.text.encode()).hexdigest()

            # Prevent re-solving same question repeatedly
            if config.auto_solve_single and q_hash != self._last_solved_question_hash:
                print(f"[Dev_Cheat] Single question detected! Solving automatically: {q.title}")
                self.status = "solving"
                self._emit("status_change", {"status": "solving", "target": q.title})
                self.solve_question(q.to_dict())
                self._last_solved_question_hash = q_hash
            else:
                self.status = "idle"
        else:
            # Multiple Questions -> Red boxes rendered, waiting for user click!
            print(f"[Dev_Cheat] Detected {q_count} questions on screen! Red boxes placed. Click any question or press hotkey to solve.")
            self.status = "idle"

        self._emit("status_change", {"status": "idle"})

    def solve_question(self, question_data: Dict[str, Any]):
        """Solves a specified question (either auto-detected single or user-clicked)."""
        q_id = question_data.get("id", "q")
        q_text = question_data.get("text", "")
        q_type = question_data.get("type", "general")
        options = question_data.get("options", [])

        print(f"[Dev_Cheat] Solving question {q_id} ({q_type}): {q_text[:80]}...")
        self.status = "solving"
        self._emit("status_change", {"status": "solving", "target": q_id})

        solution = solver.solve(q_text, q_type, options)
        solution["question_id"] = q_id
        self.last_solution = solution

        # Update overlay with floating solution card
        desktop_overlay.show_solution(solution)

        # Broadcast solution to web dashboard
        self._emit("solved", {
            "question": question_data,
            "solution": solution
        })

        self.status = "idle"
        self._emit("status_change", {"status": "idle"})
        return solution

screen_monitor = ScreenMonitor()
