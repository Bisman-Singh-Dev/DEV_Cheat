// DEV_Cheat Frontend Application
(function() {
  // DOM Elements
  const statusPill = document.getElementById("statusPill");
  const statusLabel = document.getElementById("statusLabel");
  const questionCount = document.getElementById("questionCount");
  const tabQuestionCount = document.getElementById("tabQuestionCount");
  const historyCount = document.getElementById("historyCount");
  const cliMsg = document.getElementById("cliMsg");

  const btnManualScan = document.getElementById("btnManualScan");
  const btnHideResponses = document.getElementById("btnHideResponses");
  const btnSimulateMultiple = document.getElementById("btnSimulateMultiple");
  const btnSimulateCoding = document.getElementById("btnSimulateCoding");
  const btnSettings = document.getElementById("btnSettings");
  const btnDismissSolution = document.getElementById("btnDismissSolution");
  const btnCopyAnswer = document.getElementById("btnCopyAnswer");
  const btnCopyCode = document.getElementById("btnCopyCode");
  const btnClearHistory = document.getElementById("btnClearHistory");

  const liveScreenshot = document.getElementById("liveScreenshot");
  const bboxOverlay = document.getElementById("bboxOverlay");
  const canvasContainer = document.getElementById("canvasContainer");

  const emptySolutionState = document.getElementById("emptySolutionState");
  const solutionData = document.getElementById("solutionData");
  const solType = document.getElementById("solType");
  const solTimestamp = document.getElementById("solTimestamp");
  const solDirectAnswer = document.getElementById("solDirectAnswer");
  const solTimeComp = document.getElementById("solTimeComp");
  const solSpaceComp = document.getElementById("solSpaceComp");
  const solCodeContainer = document.getElementById("solCodeContainer");
  const solCode = document.getElementById("solCode");
  const solExplanation = document.getElementById("solExplanation");
  const solKeyPoints = document.getElementById("solKeyPoints");

  const questionsList = document.getElementById("questionsList");
  const historyList = document.getElementById("historyList");
  const historySearch = document.getElementById("historySearch");

  // Settings Modal
  const settingsModal = document.getElementById("settingsModal");
  const btnCloseSettings = document.getElementById("btnCloseSettings");
  const btnCancelSettings = document.getElementById("btnCancelSettings");
  const btnSaveSettings = document.getElementById("btnSaveSettings");
  const cfgApiKey = document.getElementById("cfgApiKey");
  const cfgModel = document.getElementById("cfgModel");
  const cfgInterval = document.getElementById("cfgInterval");
  const cfgAutoSolveSingle = document.getElementById("cfgAutoSolveSingle");
  const cfgDesktopOverlay = document.getElementById("cfgDesktopOverlay");

  // State
  let currentQuestions = [];
  let currentHistory = [];
  let activeSolution = null;
  let naturalScreenWidth = 1920;
  let naturalScreenHeight = 1080;
  let ws = null;

  // Initialize
  initWebSocket();
  initTabs();
  initKeyboardListeners();
  fetchInitialState();

  // Setup WebSocket
  function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setCliMsg("Connected to DEV_Cheat Engine. Monitoring active.");
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleWsEvent(msg.type, msg.data);
      } catch (e) {
        // Ping response or string
      }
    };

    ws.onclose = () => {
      setCliMsg("Connection lost. Reconnecting in 2s...");
      setTimeout(initWebSocket, 2000);
    };
  }

  function handleWsEvent(type, data) {
    switch (type) {
      case "init":
        updateStatus(data.status);
        if (data.questions) {
          updateQuestions(data.questions);
        }
        if (data.last_solution) {
          showSolution(data.last_solution);
        }
        if (data.history) {
          updateHistory(data.history);
        }
        break;

      case "status_change":
        updateStatus(data.status, data.target);
        break;

      case "questions_detected":
        updateQuestions(data.questions || []);
        refreshScreenshot();
        break;

      case "solved":
        showSolution(data.solution);
        refreshHistory();
        break;

      case "hide_responses":
        hideResponses();
        break;

      case "clear":
        updateQuestions([]);
        hideResponses();
        break;
    }
  }

  async function fetchInitialState() {
    try {
      const res = await fetch("/api/status");
      const data = await res.json();
      updateStatus(data.status);
      if (data.config) {
        cfgModel.value = data.config.gemini_model;
        cfgInterval.value = data.config.scan_interval;
        cfgAutoSolveSingle.checked = data.config.auto_solve_single;
        cfgDesktopOverlay.checked = data.config.enable_desktop_overlay;
      }
    } catch (e) {
      console.error(e);
    }
    refreshHistory();
  }

  function updateStatus(status, target = "") {
    statusPill.className = "status-indicator";
    if (status === "scanning") {
      statusPill.classList.add("scanning");
      statusLabel.textContent = "Scanning Screen...";
      setCliMsg("Scanning active desktop display for technical questions...");
    } else if (status === "solving") {
      statusPill.classList.add("solving");
      statusLabel.textContent = `Solving ${target || "Question"}...`;
      setCliMsg(`Gemini AI solving ${target || "question"} in real time...`);
    } else if (status === "idle") {
      statusLabel.textContent = "Monitoring Screen";
      setCliMsg("Monitoring screen. Press 'S' to force scan, 'Q' to hide solutions.");
    } else if (status === "paused") {
      statusLabel.textContent = "Monitor Paused";
      setCliMsg("Screen monitor paused.");
    }
  }

  function setCliMsg(msg) {
    if (cliMsg) cliMsg.textContent = msg;
  }

  function updateQuestions(questions) {
    currentQuestions = questions;
    const count = questions.length;
    questionCount.textContent = count;
    tabQuestionCount.textContent = count;

    renderBboxOverlay();
    renderQuestionsList();
  }

  function renderBboxOverlay() {
    bboxOverlay.innerHTML = "";
    if (!currentQuestions || currentQuestions.length === 0) return;

    // Get current displayed image dimensions
    const imgRect = liveScreenshot.getBoundingClientRect();
    const dispW = imgRect.width;
    const dispH = imgRect.height;
    if (dispW === 0 || dispH === 0) return;

    // Scale factors
    const naturalW = liveScreenshot.naturalWidth || 1920;
    const naturalH = liveScreenshot.naturalHeight || 1080;
    const scaleX = dispW / naturalW;
    const scaleY = dispH / naturalH;

    // Set SVG viewBox to match the image exactly
    bboxOverlay.setAttribute("viewBox", `0 0 ${dispW} ${dispH}`);

    currentQuestions.forEach((q, idx) => {
      const [bx, by, bw, bh] = q.bbox;
      const x = bx * scaleX;
      const y = by * scaleY;
      const w = bw * scaleX;
      const h = bh * scaleY;

      // Group for each question
      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");

      // Red Box Rect
      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", x);
      rect.setAttribute("y", y);
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("rx", "4");
      rect.setAttribute("class", "bbox-rect");
      rect.onclick = () => solveQuestion(q);

      // Badge Background
      const badgeW = 90;
      const badgeH = 20;
      const badgeY = Math.max(2, y - badgeH - 3);

      const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      bg.setAttribute("x", x);
      bg.setAttribute("y", badgeY);
      bg.setAttribute("width", badgeW);
      bg.setAttribute("height", badgeH);
      bg.setAttribute("rx", "3");
      bg.setAttribute("class", "bbox-badge-bg");
      bg.onclick = () => solveQuestion(q);

      // Badge Text
      const txt = document.createElementNS("http://www.w3.org/2000/svg", "text");
      txt.setAttribute("x", x + 6);
      txt.setAttribute("y", badgeY + 14);
      txt.setAttribute("class", "bbox-badge-text");
      txt.textContent = `🎯 ${q.id.toUpperCase()}: SOLVE`;

      g.appendChild(rect);
      g.appendChild(bg);
      g.appendChild(txt);
      bboxOverlay.appendChild(g);
    });
  }

  function renderQuestionsList() {
    if (!currentQuestions || currentQuestions.length === 0) {
      questionsList.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🔍</div>
          <h3>No Questions Highlighted</h3>
          <p>Scan your screen or test with a simulated scenario.</p>
        </div>
      `;
      return;
    }

    questionsList.innerHTML = currentQuestions.map(q => `
      <div class="question-item-card" data-qid="${q.id}">
        <div class="q-card-header">
          <span class="type-pill">${(q.type || 'QUESTION').toUpperCase()}</span>
          <span class="q-card-title">${escapeHtml(q.title)}</span>
        </div>
        <p class="q-card-text">${escapeHtml(q.text.slice(0, 140))}${q.text.length > 140 ? '...' : ''}</p>
        <div class="q-card-actions">
          <button class="btn-solve-now" data-qid="${q.id}">⚡ Click to Solve</button>
        </div>
      </div>
    `).join("");

    // Bind clicks
    questionsList.querySelectorAll(".btn-solve-now, .question-item-card").forEach(el => {
      el.addEventListener("click", (e) => {
        const qid = el.getAttribute("data-qid");
        const target = currentQuestions.find(q => q.id === qid);
        if (target) solveQuestion(target);
      });
    });
  }

  async function solveQuestion(question) {
    updateStatus("solving", question.title || question.id);
    switchTab("activeSolution");

    try {
      const res = await fetch("/api/solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(question)
      });
      const data = await res.json();
      if (data.solution) {
        showSolution(data.solution);
        refreshHistory();
      }
    } catch (e) {
      console.error(e);
      setCliMsg("Error calling solver: " + e.message);
    }
  }

  function showSolution(sol) {
    activeSolution = sol;
    emptySolutionState.classList.add("hidden");
    solutionData.classList.remove("hidden");

    solType.textContent = (sol.q_type || "SOLUTION").toUpperCase();
    solTimestamp.textContent = sol.timestamp || "Just now";
    solDirectAnswer.textContent = sol.direct_answer || "No direct answer returned";

    // Complexity
    if (sol.time_complexity || sol.space_complexity) {
      solTimeComp.textContent = `Time: ${sol.time_complexity || 'O(n)'}`;
      solSpaceComp.textContent = `Space: ${sol.space_complexity || 'O(1)'}`;
      solTimeComp.style.display = "block";
      solSpaceComp.style.display = "block";
    } else {
      solTimeComp.style.display = "none";
      solSpaceComp.style.display = "none";
    }

    // Code
    if (sol.code && sol.code.trim()) {
      solCodeContainer.style.display = "block";
      solCode.textContent = sol.code.trim();
    } else {
      solCodeContainer.style.display = "none";
    }

    // Explanation & Key Points with clean step formatting
    const rawExp = sol.explanation || "";
    const cleanExp = rawExp
      .replace(/\$/g, "")
      .replace(/\\implies/g, "=>")
      .replace(/\\cdot/g, "*")
      .replace(/\\times/g, "*")
      .replace(/\\approx/g, "~")
      .replace(/\\frac/g, "")
      .replace(/\\propto/g, "proportional to");

    solExplanation.textContent = cleanExp;
    if (sol.key_points && sol.key_points.length > 0) {
      solKeyPoints.innerHTML = sol.key_points.map(pt => `<li>${escapeHtml(pt)}</li>`).join("");
      solKeyPoints.style.display = "block";
    } else {
      solKeyPoints.style.display = "none";
    }

    setCliMsg(`Solved! Press 'Q' anytime to hide the solution overlay.`);
  }

  function hideResponses() {
    activeSolution = null;
    solutionData.classList.add("hidden");
    emptySolutionState.classList.remove("hidden");
    setCliMsg("Responses hidden. Waiting for next question...");
  }

  async function refreshHistory() {
    try {
      const res = await fetch("/api/history");
      const list = await res.json();
      updateHistory(list);
    } catch (e) {
      console.error(e);
    }
  }

  function updateHistory(items) {
    currentHistory = items;
    historyCount.textContent = items.length;
    renderHistory(items);
  }

  function renderHistory(items) {
    if (!items || items.length === 0) {
      historyList.innerHTML = `<div class="empty-state"><p>No saved responses yet.</p></div>`;
      return;
    }

    historyList.innerHTML = items.map(item => `
      <div class="history-card">
        <div class="history-date">${item.timestamp || ''} • <span class="type-pill">${(item.q_type || 'GENERAL').toUpperCase()}</span></div>
        <div class="history-question">${escapeHtml(item.question_text ? item.question_text.slice(0, 90) : 'Question')}</div>
        <div class="history-answer">✓ ${escapeHtml(item.direct_answer || '')}</div>
      </div>
    `).join("");
  }

  function refreshScreenshot() {
    liveScreenshot.src = `/api/screenshot?t=${Date.now()}`;
    liveScreenshot.onload = () => {
      renderBboxOverlay();
    };
  }

  // Keyboard Handlers: 'Q' hides responses
  function initKeyboardListeners() {
    window.addEventListener("keydown", (e) => {
      // If typing in input or textarea, don't hijack
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
        return;
      }

      if (e.key === "q" || e.key === "Q") {
        e.preventDefault();
        fetch("/api/hide", { method: "POST" });
        hideResponses();
      } else if (e.key === "s" || e.key === "S") {
        e.preventDefault();
        fetch("/api/scan", { method: "POST" });
        setCliMsg("Manual scan triggered...");
      } else if (e.key === "c" || e.key === "C") {
        e.preventDefault();
        fetch("/api/clear", { method: "POST" });
      }
    });

    window.addEventListener("resize", () => {
      renderBboxOverlay();
    });
  }

  // Tabs Handler
  function initTabs() {
    document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-tab");
        switchTab(tab);
      });
    });
  }

  function switchTab(tabName) {
    document.querySelectorAll(".tab-btn").forEach(b => {
      b.classList.toggle("active", b.getAttribute("data-tab") === tabName);
    });

    document.getElementById("tabActiveSolution").classList.toggle("active", tabName === "activeSolution");
    document.getElementById("tabDetectedQuestions").classList.toggle("active", tabName === "detectedQuestions");
    document.getElementById("tabHistory").classList.toggle("active", tabName === "historyTab");
  }

  // Event Listeners
  btnManualScan.addEventListener("click", () => {
    fetch("/api/scan", { method: "POST" });
    setCliMsg("Manual scan triggered...");
  });

  btnHideResponses.addEventListener("click", () => {
    fetch("/api/hide", { method: "POST" });
    hideResponses();
  });

  btnDismissSolution.addEventListener("click", () => {
    fetch("/api/hide", { method: "POST" });
    hideResponses();
  });

  btnSimulateMultiple.addEventListener("click", async () => {
    setCliMsg("Simulating multiple questions scenario with red bounding boxes...");
    await fetch("/api/simulate?scenario_type=multiple", { method: "POST" });
    switchTab("detectedQuestions");
  });

  btnSimulateCoding.addEventListener("click", async () => {
    setCliMsg("Simulating LeetCode problem scenario...");
    await fetch("/api/simulate?scenario_type=coding", { method: "POST" });
    switchTab("activeSolution");
  });

  btnCopyAnswer.addEventListener("click", () => {
    if (activeSolution && activeSolution.direct_answer) {
      navigator.clipboard.writeText(activeSolution.direct_answer);
      btnCopyAnswer.textContent = "Copied!";
      setTimeout(() => btnCopyAnswer.textContent = "Copy Answer", 1500);
    }
  });

  btnCopyCode.addEventListener("click", () => {
    if (activeSolution && activeSolution.code) {
      navigator.clipboard.writeText(activeSolution.code);
      btnCopyCode.textContent = "Copied!";
      setTimeout(() => btnCopyCode.textContent = "Copy Code", 1500);
    }
  });

  btnClearHistory.addEventListener("click", async () => {
    if (confirm("Are you sure you want to clear all saved responses?")) {
      await fetch("/api/history", { method: "DELETE" });
      updateHistory([]);
    }
  });

  historySearch.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    const filtered = currentHistory.filter(item => 
      (item.question_text && item.question_text.toLowerCase().includes(q)) ||
      (item.direct_answer && item.direct_answer.toLowerCase().includes(q))
    );
    renderHistory(filtered);
  });

  // Settings Modal Handlers
  btnSettings.addEventListener("click", () => {
    settingsModal.classList.remove("hidden");
  });

  btnCloseSettings.addEventListener("click", () => {
    settingsModal.classList.add("hidden");
  });

  btnCancelSettings.addEventListener("click", () => {
    settingsModal.classList.add("hidden");
  });

  btnSaveSettings.addEventListener("click", async () => {
    const payload = {
      gemini_model: cfgModel.value,
      scan_interval: parseFloat(cfgInterval.value),
      auto_solve_single: cfgAutoSolveSingle.checked,
      enable_desktop_overlay: cfgDesktopOverlay.checked
    };
    if (cfgApiKey.value.trim()) {
      payload.gemini_api_key = cfgApiKey.value.trim();
    }

    await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    settingsModal.classList.add("hidden");
    setCliMsg("Settings updated successfully.");
  });

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
})();
