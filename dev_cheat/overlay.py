import sys
import threading
import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Optional, Callable

class DesktopOverlay:
    """
    Sleek, transparent cyber-HUD desktop overlay:
    1. Precision bounding boxes around detected physics/math questions.
    2. Interactive click-to-solve badges and box triggers.
    3. Glassmorphic, scrollable solution card with step-by-step numbered derivations.
    4. Dismiss via 'Q' key or close button.
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
        self._sol_frame: Optional[tk.Frame] = None

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

            # Full screen geometry
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            self.root.geometry(f"{screen_width}x{screen_height}+0+0")

            if sys.platform == "win32":
                self.root.config(bg=self.transparent_color)
                self.root.attributes("-transparentcolor", self.transparent_color)
            else:
                self.root.attributes("-alpha", 0.90)

            self.canvas = tk.Canvas(
                self.root,
                width=screen_width,
                height=screen_height,
                bg=self.transparent_color,
                highlightthickness=0
            )
            self.canvas.pack(fill=tk.BOTH, expand=True)

            # Hotkeys inside Tkinter
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
        self.root.after(150, self._poll_updates)

    def update_questions(self, questions: List[Dict[str, Any]]):
        self.questions = questions

    def show_solution(self, solution: Dict[str, Any]):
        self.active_solution = solution
        # Force re-render of solution widget on next poll
        if self._sol_frame:
            try:
                self._sol_frame.destroy()
                self._sol_frame = None
            except Exception:
                pass

    def hide_responses(self):
        """User pressed 'Q': Hide all open response boxes/solutions."""
        self.active_solution = None
        if self._sol_frame:
            try:
                self._sol_frame.destroy()
                self._sol_frame = None
            except Exception:
                pass
        if self.canvas:
            self.canvas.delete("solution_tag")
        print("[Dev_Cheat] Solution card dismissed via 'Q' key.")

    def clear(self):
        self.questions = []
        self.active_solution = None
        if self._sol_frame:
            try:
                self._sol_frame.destroy()
                self._sol_frame = None
            except Exception:
                pass
        if self.canvas:
            self.canvas.delete("all")

    def _redraw(self):
        if not self.canvas:
            return

        self.canvas.delete("q_box")
        self.canvas.delete("q_badge")

        # Draw red bounding boxes around detected physics/math questions
        for q in self.questions:
            bbox = q.get("bbox", [0, 0, 0, 0])
            x, y, w, h = bbox
            if w <= 10 or h <= 10:
                continue

            has_solution = bool(q.get("solution"))
            box_color = "#00ffcc" if has_solution else "#ff1a4b"

            # Outer crisp bounding box
            rect_id = self.canvas.create_rectangle(
                x, y, x + w, y + h,
                outline=box_color,
                width=2,
                tags="q_box"
            )

            # Interactive Badge on top edge
            q_label = q.get("title", q.get("id", "Q")).split(":")[0].strip()
            if has_solution:
                direct = q["solution"].get("direct_answer", "Solved")
                badge_text = f"⚡ {q_label}: {direct[:25]}"
                badge_bg = "#00b894"
            else:
                badge_text = f"🎯 {q_label}: Click to Solve"
                badge_bg = "#ff1a4b"

            badge_w = min(360, len(badge_text) * 8 + 18)
            badge_h = 24
            badge_y = max(4, y - badge_h)

            bg_id = self.canvas.create_rectangle(
                x, badge_y, x + badge_w, badge_y + badge_h,
                fill=badge_bg,
                outline="#ffffff",
                width=1,
                tags="q_badge"
            )
            txt_id = self.canvas.create_text(
                x + 9, badge_y + 12,
                text=badge_text,
                anchor="w",
                fill="#ffffff",
                font=("Segoe UI", 9, "bold"),
                tags="q_badge"
            )

            # Click handlers
            def make_handler(target_q=q):
                return lambda event: self._on_box_clicked(target_q)

            self.canvas.tag_bind(rect_id, "<Button-1>", make_handler(q))
            self.canvas.tag_bind(bg_id, "<Button-1>", make_handler(q))
            self.canvas.tag_bind(txt_id, "<Button-1>", make_handler(q))

        # Render floating solution card if active and not yet drawn
        if self.active_solution and not self._sol_frame:
            self._render_solution_widget(self.active_solution)

    def _render_solution_widget(self, sol: Dict[str, Any]):
        """Renders an ultra-sleek, scrollable dark glassmorphic solution card."""
        if not self.root:
            return

        card_w = 600
        card_h = 420
        screen_w = self.root.winfo_screenwidth()
        pos_x = max(20, screen_w - card_w - 30)
        pos_y = 50

        # Frame container with glowing cyan border
        frame = tk.Frame(
            self.root,
            bg="#0d111a",
            highlightthickness=2,
            highlightbackground="#00f2fe",
            highlightcolor="#00f2fe"
        )
        frame.place(x=pos_x, y=pos_y, width=card_w, height=card_h)
        self._sol_frame = frame

        # Top Header Bar
        header = tk.Frame(frame, bg="#161b26", height=38)
        header.pack(fill=tk.X, side=tk.TOP)

        hdr_lbl = tk.Label(
            header,
            text="⚡ DEV_CHEAT SOLUTION",
            fg="#00f2fe",
            bg="#161b26",
            font=("Segoe UI", 10, "bold")
        )
        hdr_lbl.pack(side=tk.LEFT, padx=12, pady=7)

        dismiss_hint = tk.Label(
            header,
            text="[Press 'Q' to Dismiss]",
            fg="#8b949e",
            bg="#161b26",
            font=("Consolas", 9)
        )
        dismiss_hint.pack(side=tk.LEFT, padx=6, pady=7)

        close_btn = tk.Label(
            header,
            text="✕",
            fg="#ff5555",
            bg="#161b26",
            font=("Segoe UI", 12, "bold"),
            cursor="hand2"
        )
        close_btn.pack(side=tk.RIGHT, padx=12, pady=6)
        close_btn.bind("<Button-1>", lambda e: self.hide_responses())

        # Direct Answer Hero Box
        ans_box = tk.Frame(frame, bg="#141924", padx=14, pady=10)
        ans_box.pack(fill=tk.X, padx=12, pady=(10, 6))

        ans_title = tk.Label(
            ans_box,
            text="DIRECT ANSWER:",
            fg="#38bdf8",
            bg="#141924",
            font=("Consolas", 9, "bold")
        )
        ans_title.pack(anchor="w")

        direct_ans = sol.get("direct_answer", "Solved")
        ans_val = tk.Label(
            ans_box,
            text=direct_ans,
            fg="#4ade80",
            bg="#141924",
            font=("Segoe UI", 13, "bold"),
            wraplength=card_w - 50,
            justify="left"
        )
        ans_val.pack(anchor="w", pady=(2, 0))

        # Derivation Section Header
        der_header = tk.Label(
            frame,
            text="STEP-BY-STEP DERIVATION (Scroll with Mousewheel):",
            fg="#8b949e",
            bg="#0d111a",
            font=("Consolas", 8, "bold")
        )
        der_header.pack(anchor="w", padx=14, pady=(4, 2))

        # Scrollable Text Container
        text_container = tk.Frame(frame, bg="#0d111a")
        text_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        scrollbar = tk.Scrollbar(text_container, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        txt_widget = tk.Text(
            text_container,
            bg="#141924",
            fg="#e6edf3",
            font=("Consolas", 10),
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            relief=tk.FLAT,
            padx=12,
            pady=10
        )
        txt_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=txt_widget.yview)

        # Mousewheel scroll binding for smooth scrolling anywhere on the card
        def _on_mousewheel(event):
            txt_widget.yview_scroll(int(-1 * (event.delta / 120)), "units")

        txt_widget.bind("<MouseWheel>", _on_mousewheel)
        frame.bind("<MouseWheel>", _on_mousewheel)

        # Tag configurations for syntax highlighting steps
        txt_widget.tag_config("step_header", foreground="#38bdf8", font=("Consolas", 10, "bold"))
        txt_widget.tag_config("final_res", foreground="#4ade80", font=("Consolas", 10, "bold"))
        txt_widget.tag_config("body", foreground="#f0f6fc", font=("Consolas", 10))

        # Format and insert explanation cleanly line by line
        raw_exp = sol.get("explanation", "").strip()
        # Clean latex symbols
        clean_exp = (
            raw_exp.replace("$", "")
            .replace("\\implies", "=>")
            .replace("\\cdot", "*")
            .replace("\\times", "*")
            .replace("\\approx", "~")
            .replace("\\frac", "")
            .replace("\\propto", "proportional to")
        )

        lines = clean_exp.split("\n")
        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                txt_widget.insert(tk.END, "\n")
                continue

            if any(trimmed.lower().startswith(p) for p in ["step 1", "step 2", "step 3", "step 4", "step 5", "given:", "principle:"]):
                txt_widget.insert(tk.END, f"{trimmed}\n", "step_header")
            elif any(trimmed.lower().startswith(p) for p in ["final answer", "final result", "conclusion"]):
                txt_widget.insert(tk.END, f"\n{trimmed}\n", "final_res")
            else:
                txt_widget.insert(tk.END, f"{trimmed}\n", "body")

        txt_widget.config(state=tk.DISABLED)

    def _on_box_clicked(self, question: Dict[str, Any]):
        print(f"[Dev_Cheat] Question box clicked: {question.get('id')}")
        # If solution already embedded in question, show it immediately!
        if question.get("solution"):
            self.show_solution(question["solution"])
        elif self.on_solve_request:
            self.on_solve_request(question)

    def stop(self):
        self.is_running = False
        if self._sol_frame:
            try:
                self._sol_frame.destroy()
            except Exception:
                pass
        if self.root:
            try:
                self.root.quit()
            except Exception:
                pass

desktop_overlay = DesktopOverlay()
