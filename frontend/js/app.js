// ============================================================
// app.js — talks to the FastAPI backend at API_BASE.
// ============================================================

const API_BASE = "http://localhost:8000";

// ---------------- Tab navigation ----------------

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));

    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");

    if (btn.dataset.tab === "dashboard") loadDashboard();
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
    </tr>
  `).join("");
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