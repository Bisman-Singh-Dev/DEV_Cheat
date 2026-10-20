import sys
import threading
import tkinter as tk
from typing import List, Dict, Any, Optional, Callable

class DesktopOverlay:
    """
    Transparent, borderless overlay window that draws red boxes around detected questions
    and displays floating solution cards on the user's screen.
    """
    def __init__(self, on_solve_request: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.root: Optional[tk.Tk] = None
        self.canvas: Optional[tk.Canvas] = None
        self.on_solve_request = on_solve_request
        self.questions: List[Dict[str, Any]] = []
        self.active_solution: Optional[Dict[str, Any]] = None
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self.transparent_color = "#000001"

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._run_tk, daemon=True)
        self._thread.start()

    def _run_tk(self):
        try:
            self.root = tk.Tk()
            self.root.title("Dev_Cheat HUD")
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)

            # Screen geometry
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            self.root.geometry(f"{screen_width}x{screen_height}+0+0")

            # Setup transparency
            if sys.platform == "win32":
                self.root.config(bg=self.transparent_color)
                self.root.attributes("-transparentcolor", self.transparent_color)
            else:
                self.root.attributes("-alpha", 0.85)

            self.canvas = tk.Canvas(
                self.root,
                width=screen_width,
                height=screen_height,
                bg=self.transparent_color,
                highlightthickness=0
            )
            self.canvas.pack(fill=tk.BOTH, expand=True)

            # Keybindings: Pressing 'Q' hides the solution overlays
            self.root.bind("<Key-q>", lambda e: self.hide_responses())
            self.root.bind("<Key-Q>", lambda e: self.hide_responses())
            self.root.bind("<Escape>", lambda e: self.hide_responses())

            self._poll_updates()
            self.root.mainloop()
        except Exception as e:
            print(f"[Overlay] Error in Tkinter loop: {e}")

    def _poll_updates(self):
        if not self.is_running or not self.root:
            return
        self._redraw()
        self.root.after(200, self._poll_updates)

    def update_questions(self, questions: List[Dict[str, Any]]):
        self.questions = questions

    def show_solution(self, solution: Dict[str, Any]):
        self.active_solution = solution

    def hide_responses(self):
        """User pressed 'Q': Hide all open response boxes/solutions."""
        self.active_solution = None
        if self.canvas:
            self.canvas.delete("solution_tag")
        print("[Dev_Cheat] Response hidden via 'Q' key.")

    def clear(self):
        self.questions = []
        self.active_solution = None
        if self.canvas:
            self.canvas.delete("all")

    def _redraw(self):
        if not self.canvas:
            return

        self.canvas.delete("all")

        # Draw red bounding boxes around detected questions
        for q in self.questions:
            bbox = q.get("bbox", [0, 0, 0, 0])
            x, y, w, h = bbox
            if w <= 0 or h <= 0:
                continue

            # Draw outer glow / shadow
            self.canvas.create_rectangle(
                x - 2, y - 2, x + w + 2, y + h + 2,
                outline="#ff0055",
                width=1,
                tags="q_box"
            )
            # Main Red Box
            rect_id = self.canvas.create_rectangle(
                x, y, x + w, y + h,
                outline="#ff2244",
                width=3,
                tags="q_box"
            )

            # Badge / Label on top of red box
            badge_text = f"🎯 {q.get('id', 'Q').upper()}: Click to Solve"
            badge_w = len(badge_text) * 8 + 16
            badge_h = 24
            badge_y = max(4, y - badge_h)

            bg_id = self.canvas.create_rectangle(
                x, badge_y, x + badge_w, badge_y + badge_h,
                fill="#ff2244",
                outline="#ffffff",
                width=1,
                tags="q_badge"
            )
            txt_id = self.canvas.create_text(
                x + 8, badge_y + 12,
                text=badge_text,
                anchor="w",
                fill="#ffffff",
                font=("Consolas", 10, "bold"),
                tags="q_badge"
            )

            # Bind click event on the question box or badge
            def make_handler(target_q=q):
                return lambda event: self._on_box_clicked(target_q)

            self.canvas.tag_bind(rect_id, "<Button-1>", make_handler(q))
            self.canvas.tag_bind(bg_id, "<Button-1>", make_handler(q))
            self.canvas.tag_bind(txt_id, "<Button-1>", make_handler(q))

        # Draw active floating solution card if available
        if self.active_solution:
            self._draw_solution_card(self.active_solution)

    def _draw_solution_card(self, sol: Dict[str, Any]):
        if not self.canvas:
            return

        # Position solution card centered or near top right
        card_w = 540
        card_h = 320
        screen_w = self.canvas.winfo_width() or 1920
        card_x = max(20, screen_w - card_w - 40)
        card_y = 60

        # Background card (dark semi-opaque theme)
        self.canvas.create_rectangle(
            card_x, card_y, card_x + card_w, card_y + card_h,
            fill="#0f111a",
            outline="#00ffcc",
            width=2,
            tags="solution_tag"
        )

        # Header bar
        self.canvas.create_rectangle(
            card_x, card_y, card_x + card_w, card_y + 36,
            fill="#1a1d2e",
            outline="#00ffcc",
            width=1,
            tags="solution_tag"
        )
        self.canvas.create_text(
            card_x + 14, card_y + 18,
            text="⚡ DEV_CHEAT SOLUTION  (Press 'Q' to dismiss)",
            anchor="w",
            fill="#00ffcc",
            font=("Segoe UI", 10, "bold"),
            tags="solution_tag"
        )

        # Close [X] button
        close_btn = self.canvas.create_text(
            card_x + card_w - 20, card_y + 18,
            text="✕",
            fill="#ff4466",
            font=("Segoe UI", 12, "bold"),
            tags="solution_tag"
        )
        self.canvas.tag_bind(close_btn, "<Button-1>", lambda e: self.hide_responses())

        # Direct Answer Section
        direct_ans = sol.get("direct_answer", "")
        self.canvas.create_text(
            card_x + 16, card_y + 60,
            text="DIRECT ANSWER:",
            anchor="w",
            fill="#8892b0",
            font=("Consolas", 9, "bold"),
            tags="solution_tag"
        )
        self.canvas.create_text(
            card_x + 16, card_y + 85,
            text=direct_ans[:80],
            anchor="w",
            fill="#50fa7b",
            font=("Segoe UI", 12, "bold"),
            tags="solution_tag"
        )

        # Complexity / Badges
        tc = sol.get("time_complexity", "")
        sc = sol.get("space_complexity", "")
        if tc or sc:
            badge_info = f"Time: {tc or 'N/A'}  |  Space: {sc or 'N/A'}"
            self.canvas.create_text(
                card_x + 16, card_y + 115,
                text=badge_info,
                anchor="w",
                fill="#f1fa8c",
                font=("Consolas", 9),
                tags="solution_tag"
            )

        # Code or Explanation
        code = sol.get("code", "").strip()
        explanation = sol.get("explanation", "").strip()

        if code:
            self.canvas.create_rectangle(
                card_x + 14, card_y + 135, card_x + card_w - 14, card_y + card_h - 16,
                fill="#161824",
                outline="#2d3148",
                tags="solution_tag"
            )
            # Preview first 5 lines of code
            code_lines = code.split("\n")[:6]
            preview_code = "\n".join(code_lines)
            self.canvas.create_text(
                card_x + 22, card_y + 145,
                text=preview_code,
                anchor="nw",
                fill="#f8f8f2",
                font=("Consolas", 9),
                tags="solution_tag"
            )
        elif explanation:
            self.canvas.create_text(
                card_x + 16, card_y + 150,
                text=explanation[:300],
                anchor="nw",
                width=card_w - 32,
                fill="#ccd6f6",
                font=("Segoe UI", 10),
                tags="solution_tag"
            )

    def _on_box_clicked(self, question: Dict[str, Any]):
        print(f"[Dev_Cheat] Question box clicked: {question.get('id')}")
        if self.on_solve_request:
            self.on_solve_request(question)

    def stop(self):
        self.is_running = False
        if self.root:
            try:
                self.root.quit()
            except Exception:
                pass

desktop_overlay = DesktopOverlay()
