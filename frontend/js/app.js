// ============================================================
// app.js — talks to the FastAPI backend at API_BASE.
// Login: the token from /api/auth/login is kept in localStorage and
// sent as "Authorization: Bearer <token>" on every request.
// ============================================================

const API_BASE = "http://localhost:8000";
const TOKEN_KEY = "afc_token";
const NOTICE_KEY = "afc_notice";

let categoryChart = null;
let trendChart = null;
let dowChart = null;
let momChart = null;
let expenseCache = {};

// ---------------- Helpers ----------------

// Escape text before putting it into innerHTML so typed text is never run as HTML.
function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function endSession(notice) {
  localStorage.removeItem(TOKEN_KEY);
  if (notice) sessionStorage.setItem(NOTICE_KEY, notice);
  location.reload();
}

// fetch wrapper: adds the login token, and sends the user back to the
// login screen if the server says the session is no longer valid.
async function api(path, options = {}) {
  const headers = Object.assign({}, options.headers || {});
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, Object.assign({}, options, { headers }));

  if (res.status === 401) {
    endSession("Your session expired. Please log in again.");
    throw new Error("unauthorized");
  }
  return res;
}

function apiJson(path, method, body) {
  return api(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function errorText(data, fallback) {
  return data && typeof data.detail === "string" ? data.detail : fallback;
}

// ---------------- Login / register screen ----------------

let authMode = "login"; // "login" or "register"

const authScreen = document.getElementById("auth-screen");
const appShell = document.getElementById("app-shell");
const authForm = document.getElementById("auth-form");
const authError = document.getElementById("auth-error");

function showAuthError(message) {
  authError.textContent = message;
  authError.classList.remove("is-hidden");
}

function clearAuthError() {
  authError.textContent = "";
  authError.classList.add("is-hidden");
}

function setAuthMode(mode) {
  authMode = mode;
  clearAuthError();
  const registering = mode === "register";
  document.getElementById("auth-title").textContent = registering ? "Create account" : "Log in";
  document.getElementById("auth-sub").textContent = registering
    ? "Pick a username (or use your email) and a password of at least 6 characters."
    : "Welcome back. Enter your details to continue.";
  document.getElementById("auth-submit").textContent = registering ? "Create account" : "Log in";
  document.getElementById("auth-switch-text").textContent = registering ? "Already have an account?" : "New here?";
  document.getElementById("auth-switch-btn").textContent = registering ? "Log in" : "Create an account";
  document.getElementById("auth-password").setAttribute(
    "autocomplete",
    registering ? "new-password" : "current-password"
  );
}

function showAuthScreen(message) {
  appShell.classList.add("is-hidden");
  authScreen.classList.remove("is-hidden");
  if (message) showAuthError(message);
}

function showApp(username) {
  authScreen.classList.add("is-hidden");
  appShell.classList.remove("is-hidden");
  document.getElementById("user-label").textContent = username;
}

document.getElementById("auth-switch-btn").addEventListener("click", () => {
  setAuthMode(authMode === "login" ? "register" : "login");
});

authForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearAuthError();

  const submitBtn = document.getElementById("auth-submit");
  submitBtn.disabled = true;

  const payload = {
    username: document.getElementById("auth-username").value.trim(),
    password: document.getElementById("auth-password").value,
  };

  try {
    const res = await fetch(`${API_BASE}/api/auth/${authMode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      showAuthError(errorText(data, "Please fill in both fields."));
      return;
    }

    localStorage.setItem(TOKEN_KEY, data.token);
    authForm.reset();
    showApp(data.username);
    loadDashboard();
    loadCharts();
  } catch (err) {
    showAuthError("Cannot reach the server. Is the backend running?");
  } finally {
    submitBtn.disabled = false;
  }
});

document.getElementById("logout-btn").addEventListener("click", async () => {
  try {
    await api("/api/auth/logout", { method: "POST" });
  } catch (err) {
    // even if the server can't be reached, still log out locally
  }
  endSession();
});

// ---------------- Tab navigation ----------------

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));

    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");

    if (btn.dataset.tab === "dashboard") {
      loadDashboard();
      loadCharts();
    }
    if (btn.dataset.tab === "expense") loadExpenses();
  });
});

// ---------------- Dashboard ----------------

async function loadDashboard() {
  const res = await api("/api/dashboard");
  const data = await res.json();

  const budgetContainer = document.getElementById("budget-cards");
  if (!data.budget_status || data.budget_status.length === 0) {
    budgetContainer.innerHTML = `<p class="empty-state">No budgets set yet. Head to Budgets to add category limits.</p>`;
  } else {
    budgetContainer.innerHTML = data.budget_status.map((b) => `
      <div class="status-card ${esc(b.status)}">
        <div class="cat-name">${esc(b.category)}</div>
        <div class="cat-amount">Rs.${b.spent.toFixed(0)}</div>
        <div class="cat-limit">of Rs.${b.limit.toFixed(0)} limit &middot; ${b.percent_used}%</div>
        <div class="bar-track"><div class="bar-fill" style="width:${Math.min(b.percent_used, 100)}%"></div></div>
      </div>
    `).join("");
  }

  const goalContainer = document.getElementById("goal-cards");
  if (!data.goals || data.goals.length === 0) {
    goalContainer.innerHTML = `<p class="empty-state">No goals yet. Add one in the Goals tab.</p>`;
  } else {
    goalContainer.innerHTML = data.goals.map((g) => `
      <div class="status-card">
        <div class="cat-name">${esc(g.title)} (ID: ${g.id})</div>
        <div class="cat-amount">Rs.${g.saved_amount.toFixed(0)}</div>
        <div class="cat-limit">of Rs.${g.target_amount.toFixed(0)} goal &middot; ${g.percent_complete}%</div>
        <div class="bar-track"><div class="bar-fill" style="width:${Math.min(g.percent_complete, 100)}%"></div></div>
        <div class="cat-tip">${esc(g.pacing_message)}</div>
      </div>
    `).join("");
  }
}

// ---------------- Charts & Insights ----------------

async function loadCharts() {
  const [catRes, trendRes, dowRes, momRes, statsRes] = await Promise.all([
    api("/api/charts/category-breakdown"),
    api("/api/charts/trend"),
    api("/api/charts/day-of-week"),
    api("/api/charts/month-over-month"),
    api("/api/charts/key-stats"),
  ]);
  const catData = await catRes.json();
  const trendData = await trendRes.json();
  const dowData = await dowRes.json();
  const momData = await momRes.json();
  const statsData = await statsRes.json();

  const strip = document.getElementById("insight-strip");
  let insights = [];

  if (momData.percent_change !== null) {
    const direction = momData.percent_change >= 0 ? "up" : "down";
    insights.push(`Spending is ${direction} ${Math.abs(momData.percent_change)}% vs last month`);
  }
  if (statsData.average_daily_spend > 0) {
    insights.push(`Avg Rs.${statsData.average_daily_spend.toFixed(0)}/day this month`);
  }
  if (statsData.biggest_expense) {
    insights.push(`Biggest expense: ${statsData.biggest_expense.description} (Rs.${statsData.biggest_expense.amount.toFixed(0)})`);
  }
  strip.innerHTML = insights.map((i) => `<div class="insight-pill">${esc(i)}</div>`).join("");

  const catCtx = document.getElementById("category-chart").getContext("2d");
  if (categoryChart) categoryChart.destroy();
  categoryChart = new Chart(catCtx, {
    type: "doughnut",
    data: {
      labels: catData.map((c) => c.category),
      datasets: [{
        data: catData.map((c) => c.total),
        backgroundColor: ["#3F6C51", "#B5763B", "#A6432B", "#7C8A80", "#16211C", "#DCD7C9", "#8FA98E", "#C98F5E", "#5E7A6C"],
      }],
    },
    options: { plugins: { legend: { position: "bottom" } } },
  });

  const trendCtx = document.getElementById("trend-chart").getContext("2d");
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(trendCtx, {
    type: "line",
    data: {
      labels: trendData.map((d) => d.date),
      datasets: [{
        label: "Daily Spend",
        data: trendData.map((d) => d.total),
        borderColor: "#3F6C51",
        backgroundColor: "rgba(63,108,81,0.1)",
        tension: 0.3,
        fill: true,
      }],
    },
    options: { plugins: { legend: { display: false } } },
  });

  const dowCtx = document.getElementById("dow-chart").getContext("2d");
  if (dowChart) dowChart.destroy();
  dowChart = new Chart(dowCtx, {
    type: "bar",
    data: {
      labels: dowData.map((d) => d.day.slice(0, 3)),
      datasets: [{
        label: "Total Spend",
        data: dowData.map((d) => d.total),
        backgroundColor: "#B5763B",
      }],
    },
    options: { plugins: { legend: { display: false } } },
  });

  const momCtx = document.getElementById("mom-chart").getContext("2d");
  if (momChart) momChart.destroy();
  momChart = new Chart(momCtx, {
    type: "bar",
    data: {
      labels: [momData.previous_period, momData.current_period],
      datasets: [{
        label: "Total Spend",
        data: [momData.previous_total, momData.current_total],
        backgroundColor: ["#7C8A80", "#3F6C51"],
      }],
    },
    options: { plugins: { legend: { display: false } } },
  });
}

// ---------------- Monthly Report ----------------

async function loadReport() {
  const box = document.getElementById("report-box");
  box.classList.remove("hidden");
  box.innerHTML = "Generating report...";

  try {
    const res = await api("/api/report");
    const data = await res.json();

    let html = `<strong>Report for ${esc(data.period)}</strong><br>`;
    html += `Total spent: Rs.${data.total_spent.toFixed(0)}<br><br>`;

    if (data.category_breakdown.length > 0) {
      html += "<strong>By category:</strong><br>";
      data.category_breakdown.forEach((c) => {
        html += `${esc(c.category)}: Rs.${c.total.toFixed(0)} (${c.count} transactions)<br>`;
      });
      html += "<br>";
    }

    html += `<strong>Summary:</strong><br>${esc(data.narrative).replace(/\n/g, "<br>")}`;
    box.innerHTML = html;
  } catch (err) {
    if (err.message !== "unauthorized") {
      box.innerHTML = "Could not load report. Check the server is running.";
    }
  }
}

document.getElementById("report-btn").addEventListener("click", loadReport);

// ---------------- Expenses ----------------

document.getElementById("expense-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const payload = {
    amount: parseFloat(form.amount.value),
    description: form.description.value,
    date: form.date.value,
    category: form.category.value || null,
  };

  const res = await apiJson("/api/expenses", "POST", payload);
  const data = await res.json();

  const box = document.getElementById("expense-result");
  box.classList.remove("hidden");

  if (!res.ok) {
    box.innerHTML = esc(errorText(data, "Could not add the expense."));
    return;
  }

  box.innerHTML = `
    <strong>Categorized as: ${esc(data.expense.category)}</strong><br>
    ${data.budget_recommendation ? esc(data.budget_recommendation) : "No budget set for this category yet."}
  `;

  form.reset();
  loadExpenses();
});

async function loadExpenses() {
  const res = await api("/api/expenses");
  const expenses = await res.json();
  const tbody = document.querySelector("#expense-table tbody");

  expenseCache = {};
  expenses.forEach((exp) => { expenseCache[exp.id] = exp; });

  tbody.innerHTML = expenses.map((exp) => `
    <tr>
      <td>${esc(exp.date)}</td>
      <td>${esc(exp.description)}</td>
      <td><span class="cat-pill">${esc(exp.category)}</span></td>
      <td class="num">Rs.${exp.amount.toFixed(2)}</td>
      <td class="actions-cell">
        <button class="icon-btn" data-action="edit" data-id="${exp.id}">Edit</button>
        <button class="icon-btn danger" data-action="delete" data-id="${exp.id}">Delete</button>
      </td>
    </tr>
  `).join("");
}

// One click handler for every Edit/Delete button in the table.
document.querySelector("#expense-table tbody").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-action]");
  if (!btn) return;
  const id = Number(btn.dataset.id);
  if (btn.dataset.action === "edit") editExpense(id);
  if (btn.dataset.action === "delete") deleteExpense(id);
});

async function editExpense(id) {
  const current = expenseCache[id];
  if (!current) return;

  const newAmount = prompt("Amount (Rs.):", current.amount);
  if (newAmount === null) return;

  const newDescription = prompt("Description:", current.description);
  if (newDescription === null) return;

  const newDate = prompt("Date (YYYY-MM-DD):", current.date);
  if (newDate === null) return;

  const payload = {};
  if (parseFloat(newAmount) !== current.amount) payload.amount = parseFloat(newAmount);
  if (newDescription !== current.description) payload.description = newDescription;
  if (newDate !== current.date) payload.date = newDate;

  if (Object.keys(payload).length === 0) return;

  const res = await apiJson(`/api/expenses/${id}`, "PUT", payload);
  if (!res.ok) {
    alert("Could not update expense.");
    return;
  }

  loadExpenses();
  loadDashboard();
  loadCharts();
}

async function deleteExpense(id) {
  if (!confirm("Delete this expense?")) return;

  const res = await api(`/api/expenses/${id}`, { method: "DELETE" });
  if (!res.ok) {
    alert("Could not delete expense.");
    return;
  }

  loadExpenses();
  loadDashboard();
  loadCharts();
}

// ---------------- CSV Import ----------------

document.getElementById("csv-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;

  const formData = new FormData();
  formData.append("file", form.file.files[0]);

  const box = document.getElementById("csv-result");
  box.classList.remove("hidden");
  box.innerHTML = "Importing...";

  try {
    const res = await api("/api/expenses/import", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) {
      box.innerHTML = `Error: ${esc(errorText(data, "Import failed."))}`;
      return;
    }

    let html = `Imported ${data.imported} transactions (${data.skipped} skipped).`;
    if (data.budget_recommendations && data.budget_recommendations.length > 0) {
      html += "<br><br><strong>Budget alerts:</strong><br>";
      data.budget_recommendations.forEach((r) => {
        html += `${esc(r.category)}: ${esc(r.tip)}<br>`;
      });
    }
    box.innerHTML = html;
    form.reset();
    loadExpenses();
  } catch (err) {
    if (err.message !== "unauthorized") {
      box.innerHTML = "Import failed. Check the server is running.";
    }
  }
});

// ---------------- Budgets ----------------

document.getElementById("budget-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const payload = {
    category: form.category.value,
    monthly_limit: parseFloat(form.monthly_limit.value),
  };

  await apiJson("/api/budgets", "POST", payload);

  const box = document.getElementById("budget-result");
  box.classList.remove("hidden");
  box.innerHTML = `Budget saved for <strong>${esc(payload.category)}</strong>: Rs.${payload.monthly_limit}/month.`;
  form.reset();
});

// ---------------- Goals ----------------

document.getElementById("goal-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const payload = {
    title: form.title.value,
    target_amount: parseFloat(form.target_amount.value),
    deadline: form.deadline.value || null,
  };

  const res = await apiJson("/api/goals", "POST", payload);
  const data = await res.json();

  const box = document.getElementById("goal-result");
  box.classList.remove("hidden");
  box.innerHTML = `Goal created: <strong>${esc(payload.title)}</strong> (ID: ${data.id}). Use this ID to add savings below.`;
  form.reset();
});

document.getElementById("goal-update-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const goalId = form.goal_id.value;
  const payload = { add_amount: parseFloat(form.add_amount.value) };

  const res = await apiJson(`/api/goals/${encodeURIComponent(goalId)}/add`, "POST", payload);

  const box = document.getElementById("goal-result");
  box.classList.remove("hidden");
  if (!res.ok) {
    box.innerHTML = `No goal with ID ${esc(goalId)} found in your account.`;
    return;
  }
  box.innerHTML = `Added Rs.${payload.add_amount} to goal ID ${esc(goalId)}.`;
  form.reset();
});

// ---------------- Tutor Chat ----------------

document.getElementById("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const message = form.message.value;
  const chatWindow = document.getElementById("chat-window");

  chatWindow.innerHTML += `
    <div class="chat-msg user"><span class="chat-role">You</span>${esc(message)}</div>
  `;
  chatWindow.scrollTop = chatWindow.scrollHeight;
  form.reset();

  const res = await apiJson("/api/chat", "POST", { message });
  const data = await res.json();

  chatWindow.innerHTML += `
    <div class="chat-msg assistant"><span class="chat-role">Tutor</span>${esc(data.reply)}</div>
  `;
  chatWindow.scrollTop = chatWindow.scrollHeight;
});

// ---------------- Start-up: decide login screen vs app ----------------

async function init() {
  setAuthMode("login");
  const notice = sessionStorage.getItem(NOTICE_KEY);
  sessionStorage.removeItem(NOTICE_KEY);

  const token = getToken();
  if (!token) {
    showAuthScreen(notice);
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      showAuthScreen("Your session expired. Please log in again.");
      return;
    }
    const data = await res.json();
    showApp(data.username);
    loadDashboard();
    loadCharts();
  } catch (err) {
    // Server not reachable: keep the saved login, just explain the problem.
    showAuthScreen("Cannot reach the server. Start the backend, then refresh this page.");
  }
}

init();
