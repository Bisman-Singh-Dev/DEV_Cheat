import io
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

from .config import config, WEB_DIR
from .screen_monitor import screen_monitor
from .solver import solver

app = FastAPI(title="Dev_Cheat API", version="1.0.0")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# Forward monitor events to websockets
def on_monitor_event(event_type: str, data: Any):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(manager.broadcast({"type": event_type, "data": data}))
    except Exception:
        pass

screen_monitor.add_listener(on_monitor_event)

class SolveRequest(BaseModel):
    id: Optional[str] = None
    text: Optional[str] = None
    type: Optional[str] = "general"
    options: Optional[List[str]] = []

class ConfigUpdateRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    scan_interval: Optional[float] = None
    auto_solve_single: Optional[bool] = None
    enable_desktop_overlay: Optional[bool] = None

@app.get("/api/status")
async def get_status():
    return {
        "status": screen_monitor.status,
        "is_paused": screen_monitor.is_paused,
        "is_running": screen_monitor.is_running,
        "questions_count": len(screen_monitor.current_questions),
        "has_active_solution": screen_monitor.last_solution is not None,
        "config": {
            "gemini_model": config.gemini_model,
            "scan_interval": config.scan_interval,
            "auto_solve_single": config.auto_solve_single,
            "has_api_key": bool(config.gemini_api_key),
            "enable_desktop_overlay": config.enable_desktop_overlay
        }
    }

@app.get("/api/questions")
async def get_questions():
    return [q.to_dict() for q in screen_monitor.current_questions]

@app.post("/api/scan")
async def trigger_scan():
    screen_monitor.trigger_scan_now()
    return {"status": "scanning_triggered"}

@app.post("/api/hide")
async def hide_responses():
    screen_monitor.handle_q_key()
    return {"status": "responses_hidden"}

@app.post("/api/clear")
async def clear_all():
    screen_monitor.clear_all()
    return {"status": "cleared"}

@app.post("/api/toggle-monitor")
async def toggle_monitor():
    if screen_monitor.is_paused:
        screen_monitor.resume()
    else:
        screen_monitor.pause()
    return {"is_paused": screen_monitor.is_paused, "status": screen_monitor.status}

@app.post("/api/solve")
async def solve_endpoint(req: SolveRequest):
    # If ID is provided, look in current detected questions
    target_q = None
    if req.id:
        for q in screen_monitor.current_questions:
            if q.id == req.id:
                target_q = q.to_dict()
                break

    if not target_q:
        if not req.text:
            raise HTTPException(status_code=400, detail="Missing question text or invalid ID")
        target_q = {
            "id": req.id or "custom",
            "text": req.text,
            "type": req.type or "general",
            "options": req.options or []
        }

    solution = screen_monitor.solve_question(target_q)
    return {"question": target_q, "solution": solution}

@app.get("/api/history")
async def get_history():
    return solver.get_history()

@app.delete("/api/history")
async def clear_history():
    solver.clear_history()
    return {"status": "history_cleared"}

@app.get("/api/screenshot")
async def get_screenshot():
    if not screen_monitor.last_screenshot:
        # Capture on the fly
        from .ocr_engine import ocr_engine
        screen_monitor.last_screenshot = ocr_engine.capture_screen()

    buf = io.BytesIO()
    # Compress lightly for fast localhost transmission
    screen_monitor.last_screenshot.save(buf, format="JPEG", quality=75)
    return Response(content=buf.getvalue(), media_type="image/jpeg")

@app.post("/api/config")
async def update_config(req: ConfigUpdateRequest):
    updates = req.model_dump(exclude_unset=True)
    config.update(**updates)
    return {"status": "config_updated", "config": updates}

@app.post("/api/simulate")
async def simulate_scenario(scenario_type: str = "multiple"):
    """
    Test scenario generator to demonstrate DEV_Cheat question detection,
    red bounding boxes, clicking, and instant solving.
    """
    from .question_detector import QuestionBlock

    if scenario_type == "multiple":
        q1 = QuestionBlock(
            q_id="q_1",
            title="Q1: Given an array of integers nums and an integer target...",
            text="Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume that each input would have exactly one solution. Example: nums = [2,7,11,15], target = 9 -> Output: [0,1]",
            bbox=[120, 180, 580, 140],
            q_type="coding"
        )
        q2 = QuestionBlock(
            q_id="q_2",
            title="Q2: What is the worst-case time complexity of QuickSort?",
            text="What is the worst-case time complexity of QuickSort algorithm?\nA) O(n log n)\nB) O(n^2)\nC) O(log n)\nD) O(n)",
            bbox=[120, 360, 580, 150],
            q_type="mcq"
        )
        q2.options = ["A) O(n log n)", "B) O(n^2)", "C) O(log n)", "D) O(n)"]

        q3 = QuestionBlock(
            q_id="q_3",
            title="Q3: Which HTTP status code indicates 'Unauthorized'?",
            text="Which HTTP status code indicates 'Unauthorized' access according to RFC 7235?\nA) 400 Bad Request\nB) 401 Unauthorized\nC) 403 Forbidden\nD) 404 Not Found",
            bbox=[120, 550, 580, 150],
            q_type="mcq"
        )
        q3.options = ["A) 400 Bad Request", "B) 401 Unauthorized", "C) 403 Forbidden", "D) 404 Not Found"]

        simulated = [q1, q2, q3]
    else:
        q1 = QuestionBlock(
            q_id="q_1",
            title="Q1: Reverse Linked List in O(n) time and O(1) space",
            text="Given the head of a singly linked list, reverse the list, and return the reversed list.",
            bbox=[180, 220, 600, 160],
            q_type="coding"
        )
        simulated = [q1]

    screen_monitor.current_questions = simulated
    questions_dict = [q.to_dict() for q in simulated]
    from .overlay import desktop_overlay
    desktop_overlay.update_questions(questions_dict)
    await manager.broadcast({
        "type": "questions_detected",
        "data": {
            "count": len(simulated),
            "questions": questions_dict
        }
    })

    # If single question simulation, auto-solve it
    if len(simulated) == 1 and config.auto_solve_single:
        screen_monitor.solve_question(simulated[0].to_dict())

    return {"status": "simulated", "count": len(simulated)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial state
        await websocket.send_json({
            "type": "init",
            "data": {
                "status": screen_monitor.status,
                "is_paused": screen_monitor.is_paused,
                "questions": [q.to_dict() for q in screen_monitor.current_questions],
                "last_solution": screen_monitor.last_solution,
                "history": solver.get_history()
            }
        })
        while True:
            data = await websocket.receive_text()
            # Heartbeat / ping
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# Mount web directory for static localhost frontend
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="static")
