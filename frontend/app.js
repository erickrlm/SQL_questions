// ── State ─────────────────────────────────────────────
let currentQuestions = [];
let currentIndex = 0;
let questionStartTime = null;
let answered = false;
let selectedConfidence = null;
let currentCodeQuestion = null;

// ── API ───────────────────────────────────────────────
async function api(url, opts = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ── Navigation ────────────────────────────────────────
document.querySelectorAll("nav button").forEach(btn => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});

function switchView(name) {
  document.querySelectorAll("nav button").forEach(b => b.classList.remove("active"));
  document.querySelector(`nav button[data-view="${name}"]`).classList.add("active");
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.getElementById(`view-${name}`).classList.add("active");
  document.querySelector("main").classList.toggle("wide", name === "code");
  if (name === "stats") loadStats();
  if (name === "questions") loadQuestionList();
  if (name === "code") loadRandomCodeQuestion();
}

function setDifficultyBadge(el, difficulty) {
  el.textContent = difficulty;
  el.className = `badge difficulty-badge ${difficulty}`;
}

// ── Theme ─────────────────────────────────────────────
const themeToggle = document.getElementById("theme-toggle");
themeToggle.addEventListener("click", () => {
  const html = document.documentElement;
  const next = html.dataset.theme === "dark" ? "light" : "dark";
  html.dataset.theme = next;
  localStorage.setItem("theme", next);
  themeToggle.textContent = next === "dark" ? "◐" : "◑";
});

const savedTheme = localStorage.getItem("theme") || "dark";
document.documentElement.dataset.theme = savedTheme;
themeToggle.textContent = savedTheme === "dark" ? "◐" : "◑";

// ── Filters ───────────────────────────────────────────
async function loadTopics() {
  const data = await api("/api/topics");
  const topicSelects = ["filter-topic", "qlist-topic", "code-filter-topic"];
  const categorySelects = ["qlist-category"];

  topicSelects.forEach(id => {
    const sel = document.getElementById(id);
    data.topics.forEach(t => { const o = document.createElement("option"); o.value = t; o.textContent = t; sel.appendChild(o); });
  });
  categorySelects.forEach(id => {
    const sel = document.getElementById(id);
    data.categories.forEach(c => { const o = document.createElement("option"); o.value = c; o.textContent = c; sel.appendChild(o); });
  });
}

// ── Practice ──────────────────────────────────────────
document.getElementById("filter-difficulty").addEventListener("change", loadRandomQuestion);
document.getElementById("filter-topic").addEventListener("change", loadRandomQuestion);
document.getElementById("btn-random").addEventListener("click", loadRandomQuestion);
document.getElementById("btn-next").addEventListener("click", loadRandomQuestion);

async function loadRandomQuestion() {
  const difficulty = document.getElementById("filter-difficulty").value;
  const topic = document.getElementById("filter-topic").value;

  const params = new URLSearchParams();
  params.set("type", "Multiple choice");
  if (difficulty) params.set("difficulty", difficulty);
  if (topic) params.set("topic", topic);

  const qs = await api(`/api/questions?${params}`);
  currentQuestions = qs;

  if (qs.length === 0) {
    document.getElementById("question-container").classList.add("hidden");
    document.getElementById("practice-empty").classList.remove("hidden");
    return;
  }

  document.getElementById("question-container").classList.remove("hidden");
  document.getElementById("practice-empty").classList.add("hidden");
  currentIndex = Math.floor(Math.random() * qs.length);
  renderQuestion(qs[currentIndex]);
}

function renderQuestion(q) {
  answered = false;
  selectedConfidence = null;
  questionStartTime = Date.now();

  setDifficultyBadge(document.getElementById("q-difficulty"), q.difficulty);
  document.getElementById("q-topic").textContent = q.topic;
  document.getElementById("q-category").textContent = q.category;
  document.getElementById("q-prompt").textContent = q.prompt;

  const choicesDiv = document.getElementById("q-choices");
  choicesDiv.innerHTML = "";

  const choices = JSON.parse(q.choices);
  const keys = ["A", "B", "C", "D", "E", "F"];

  choices.forEach((choice, i) => {
    const btn = document.createElement("button");
    btn.className = "choice-btn";
    btn.innerHTML = `<span class="choice-key">${keys[i]}</span>${choice}`;
    btn.addEventListener("click", () => submitAnswer(q, choice, i));
    choicesDiv.appendChild(btn);
  });

  document.getElementById("q-feedback").classList.add("hidden");
  document.getElementById("q-confidence").classList.add("hidden");
  document.getElementById("btn-next").classList.add("hidden");

  document.querySelectorAll("#q-confidence button").forEach(b => b.classList.remove("selected"));
}

async function submitAnswer(q, userAnswer, choiceIndex) {
  if (answered) return;
  answered = true;

  const responseTime = Date.now() - questionStartTime;
  const correct = userAnswer === q.correct_answer;

  await api("/api/progress", {
    method: "POST",
    body: JSON.stringify({
      question_id: q.id,
      correct,
      user_answer: userAnswer,
      response_time_ms: responseTime,
      confidence: null,
    }),
  });

  // Show result
  const choices = JSON.parse(q.choices);
  const correctIdx = choices.indexOf(q.correct_answer);
  const buttons = document.querySelectorAll(".choice-btn");

  buttons.forEach((btn, i) => {
    btn.disabled = true;
    if (i === correctIdx) btn.classList.add("correct");
    if (i === choiceIndex && !correct) btn.classList.add("incorrect");
  });

  const feedback = document.getElementById("q-feedback");
  feedback.classList.remove("hidden", "correct", "incorrect");
  feedback.classList.add(correct ? "correct" : "incorrect");
  feedback.innerHTML = `
    <div class="result-label">${correct ? "Correct" : "Incorrect"}</div>
    <p>${q.explanation}</p>
  `;

  document.getElementById("q-confidence").classList.remove("hidden");
  document.getElementById("btn-next").classList.remove("hidden");
  document.getElementById("btn-next").focus();
}

// ── Confidence ────────────────────────────────────────
document.querySelectorAll("#q-confidence button").forEach(btn => {
  btn.addEventListener("click", async () => {
    document.querySelectorAll("#q-confidence button").forEach(b => b.classList.remove("selected"));
    btn.classList.add("selected");
    selectedConfidence = btn.dataset.confidence;

    const q = currentQuestions[currentIndex];
    await api("/api/progress", {
      method: "POST",
      body: JSON.stringify({
        question_id: q.id,
        correct: null,
        user_answer: "",
        confidence: selectedConfidence,
      }),
    });
  });
});

// ── Keyboard ──────────────────────────────────────────
document.addEventListener("keydown", (e) => {
  // Ctrl+Enter to run query in code editor
  if (e.ctrlKey && e.key === "Enter" && e.target.id === "code-sql-editor") {
    e.preventDefault();
    if (typeof runCodeQuery === "function") runCodeQuery();
    return;
  }

  if (e.target.tagName === "SELECT" || e.target.tagName === "TEXTAREA") return;

  // View switching
  if (e.key === "1" && !e.ctrlKey && !e.metaKey) switchView("practice");
  if (e.key === "2" && !e.ctrlKey && !e.metaKey) switchView("stats");
  if (e.key === "3" && !e.ctrlKey && !e.metaKey) switchView("questions");
  if (e.key === "4" && !e.ctrlKey && !e.metaKey) switchView("code");

  // Question answering (A-D keys) — only when Practice view is active
  const isPracticeActive = document.getElementById("view-practice").classList.contains("active");
  if (!answered && currentQuestions.length > 0 && isPracticeActive) {
    const keys = ["a", "b", "c", "d", "e", "f"];
    const idx = keys.indexOf(e.key.toLowerCase());
    if (idx >= 0) {
      const buttons = document.querySelectorAll(".choice-btn");
      if (buttons[idx]) buttons[idx].click();
    }
  }

  // Next question
  if (e.key === "Enter" && answered) {
    loadRandomQuestion();
  }

  // Random question shortcut
  if (e.key === "r" && e.ctrlKey && !e.metaKey) {
    e.preventDefault();
    loadRandomQuestion();
  }
});

// ── Stats ─────────────────────────────────────────────
async function loadStats() {
  const stats = await api("/api/progress/stats");
  const weakTopics = await api("/api/progress/weak-topics?threshold=60");

  document.getElementById("stat-accuracy").textContent = stats.accuracy + "%";
  document.getElementById("stat-total").textContent = stats.total_answered;
  document.getElementById("stat-correct").textContent = stats.total_correct;

  renderWeakTopics(weakTopics, stats.total_answered);
  renderStatBars("stats-by-topic", stats.by_topic, "topic");
  renderStatBars("stats-by-difficulty", stats.by_difficulty, "difficulty");
  renderRecent(stats.recent);
}

function renderWeakTopics(items, totalAnswered) {
  const container = document.getElementById("stats-weak-topics");
  if (items.length === 0) {
    const msg = totalAnswered === 0 ? "No data yet" : "No weak topics — nice work!";
    container.innerHTML = `<p style="color:var(--text-secondary)">${msg}</p>`;
    return;
  }
  container.innerHTML = items.map(item => `
    <div class="stat-row">
      <span class="label">${item.topic}</span>
      <div class="bar-bg"><div class="bar-fill low" style="width:${item.accuracy}%"></div></div>
      <span class="pct">${item.accuracy}%</span>
    </div>`).join("");
}

function renderStatBars(containerId, items, labelKey) {
  const container = document.getElementById(containerId);
  if (items.length === 0) {
    container.innerHTML = '<p style="color:var(--text-secondary)">No data yet</p>';
    return;
  }
  container.innerHTML = items.map(item => {
    const pct = item.accuracy;
    const cls = pct >= 80 ? "high" : pct >= 50 ? "mid" : "low";
    return `
      <div class="stat-row">
        <span class="label">${item[labelKey]}</span>
        <div class="bar-bg"><div class="bar-fill ${cls}" style="width:${pct}%"></div></div>
        <span class="pct">${pct}%</span>
      </div>`;
  }).join("");
}

function renderRecent(items) {
  const container = document.getElementById("stats-recent");
  if (items.length === 0) {
    container.innerHTML = '<p style="color:var(--text-secondary)">No activity yet</p>';
    return;
  }
  container.innerHTML = items.map(r => `
    <div class="recent-row">
      <span class="icon">${r.correct ? "✓" : "✗"}</span>
      <span class="topic">${r.topic} (${r.difficulty})</span>
      <span class="date">${r.completed_at.slice(0, 16).replace("T", " ")}</span>
    </div>
  `).join("");
}

// ── Question List ─────────────────────────────────────
document.getElementById("qlist-difficulty").addEventListener("change", loadQuestionList);
document.getElementById("qlist-topic").addEventListener("change", loadQuestionList);
document.getElementById("qlist-category").addEventListener("change", loadQuestionList);
document.getElementById("qlist-type").addEventListener("change", loadQuestionList);

async function loadQuestionList() {
  const params = new URLSearchParams();
  const difficulty = document.getElementById("qlist-difficulty").value;
  const topic = document.getElementById("qlist-topic").value;
  const category = document.getElementById("qlist-category").value;
  const type = document.getElementById("qlist-type").value;
  if (difficulty) params.set("difficulty", difficulty);
  if (topic) params.set("topic", topic);
  if (category) params.set("category", category);
  if (type) params.set("type", type);

  const qs = await api(`/api/questions?${params}`);
  const container = document.getElementById("questions-list");

  if (qs.length === 0) {
    container.innerHTML = '<div class="card empty-state"><p>No questions match.</p></div>';
    return;
  }

  container.innerHTML = qs.map(q => `
    <div class="question-row" data-id="${q.id}" data-type="${q.type}">
      <span class="q-prompt">${q.prompt}</span>
      <span class="q-meta">
        <span class="badge">${q.type}</span>
        <span class="badge difficulty-badge ${q.difficulty}">${q.difficulty}</span>
        <span class="badge">${q.topic}</span>
      </span>
    </div>
  `).join("");

  container.querySelectorAll(".question-row").forEach(row => {
    row.addEventListener("click", async () => {
      const q = await api(`/api/questions/${row.dataset.id}`);
      const isCoding = q.type === "Query" || q.type === "coding";
      if (isCoding) {
        const fullQ = await api(`/api/code/questions/${q.id}`);
        currentCodeQuestion = fullQ;
        switchView("code");
        renderCodeQuestion(fullQ);
      } else {
        currentQuestions = [q];
        currentIndex = 0;
        switchView("practice");
        renderQuestion(q);
      }
    });
  });
}

// ── Code View ──────────────────────────────────────────
document.getElementById("code-filter-difficulty").addEventListener("change", loadRandomCodeQuestion);
document.getElementById("code-filter-topic").addEventListener("change", loadRandomCodeQuestion);
document.getElementById("code-btn-random").addEventListener("click", loadRandomCodeQuestion);
document.getElementById("code-btn-next").addEventListener("click", loadRandomCodeQuestion);
document.getElementById("code-btn-run").addEventListener("click", runCodeQuery);
document.getElementById("code-btn-submit").addEventListener("click", submitCodeAnswer);
document.getElementById("code-btn-clear").addEventListener("click", clearCodeEditor);

// Left-panel tabs (Description / Schema)
document.querySelectorAll(".code-tab").forEach(tab => {
  tab.addEventListener("click", () => switchCodeTab(tab.dataset.tab));
});

function switchCodeTab(name) {
  document.querySelectorAll(".code-tab").forEach(t => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".code-tab-panel").forEach(p => p.classList.toggle("active", p.id === `code-tab-${name}`));
}

// Code confidence
document.querySelectorAll("#code-confidence button").forEach(btn => {
  btn.addEventListener("click", async () => {
    document.querySelectorAll("#code-confidence button").forEach(b => b.classList.remove("selected"));
    btn.classList.add("selected");
    await api("/api/progress", {
      method: "POST",
      body: JSON.stringify({
        question_id: currentCodeQuestion.id,
        correct: null,
        user_answer: "",
        confidence: btn.dataset.confidence,
      }),
    });
  });
});

async function loadRandomCodeQuestion() {
  const difficulty = document.getElementById("code-filter-difficulty").value;
  const topic = document.getElementById("code-filter-topic").value;

  const params = new URLSearchParams();
  params.set("type", "Query");
  if (difficulty) params.set("difficulty", difficulty);
  if (topic) params.set("topic", topic);

  const qs = await api(`/api/questions?${params}`);

  if (qs.length === 0) {
    document.getElementById("code-question-container").classList.add("hidden");
    document.getElementById("code-empty").classList.remove("hidden");
    return;
  }

  document.getElementById("code-question-container").classList.remove("hidden");
  document.getElementById("code-empty").classList.add("hidden");

  const q = qs[Math.floor(Math.random() * qs.length)];
  const fullQ = await api(`/api/code/questions/${q.id}`);
  currentCodeQuestion = fullQ;
  renderCodeQuestion(fullQ);
}

function renderCodeQuestion(q) {
  setDifficultyBadge(document.getElementById("code-q-difficulty"), q.difficulty);
  document.getElementById("code-q-topic").textContent = q.topic;
  document.getElementById("code-q-category").textContent = q.category;
  document.getElementById("code-q-prompt").textContent = q.prompt;
  document.getElementById("code-schema-content").textContent = q.dataset_schema || "No schema available";
  switchCodeTab("description");

  // Clear editor
  document.getElementById("code-sql-editor").value = "";

  // Reset console: results, error, feedback, confidence, next hidden; empty-state shown
  document.getElementById("code-results").classList.add("hidden");
  document.getElementById("code-error").classList.add("hidden");
  document.getElementById("code-feedback").classList.add("hidden");
  document.getElementById("code-confidence").classList.add("hidden");
  document.getElementById("code-btn-next").classList.add("hidden");
  document.getElementById("code-console-empty").classList.remove("hidden");
  document.getElementById("code-btn-submit").disabled = false;
  document.getElementById("code-btn-run").disabled = false;

  document.getElementById("code-sql-editor").focus();
}

async function runCodeQuery() {
  if (!currentCodeQuestion) return;

  const query = document.getElementById("code-sql-editor").value.trim();
  if (!query) return;

  document.getElementById("code-error").classList.add("hidden");
  document.getElementById("code-results").classList.add("hidden");
  document.getElementById("code-feedback").classList.add("hidden");
  document.getElementById("code-console-empty").classList.add("hidden");

  const result = await api("/api/code/execute", {
    method: "POST",
    body: JSON.stringify({
      question_id: currentCodeQuestion.id,
      query: query,
    }),
  });

  if (result.error) {
    document.getElementById("code-error").textContent = result.error;
    document.getElementById("code-error").classList.remove("hidden");
    return;
  }

  renderResultsTable(result.columns, result.rows, result.row_count, result.truncated);
}

function renderResultsTable(columns, rows, rowCount, truncated) {
  const resultsDiv = document.getElementById("code-results");
  resultsDiv.classList.remove("hidden");

  document.getElementById("code-row-count").textContent =
    `${rowCount} row${rowCount !== 1 ? "s" : ""}${truncated ? " (truncated)" : ""}`;

  const thead = document.getElementById("code-results-thead");
  const tbody = document.getElementById("code-results-tbody");

  thead.innerHTML = `<tr>${columns.map(c => `<th>${escapeHtml(c)}</th>`).join("")}</tr>`;

  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="${columns.length}" style="text-align:center;color:var(--text-secondary)">No rows returned</td></tr>`;
  } else {
    tbody.innerHTML = rows.map(row =>
      `<tr>${row.map(cell =>
        `<td>${cell === null ? '<span class="null-value">NULL</span>' : escapeHtml(String(cell))}</td>`
      ).join("")}</tr>`
    ).join("");
  }
}

async function submitCodeAnswer() {
  if (!currentCodeQuestion) return;

  const query = document.getElementById("code-sql-editor").value.trim();
  if (!query) return;

  document.getElementById("code-btn-submit").disabled = true;
  document.getElementById("code-error").classList.add("hidden");
  document.getElementById("code-console-empty").classList.add("hidden");

  const result = await api("/api/code/submit", {
    method: "POST",
    body: JSON.stringify({
      question_id: currentCodeQuestion.id,
      query: query,
    }),
  });

  const feedback = document.getElementById("code-feedback");
  feedback.classList.remove("hidden", "correct", "incorrect");

  if (result.match) {
    feedback.classList.add("correct");
    feedback.innerHTML = `
      <div class="result-label">Correct</div>
      <p>Your query produced the expected result.</p>
      <p>${currentCodeQuestion.explanation}</p>
    `;
  } else {
    feedback.classList.add("incorrect");
    let detail = result.details || "Your result did not match the expected output.";
    if (result.error) detail = result.error;
    feedback.innerHTML = `
      <div class="result-label">Incorrect</div>
      <p>${detail}</p>
    `;
  }

  document.getElementById("code-confidence").classList.remove("hidden");
  document.getElementById("code-btn-next").classList.remove("hidden");
  document.getElementById("code-btn-next").focus();
}

function clearCodeEditor() {
  document.getElementById("code-sql-editor").value = "";
  document.getElementById("code-results").classList.add("hidden");
  document.getElementById("code-error").classList.add("hidden");
  document.getElementById("code-feedback").classList.add("hidden");
  document.getElementById("code-confidence").classList.add("hidden");
  document.getElementById("code-btn-next").classList.add("hidden");
  document.getElementById("code-console-empty").classList.remove("hidden");
  document.getElementById("code-btn-submit").disabled = false;
  document.getElementById("code-btn-run").disabled = false;
  document.getElementById("code-sql-editor").focus();
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ── Init ──────────────────────────────────────────────
loadTopics();
loadRandomQuestion();
