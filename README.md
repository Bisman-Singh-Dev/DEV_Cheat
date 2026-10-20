# DEV_Cheat ⚡

[![GitHub Repo](https://img.shields.io/badge/GitHub-Bisman--Singh--Dev%2FDEV__Cheat-ff2a5f?style=for-the-badge&logo=github)](https://github.com/Bisman-Singh-Dev/DEV_Cheat)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini AI](https://img.shields.io/badge/AI-Gemini%203.8%20Flash-4285F4?style=for-the-badge&logo=google)](https://aistudio.google.com)

> **Autonomous Real-Time Screen Question Solver & Developer Assistant with On-Screen Red Bounding Box HUD and Localhost Web Dashboard.**

---

## 🌟 What is DEV_Cheat?

**DEV_Cheat** is an ultra-fast developer assistant designed to run directly from your **Command Prompt**. It constantly monitors your screen in real time, intelligently detects technical questions (LeetCode problems, multiple choice questions, interview tests, coding quizzes), and instantly solves them right on your screen.

### 🎯 Key Highlights:
- **Instant Auto-Solve for Single Questions**: When a single question appears on your screen, DEV_Cheat immediately extracts the text, passes it to Gemini 3.8 Flash, and projects the direct solution and optimal code.
- **Red Bounding Boxes for Multiple Questions**: When multiple questions appear on your screen, DEV_Cheat outlines each question with a crisp **red bounding box** with interactive target badges `[Q1]`, `[Q2]`, `[Q3]`...
- **Click to Solve**: Simply click on any red bounding box (directly on your screen HUD or on the Localhost Canvas) to solve that specific question instantly!
- **Dismiss Overlays with `Q`**: Pressing <kbd>Q</kbd> on your keyboard immediately hides all open solution cards and resets the view so you can get right back to your workflow.
- **Localhost Web Dashboard**: Live view at `http://localhost:5055` showing real-time screen captures, red bounding box overlays, question queues, searchable solution history, and live controls.
- **Zero-Lag Native Windows OCR**: Uses `Windows.Media.Ocr` under the hood for zero latency and pinpoint word/line bounding box coordinates without needing bulky Tesseract installations.

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/Bisman-Singh-Dev/DEV_Cheat.git
cd DEV_Cheat
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Key
Create or edit your `.env` file:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash
PORT=5055
SCAN_INTERVAL=2.0
AUTO_SOLVE_SINGLE=true
ENABLE_DESKTOP_OVERLAY=true
```

*(Note: If you don't provide an API key, DEV_Cheat will seamlessly use its built-in offline mathematical & heuristic logic solver).*

### 4. Run DEV_Cheat from Command Prompt
```bash
python main.py
# or
python dev_cheat.py
```

DEV_Cheat will launch the CLI banner, initiate screen monitoring, activate the desktop HUD, and open the interactive dashboard in your browser at `http://localhost:5055`!

---

## ⌨️ Command Prompt & Global Hotkeys

| Hotkey | Action | Description |
|:---:|:---|:---|
| <kbd>Q</kbd> | **Hide Responses** | Instantly dismisses active solution cards and resets overlays |
| <kbd>S</kbd> | **Instant Scan** | Forces an immediate screen capture and OCR scan |
| <kbd>C</kbd> | **Clear Highlights** | Clears all red bounding boxes and cached question states |
| <kbd>Click</kbd> | **Solve Question** | Click any red bounding box on screen or dashboard to solve |
| <kbd>Ctrl + C</kbd> | **Stop** | Gracefully stops the background monitor and server |

---

## 🖥️ Localhost Web Dashboard (`http://localhost:5055`)

The web dashboard provides an interactive mission control:
1. **Interactive Live Viewport**:
   - Shows the live screen capture.
   - SVG-rendered pulsing red bounding boxes around all detected questions.
   - Clickable badges: Click any red box on the canvas to trigger an immediate solve.
2. **Active Solution Hub**:
   - **Direct Answer Hero**: Prominently highlights the correct option (e.g., `Option B: O(log n)`).
   - **Optimal Code Block**: Formatted code with a 1-click copy button.
   - **Complexity Meters**: Time & Space complexity metrics.
   - **Reasoning**: Step-by-step breakdown of why the solution is correct.
3. **Multi-Question Simulation Tools**:
   - Click **"Test Multi-Question"** to simulate multiple questions with red boxes right away.
   - Click **"Test LeetCode"** to test coding problem solving.
4. **Saved History**:
   - Automatically stores all generated solutions in `data/history.json`.
   - Searchable and exportable.

---

## 🛠️ CLI Options

You can customize runtime behavior directly from your terminal:

```bash
# Custom port
python main.py --port 8080

# Faster scan interval (e.g. 1.0s)
python main.py --interval 1.0

# Run without opening the browser automatically
python main.py --no-browser

# Disable the on-screen desktop HUD (web dashboard only)
python main.py --no-overlay

# Disable auto-solving single questions (wait for manual click)
python main.py --no-auto-solve
```

---

## 🏗️ Architecture

```
DEV_Cheat/
├── dev_cheat/
│   ├── config.py             # Environment & configuration manager
│   ├── ocr_engine.py         # Native Windows.Media.Ocr pipeline & coordinate extractor
│   ├── question_detector.py  # Regex, MCQ & LeetCode parser with bounding box clusterer
│   ├── solver.py             # Multi-tier Gemini 3.8 Flash & offline solver engine
│   ├── screen_monitor.py     # Background screen grabber, change detector & hotkey handler
│   ├── overlay.py            # Transparent Tkinter HUD with red bounding boxes & floating cards
│   └── server.py             # FastAPI WebSocket & REST API backend
├── web/
│   ├── index.html            # Cyber-themed localhost web UI
│   ├── style.css             # Glassmorphism, neon styling & responsive grid
│   └── app.js                # WebSocket client, SVG bounding box renderer & interactivity
├── data/
│   └── history.json          # Persistent response and solution logs
├── main.py                   # Main CLI entry point with rich terminal banner
├── dev_cheat.py              # Alias entry point
├── requirements.txt          # Python dependencies
├── .env                      # Active credentials & settings
└── README.md                 # Complete documentation
```

---

## 🔒 Privacy & Safety Notice

- All OCR recognition runs **locally on your machine** using Windows Media OCR.
- Screen captures are kept in memory and never shared or sent to external servers unless an AI prompt request is made to the configured Gemini API key.
- History is saved locally in your project's `data/` folder.

---

## 👨‍💻 Author

Developed with ❤️ by **[Bisman Singh](https://github.com/Bisman-Singh-Dev)**.