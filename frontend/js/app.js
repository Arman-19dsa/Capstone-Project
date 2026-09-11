// ============================================================
// app.js — talks to the FastAPI backend at API_BASE.
// ============================================================

const API_BASE = "http://localhost:8000";

let categoryChart = null;
let trendChart = null;
let dowChart = null;
let momChart = null;

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
  const res = await fetch(`${API_BASE}/api/dashboard`);
  const data = await res.json();

  const budgetContainer = document.getElementById("budget-cards");
  if (!data.budget_status || data.budget_status.length === 0) {
    budgetContainer.innerHTML = `<p class="empty-state">No budgets set yet. Head to Budgets to add category limits.</p>`;
  } else {
    budgetContainer.innerHTML = data.budget_status.map((b) => `
      <div class="status-card ${b.status}">
        <div class="cat-name">${b.category}</div>
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
        <div class="cat-name">${g.title} (ID: ${g.id})</div>
        <div class="cat-amount">Rs.${g.saved_amount.toFixed(0)}</div>
        <div class="cat-limit">of Rs.${g.target_amount.toFixed(0)} goal &middot; ${g.percent_complete}%</div>
        <div class="bar-track"><div class="bar-fill" style="width:${Math.min(g.percent_complete, 100)}%"></div></div>
        <div class="cat-tip">${g.pacing_message}</div>
      </div>
    `).join("");
  }
}

// ---------------- Charts & Insights ----------------

async function loadCharts() {
  const catRes = await fetch(`${API_BASE}/api/charts/category-breakdown`);
  const catData = await catRes.json();

  const trendRes = await fetch(`${API_BASE}/api/charts/trend`);
  const trendData = await trendRes.json();

  const dowRes = await fetch(`${API_BASE}/api/charts/day-of-week`);
  const dowData = await dowRes.json();

  const momRes = await fetch(`${API_BASE}/api/charts/month-over-month`);
  const momData = await momRes.json();

  const statsRes = await fetch(`${API_BASE}/api/charts/key-stats`);
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
  strip.innerHTML = insights.map((i) => `<div class="insight-pill">${i}</div>`).join("");

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
    const res = await fetch(`${API_BASE}/api/report`);
    const data = await res.json();

    let html = `<strong>Report for ${data.period}</strong><br>`;
    html += `Total spent: Rs.${data.total_spent.toFixed(0)}<br><br>`;

    if (data.category_breakdown.length > 0) {
      html += "<strong>By category:</strong><br>";
      data.category_breakdown.forEach((c) => {
        html += `${c.category}: Rs.${c.total.toFixed(0)} (${c.count} transactions)<br>`;
      });
      html += "<br>";
    }

    html += `<strong>Summary:</strong><br>${data.narrative}`;
    box.innerHTML = html;
  } catch (err) {
    box.innerHTML = "Could not load report. Check the server is running.";
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

  const res = await fetch(`${API_BASE}/api/expenses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();

  const box = document.getElementById("expense-result");
  box.classList.remove("hidden");
  box.innerHTML = `
    <strong>Categorized as: ${data.expense.category}</strong><br>
    ${data.budget_recommendation ? data.budget_recommendation : "No budget set for this category yet."}
  `;

  form.reset();
  loadExpenses();
});

async function loadExpenses() {
  const res = await fetch(`${API_BASE}/api/expenses`);
  const expenses = await res.json();
  const tbody = document.querySelector("#expense-table tbody");

  tbody.innerHTML = expenses.map((exp) => `
    <tr>
      <td>${exp.date}</td>
      <td>${exp.description}</td>
      <td><span class="cat-pill">${exp.category}</span></td>
      <td class="num">Rs.${exp.amount.toFixed(2)}</td>
      <td class="actions-cell">
        <button class="icon-btn" onclick="editExpense(${exp.id}, ${exp.amount}, '${exp.description.replace(/'/g, "\\'")}', '${exp.date}')">Edit</button>
        <button class="icon-btn danger" onclick="deleteExpense(${exp.id})">Delete</button>
      </td>
    </tr>
  `).join("");
}

async function editExpense(id, currentAmount, currentDescription, currentDate) {
  const newAmount = prompt("Amount (Rs.):", currentAmount);
  if (newAmount === null) return;

  const newDescription = prompt("Description:", currentDescription);
  if (newDescription === null) return;

  const newDate = prompt("Date (YYYY-MM-DD):", currentDate);
  if (newDate === null) return;

  const payload = {};
  if (parseFloat(newAmount) !== currentAmount) payload.amount = parseFloat(newAmount);
  if (newDescription !== currentDescription) payload.description = newDescription;
  if (newDate !== currentDate) payload.date = newDate;

  if (Object.keys(payload).length === 0) return;

  const res = await fetch(`${API_BASE}/api/expenses/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

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

  const res = await fetch(`${API_BASE}/api/expenses/${id}`, { method: "DELETE" });
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
  const fileInput = form.file;

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  const box = document.getElementById("csv-result");
  box.classList.remove("hidden");
  box.innerHTML = "Importing...";

  try {
    const res = await fetch(`${API_BASE}/api/expenses/import`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (!res.ok) {
      box.innerHTML = `Error: ${data.detail}`;
      return;
    }

    let html = `Imported ${data.imported} transactions (${data.skipped} skipped).`;
    if (data.budget_recommendations && data.budget_recommendations.length > 0) {
      html += "<br><br><strong>Budget alerts:</strong><br>";
      data.budget_recommendations.forEach((r) => {
        html += `${r.category}: ${r.tip}<br>`;
      });
    }
    box.innerHTML = html;
    form.reset();
    loadExpenses();
  } catch (err) {
    box.innerHTML = "Import failed. Check the server is running.";
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

  await fetch(`${API_BASE}/api/budgets`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const box = document.getElementById("budget-result");
  box.classList.remove("hidden");
  box.innerHTML = `Budget saved for <strong>${payload.category}</strong>: Rs.${payload.monthly_limit}/month.`;
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

  const res = await fetch(`${API_BASE}/api/goals`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();

  const box = document.getElementById("goal-result");
  box.classList.remove("hidden");
  box.innerHTML = `Goal created: <strong>${payload.title}</strong> (ID: ${data.id}). Use this ID to add savings below.`;
  form.reset();
});

document.getElementById("goal-update-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const goalId = form.goal_id.value;
  const payload = { add_amount: parseFloat(form.add_amount.value) };

  await fetch(`${API_BASE}/api/goals/${goalId}/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const box = document.getElementById("goal-result");
  box.classList.remove("hidden");
  box.innerHTML = `Added Rs.${payload.add_amount} to goal ID ${goalId}.`;
  form.reset();
});

// ---------------- Tutor Chat ----------------

document.getElementById("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const message = form.message.value;
  const chatWindow = document.getElementById("chat-window");

  chatWindow.innerHTML += `
    <div class="chat-msg user"><span class="chat-role">You</span>${message}</div>
  `;
  chatWindow.scrollTop = chatWindow.scrollHeight;
  form.reset();

  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  const data = await res.json();

  chatWindow.innerHTML += `
    <div class="chat-msg assistant"><span class="chat-role">Tutor</span>${data.reply}</div>
  `;
  chatWindow.scrollTop = chatWindow.scrollHeight;
});

// ---------------- Initial load ----------------

loadDashboard();
loadCharts();