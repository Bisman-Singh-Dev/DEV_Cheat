import sys
import threading
import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Optional, Callable

class DesktopOverlay:
    """
    Sleek, transparent cyber-HUD desktop overlay:
    1. Precision red bounding boxes around detected/snipped questions.
    2. Interactive 'B' key Snipping Mode: Drag mouse to cover question with a translucent red shaded box.
    3. Fully draggable/movable DEV Kit solution card with large, high-visibility typography.
    4. Smooth mousewheel scrolling and dismiss via 'Q' key or close button.
    """
    def __init__(
        self,
        on_solve_request: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_snip_completed: Optional[Callable[[int, int, int, int], None]] = None
    ):
        self.root: Optional[tk.Tk] = None
        self.canvas: Optional[tk.Canvas] = None
        self.on_solve_request = on_solve_request
        self.on_snip_completed = on_snip_completed

        self.questions: List[Dict[str, Any]] = []
        self.active_solution: Optional[Dict[str, Any]] = None
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self.transparent_color = "#000001"
        self._sol_frame: Optional[tk.Frame] = None

        # Remember user dragged window position
        self._sol_pos_x: Optional[int] = None
        self._sol_pos_y: Optional[int] = None

        # Snip mode state
        self.is_snipping = False
        self._snip_start_x: Optional[int] = None
        self._snip_start_y: Optional[int] = None
        self._snip_fill_win: Optional[tk.Toplevel] = None

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

            # Global hotkeys inside Tkinter
            self.root.bind("<Key-q>", lambda e: self.hide_responses())
            self.root.bind("<Key-Q>", lambda e: self.hide_responses())
            self.root.bind("<Key-b>", lambda e: self.toggle_snip_mode())
            self.root.bind("<Key-B>", lambda e: self.toggle_snip_mode())
            self.root.bind("<Escape>", lambda e: self.cancel_snip_mode())

            self._poll_updates()
            self.root.mainloop()
        except Exception as e:
            print(f"[Overlay] Error in Tkinter loop: {e}")

    def _poll_updates(self):
        if not self.is_running or not self.root:
            return
        self._redraw()
        self.root.after(150, self._poll_updates)

    def toggle_snip_mode(self):
        if self.is_snipping:
            self.cancel_snip_mode()
        else:
            self.start_snip_mode()

    def start_snip_mode(self):
        """Activates mouse drag selection mode over the screen."""
        if not self.root or not self.canvas:
            return
        self.is_snipping = True
        self._snip_start_x = None
        self._snip_start_y = None

        # Create the translucent shaded fill window if needed
        if not self._snip_fill_win:
            try:
                self._snip_fill_win = tk.Toplevel(self.root)
                self._snip_fill_win.overrideredirect(True)
                self._snip_fill_win.attributes("-topmost", True)
                self._snip_fill_win.attributes("-alpha", 0.28)  # Translucent shaded tint
                self._snip_fill_win.config(bg="#ff1a4b")  # Crimson/red translucent fill
                self._snip_fill_win.withdraw()
            except Exception as e:
                print(f"[Overlay] Snip fill window notice: {e}")

        # Crosshair cursor
        self.canvas.config(cursor="crosshair")

        # Bind mouse drag events for snipping
        self.canvas.bind("<ButtonPress-1>", self._on_snip_press)
        self.canvas.bind("<B1-Motion>", self._on_snip_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_snip_release)

        # Draw top notification banner
        screen_w = self.root.winfo_screenwidth()
        banner_w = 660
        banner_h = 38
        bx = (screen_w - banner_w) // 2

        self.canvas.delete("snip_banner")
        self.canvas.create_rectangle(
            bx, 10, bx + banner_w, 10 + banner_h,
            fill="#ff1a4b", outline="#ffffff", width=2,
            tags="snip_banner"
        )
        self.canvas.create_text(
            screen_w // 2, 29,
            text="🎯 DEV_CHEAT SNIP: Drag mouse to cover question in RED BOX | ESC to cancel",
            fill="#ffffff", font=("Segoe UI", 11, "bold"),
            tags="snip_banner"
        )
        print("[Dev_Cheat] Snipping Mode Active: Drag mouse across screen to cover question in RED BOX!")

    def cancel_snip_mode(self):
        """Cancels snip mode and restores normal cursor."""
        self.is_snipping = False
        self._snip_start_x = None
        self._snip_start_y = None
        if self._snip_fill_win:
            try:
                self._snip_fill_win.withdraw()
            except Exception:
                pass
        if self.canvas:
            self.canvas.config(cursor="")
            self.canvas.delete("snip_banner")
            self.canvas.delete("snip_rect")
            self.canvas.unbind("<ButtonPress-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
        print("[Dev_Cheat] Snipping Mode Cancelled.")

    def _on_snip_press(self, event):
        self._snip_start_x = event.x
        self._snip_start_y = event.y

    def _on_snip_motion(self, event):
        if not self.canvas or self._snip_start_x is None or self._snip_start_y is None:
            return

        x1 = min(self._snip_start_x, event.x)
        y1 = min(self._snip_start_y, event.y)
        x2 = max(self._snip_start_x, event.x)
        y2 = max(self._snip_start_y, event.y)
        w = max(1, x2 - x1)
        h = max(1, y2 - y1)

        # 1. TRANSLUCENT SHADED RECTANGLE COVERING THE AREA
        if self._snip_fill_win:
            try:
                self._snip_fill_win.geometry(f"{w}x{h}+{x1}+{y1}")
                self._snip_fill_win.deiconify()
            except Exception:
                pass

        # 2. CRISP RED BORDER ON CANVAS
        self.canvas.delete("snip_rect")
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="#ff1a4b", width=2,
            tags="snip_rect"
        )

        badge_w = 210
        badge_h = 22
        badge_y = max(4, y1 - badge_h)
        self.canvas.create_rectangle(
            x1, badge_y, x1 + badge_w, badge_y + badge_h,
            fill="#ff1a4b", outline="#ffffff", width=1,
            tags="snip_rect"
        )
        self.canvas.create_text(
            x1 + 8, badge_y + 11,
            text=f"🎯 Selected: {w} × {h}px",
            fill="#ffffff", font=("Segoe UI", 9, "bold"),
            anchor="w",
            tags="snip_rect"
        )

    def _on_snip_release(self, event):
        if not self.canvas or self._snip_start_x is None or self._snip_start_y is None:
            return

        x1 = min(self._snip_start_x, event.x)
        y1 = min(self._snip_start_y, event.y)
        x2 = max(self._snip_start_x, event.x)
        y2 = max(self._snip_start_y, event.y)
        w = x2 - x1
        h = y2 - y1

        self.cancel_snip_mode()

        if w >= 20 and h >= 20:
            # Lock the red box on screen immediately while solving!
            self.canvas.delete("snip_rect")
            self.canvas.delete("pending_snip")
            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline="#ff1a4b", width=3,
                tags=("q_box", "pending_snip")
            )
            badge_w = 260
            badge_h = 24
            badge_y = max(4, y1 - badge_h)
            self.canvas.create_rectangle(
                x1, badge_y, x1 + badge_w, badge_y + badge_h,
                fill="#ff1a4b", outline="#ffffff", width=1,
                tags=("q_badge", "pending_snip")
            )
            self.canvas.create_text(
                x1 + 8, badge_y + 12,
                text="⚡ Solving with Gemini Vision...",
                anchor="w",
                fill="#ffffff", font=("Segoe UI", 9, "bold"),
                tags=("q_badge", "pending_snip")
            )

            print(f"[Dev_Cheat] Red box locked: ({x1}, {y1}) to ({x2}, {y2}) -> {w}x{h}px. Solving...")
            if self.on_snip_completed:
                self.on_snip_completed(x1, y1, x2, y2)

    def update_questions(self, questions: List[Dict[str, Any]]):
        self.questions = questions

    def show_solution(self, solution: Dict[str, Any]):
        """Updates and displays the answer in the movable DEV Kit window immediately."""
        self.active_solution = solution
        # Clear pending snip placeholder if any
        if self.canvas:
            self.canvas.delete("pending_snip")

        # Force re-render of solution widget with fresh answer
        if self._sol_frame:
            try:
                self._sol_frame.destroy()
                self._sol_frame = None
            except Exception:
                pass
        self._render_solution_widget(solution)

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
            self.canvas.delete("pending_snip")
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

        # Do not wipe canvas elements if user is currently dragging snip box
        if not self.is_snipping:
            self.canvas.delete("q_box")
            self.canvas.delete("q_badge")

            # Draw red bounding boxes around detected physics/math questions
            for q in self.questions:
                bbox = q.get("bbox", [0, 0, 0, 0])
                x, y, w, h = bbox
                if w <= 10 or h <= 10:
                    continue

                has_solution = bool(q.get("solution"))
                box_color = "#ff1a4b"

                # Crisp red bounding box
                rect_id = self.canvas.create_rectangle(
                    x, y, x + w, y + h,
                    outline=box_color,
                    width=3,
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

                badge_w = min(380, len(badge_text) * 8 + 20)
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
        """
        Renders a fully DRAGGABLE / MOVABLE, enlarged, highly legible,
        scrollable dark glassmorphic solution card.
        """
        if not self.root:
            return

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # Enlarged dimensions for clear reading
        card_w = min(780, screen_w - 60)
        card_h = min(560, screen_h - 100)

        # Default position or restore previous dragged position
        pos_x = self._sol_pos_x if self._sol_pos_x is not None else max(20, screen_w - card_w - 30)
        pos_y = self._sol_pos_y if self._sol_pos_y is not None else 50

        # Frame container with glowing cyan border
        frame = tk.Frame(
            self.root,
            bg="#090d16",
            highlightthickness=2,
            highlightbackground="#00f2fe",
            highlightcolor="#00f2fe"
        )
        frame.place(x=pos_x, y=pos_y, width=card_w, height=card_h)
        self._sol_frame = frame

        # TOP HEADER BAR - FULLY DRAGGABLE
        header = tk.Frame(frame, bg="#131926", height=42, cursor="fleur")
        header.pack(fill=tk.X, side=tk.TOP)

        hdr_lbl = tk.Label(
            header,
            text="⚡ DEV_CHEAT SOLUTION  ✥ (Drag to Move)",
            fg="#00f2fe",
            bg="#131926",
            font=("Segoe UI", 12, "bold"),
            cursor="fleur"
        )
        hdr_lbl.pack(side=tk.LEFT, padx=14, pady=8)

        dismiss_hint = tk.Label(
            header,
            text="[Press 'Q' to Dismiss | 'B' to Snip]",
            fg="#94a3b8",
            bg="#131926",
            font=("Consolas", 10),
            cursor="fleur"
        )
        dismiss_hint.pack(side=tk.LEFT, padx=8, pady=8)

        close_btn = tk.Label(
            header,
            text="✕",
            fg="#ff5555",
            bg="#131926",
            font=("Segoe UI", 14, "bold"),
            cursor="hand2"
        )
        close_btn.pack(side=tk.RIGHT, padx=14, pady=6)
        close_btn.bind("<Button-1>", lambda e: self.hide_responses())

        # DRAG LOGIC TO MOVE THE DEV KIT WINDOW FREELY
        def _start_drag(event):
            frame._drag_start_x = event.x
            frame._drag_start_y = event.y

        def _do_drag(event):
            dx = event.x - frame._drag_start_x
            dy = event.y - frame._drag_start_y
            cur_x = frame.winfo_x()
            cur_y = frame.winfo_y()
            new_x = cur_x + dx
            new_y = cur_y + dy
            self._sol_pos_x = new_x
            self._sol_pos_y = new_y
            frame.place(x=new_x, y=new_y)

        header.bind("<Button-1>", _start_drag)
        header.bind("<B1-Motion>", _do_drag)
        hdr_lbl.bind("<Button-1>", _start_drag)
        hdr_lbl.bind("<B1-Motion>", _do_drag)
        dismiss_hint.bind("<Button-1>", _start_drag)
        dismiss_hint.bind("<B1-Motion>", _do_drag)

        # DIRECT ANSWER HERO BOX (Large, bold, high-contrast)
        ans_box = tk.Frame(frame, bg="#111827", padx=16, pady=12)
        ans_box.pack(fill=tk.X, padx=14, pady=(12, 8))

        ans_title = tk.Label(
            ans_box,
            text="DIRECT ANSWER:",
            fg="#38bdf8",
            bg="#111827",
            font=("Consolas", 11, "bold")
        )
        ans_title.pack(anchor="w")

        direct_ans = sol.get("direct_answer", "Solved")
        ans_val = tk.Label(
            ans_box,
            text=direct_ans,
            fg="#4ade80",
            bg="#111827",
            font=("Segoe UI", 16, "bold"),
            wraplength=card_w - 50,
            justify="left"
        )
        ans_val.pack(anchor="w", pady=(3, 0))

        # Derivation Section Header
        der_header = tk.Label(
            frame,
            text="STEP-BY-STEP DERIVATION (Scroll with Mousewheel):",
            fg="#94a3b8",
            bg="#090d16",
            font=("Consolas", 10, "bold")
        )
        der_header.pack(anchor="w", padx=16, pady=(4, 2))

        # Scrollable Text Container
        text_container = tk.Frame(frame, bg="#090d16")
        text_container.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))

        scrollbar = tk.Scrollbar(text_container, orient=tk.VERTICAL, width=14)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        txt_widget = tk.Text(
            text_container,
            bg="#111827",
            fg="#f8fafc",
            font=("Consolas", 12),
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            relief=tk.FLAT,
            padx=14,
            pady=12,
            spacing1=3,
            spacing3=4
        )
        txt_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=txt_widget.yview)

        # Smooth mousewheel scroll binding
        def _on_mousewheel(event):
            txt_widget.yview_scroll(int(-1 * (event.delta / 120)), "units")

        txt_widget.bind("<MouseWheel>", _on_mousewheel)
        frame.bind("<MouseWheel>", _on_mousewheel)

        # Tag configurations for large, clear syntax highlighted steps
        txt_widget.tag_config("step_header", foreground="#38bdf8", font=("Consolas", 13, "bold"))
        txt_widget.tag_config("final_res", foreground="#4ade80", font=("Consolas", 14, "bold"))
        txt_widget.tag_config("body", foreground="#f8fafc", font=("Consolas", 12))

        # Clean math and latex symbols
        raw_exp = sol.get("explanation", "").strip()
        clean_exp = (
            raw_exp.replace("$", "")
            .replace("\\implies", "=>")
            .replace("\\cdot", "*")
            .replace("\\times", "*")
            .replace("\\approx", "~")
            .replace("\\frac", "")
            .replace("\\sqrt", "sqrt")
            .replace("\\int", "integral")
            .replace("\\alpha", "alpha")
            .replace("\\beta", "beta")
            .replace("\\theta", "theta")
            .replace("\\propto", "proportional to")
        )

        lines = clean_exp.split("\n")
        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                txt_widget.insert(tk.END, "\n")
                continue

            if any(trimmed.lower().startswith(p) for p in [
                "step 1", "step 2", "step 3", "step 4", "step 5",
                "given:", "principle:", "formula:"
            ]):
                txt_widget.insert(tk.END, f"{trimmed}\n", "step_header")
            elif any(trimmed.lower().startswith(p) for p in [
                "final answer", "final result", "conclusion"
            ]):
                txt_widget.insert(tk.END, f"\n{trimmed}\n", "final_res")
            else:
                txt_widget.insert(tk.END, f"{trimmed}\n", "body")

        txt_widget.config(state=tk.DISABLED)

    def _on_box_clicked(self, question: Dict[str, Any]):
        print(f"[Dev_Cheat] Question box clicked: {question.get('id')}")
        if question.get("solution"):
            self.show_solution(question["solution"])
        elif self.on_solve_request:
            self.on_solve_request(question)

    def stop(self):
        self.is_running = False
        if self._snip_fill_win:
            try:
                self._snip_fill_win.destroy()
            except Exception:
                pass
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
