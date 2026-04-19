/* global Chart */

const fmt = (n) =>
  new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(n);

function apiUrl(path) {
  const root = (typeof window !== "undefined" && window.__API_ROOT__) || "";
  const r = String(root).replace(/\/$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return r ? `${r}${p}` : p;
}

function safeNewChart(ctx, config) {
  if (typeof Chart === "undefined" || !ctx) {
    return null;
  }
  try {
    return new Chart(ctx, config);
  } catch (e) {
    console.warn("Chart skipped:", e);
    return null;
  }
}

async function fetchJson(path, options) {
  const res = await fetch(apiUrl(path), options);
  const ct = res.headers.get("content-type") || "";
  let data = {};
  if (ct.includes("application/json")) {
    try {
      data = await res.json();
    } catch {
      data = {};
    }
  } else {
    const t = await res.text();
    data = { error: (t && t.slice(0, 400)) || res.statusText || "Non-JSON response" };
  }
  if (!res.ok) {
    throw new Error(data.error || res.statusText);
  }
  return data;
}

let monthlyChart;
let pieChart;
let cashChart;
let savingsChart;

function destroyChart(ref) {
  if (ref) ref.destroy();
  return null;
}

async function loadSummary() {
  const s = await fetchJson("/api/dashboard/summary");
  document.getElementById("m-income").textContent = `₹${fmt(s.income)}`;
  document.getElementById("m-expense").textContent = `₹${fmt(s.expense)}`;
  document.getElementById("m-net").textContent = `₹${fmt(s.net)}`;
  document.getElementById("m-rate").textContent = `${s.savings_rate}%`;
}

async function loadMonthlySpend() {
  const { series } = await fetchJson("/api/dashboard/monthly-trend");
  const labels = series.map((r) => r.month);
  const ctx = document.getElementById("chart-monthly");
  monthlyChart = destroyChart(monthlyChart);
  monthlyChart = safeNewChart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Total spend",
          data: series.map((r) => r.expense),
          backgroundColor: "#fbbf24",
        },
      ],
    },
    options: {
      scales: {
        x: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
        y: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
      },
      plugins: { legend: { labels: { color: "#e8eefc" } } },
    },
  });
}

async function loadCategoryPie() {
  const { breakdown } = await fetchJson("/api/dashboard/category-breakdown");
  const labels = breakdown.map((b) => b.category);
  const values = breakdown.map((b) => b.spent);
  const ctx = document.getElementById("chart-category");
  pieChart = destroyChart(pieChart);
  pieChart = safeNewChart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: [
            "#5eead4",
            "#7c9cff",
            "#fbbf24",
            "#fb7185",
            "#a78bfa",
            "#34d399",
            "#f97316",
            "#38bdf8",
          ],
          borderWidth: 0,
        },
      ],
    },
    options: {
      plugins: { legend: { labels: { color: "#e8eefc" } } },
    },
  });
}

async function loadCashflow() {
  const { series } = await fetchJson("/api/dashboard/monthly-trend");
  const labels = series.map((r) => r.month);
  const ctx = document.getElementById("chart-cashflow");
  cashChart = destroyChart(cashChart);
  cashChart = safeNewChart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Income",
          data: series.map((r) => r.income),
          borderColor: "#4ade80",
          backgroundColor: "rgba(74,222,128,0.15)",
          tension: 0.25,
          fill: true,
        },
        {
          label: "Expense",
          data: series.map((r) => r.expense),
          borderColor: "#fb7185",
          backgroundColor: "rgba(251,113,133,0.12)",
          tension: 0.25,
          fill: true,
        },
      ],
    },
    options: {
      scales: {
        x: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
        y: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
      },
      plugins: { legend: { labels: { color: "#e8eefc" } } },
    },
  });
}

async function loadSavings() {
  const { series } = await fetchJson("/api/dashboard/monthly-trend");
  const labels = series.map((r) => r.month);
  const ctx = document.getElementById("chart-savings");
  savingsChart = destroyChart(savingsChart);
  savingsChart = safeNewChart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Monthly savings",
          data: series.map((r) => r.savings ?? r.income - r.expense),
          backgroundColor: "#7c9cff",
        },
      ],
    },
    options: {
      scales: {
        x: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
        y: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
      },
      plugins: { legend: { labels: { color: "#e8eefc" } } },
    },
  });
}

async function loadInsights() {
  const { insights } = await fetchJson("/api/dashboard/insights");
  const ul = document.getElementById("insight-list");
  ul.innerHTML = "";
  if (!insights.length) {
    ul.innerHTML = "<li>Upload data to generate insights.</li>";
    return;
  }
  insights.forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    ul.appendChild(li);
  });
}

async function loadHealthBlock() {
  const scoreEl = document.getElementById("health-score");
  const copyEl = document.getElementById("health-copy");
  try {
    const h = await fetchJson("/api/dashboard/health-score");
    scoreEl.textContent = String(h.score);
    copyEl.textContent = h.headline || "";
  } catch {
    scoreEl.textContent = "—";
    copyEl.textContent = "Upload data to compute your score.";
  }
}

async function loadSubscriptionsBlock() {
  const ul = document.getElementById("sub-list");
  try {
    const s = await fetchJson("/api/dashboard/subscriptions");
    ul.innerHTML = "";
    if (!s.subscriptions?.length) {
      ul.innerHTML =
        '<li class="hint">No recurring pattern detected yet (same merchant + amount, ~monthly).</li>';
      return;
    }
    s.subscriptions.forEach((r) => {
      const li = document.createElement("li");
      li.innerHTML = `<strong>${r.merchant}</strong>: ₹${fmt(r.amount_monthly)}/mo <span class="tag">${r.occurrences}× · ~${r.cadence_days}d</span>`;
      ul.appendChild(li);
    });
    const li = document.createElement("li");
    li.style.marginTop = "6px";
    li.innerHTML = `<strong>Total detected</strong>: ₹${fmt(s.monthly_total)}/mo`;
    ul.appendChild(li);
  } catch {
    ul.innerHTML = '<li class="hint">No data.</li>';
  }
}

async function loadAnomaliesBlock() {
  const ul = document.getElementById("anomaly-list");
  try {
    const a = await fetchJson("/api/dashboard/anomalies");
    ul.innerHTML = "";
    if (!a.anomalies?.length) {
      ul.innerHTML = '<li class="hint">No 2× category spikes detected.</li>';
      return;
    }
    a.anomalies.slice(0, 6).forEach((r) => {
      const li = document.createElement("li");
      const tail = r.description.length > 28 ? `${r.description.slice(0, 28)}…` : r.description;
      li.innerHTML = `<strong>₹${fmt(r.amount)}</strong> · ${r.category} · ${tail} <span class="tag">${r.ratio_vs_avg}× avg</span>`;
      ul.appendChild(li);
    });
  } catch {
    ul.innerHTML = '<li class="hint">No data.</li>';
  }
}

let copilotChart;

function renderCopilotChart(type, payload) {
  const canvas = document.getElementById("chart-copilot");
  copilotChart = destroyChart(copilotChart);
  if (!type || type === "none") {
    return;
  }
  if (type === "pie" && payload?.breakdown) {
    copilotChart = safeNewChart(canvas, {
      type: "pie",
      data: {
        labels: payload.breakdown.map((b) => b.category),
        datasets: [
          {
            data: payload.breakdown.map((b) => b.spent),
            backgroundColor: ["#5eead4", "#7c9cff", "#fbbf24", "#fb7185", "#a78bfa"],
          },
        ],
      },
      options: { plugins: { legend: { labels: { color: "#e8eefc" } } } },
    });
  } else if (type === "bar" && payload?.anomalies?.length) {
    copilotChart = safeNewChart(canvas, {
      type: "bar",
      data: {
        labels: payload.anomalies.map((a) => `${a.category}`),
        datasets: [
          {
            label: "₹ (spike)",
            data: payload.anomalies.map((a) => a.amount),
            backgroundColor: "#fb7185",
          },
        ],
      },
      options: {
        indexAxis: "y",
        scales: {
          x: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
          y: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
        },
        plugins: { legend: { labels: { color: "#e8eefc" } } },
      },
    });
  } else if (type === "bar" && payload?.subscriptions?.length) {
    copilotChart = safeNewChart(canvas, {
      type: "bar",
      data: {
        labels: payload.subscriptions.map((s) => s.merchant.slice(0, 22)),
        datasets: [
          {
            label: "₹ / month",
            data: payload.subscriptions.map((s) => s.amount_monthly),
            backgroundColor: "#34d399",
          },
        ],
      },
      options: {
        indexAxis: "y",
        scales: {
          x: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
          y: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
        },
        plugins: { legend: { labels: { color: "#e8eefc" } } },
      },
    });
  } else if (type === "bar" && payload?.series) {
    copilotChart = safeNewChart(canvas, {
      type: "bar",
      data: {
        labels: payload.series.map((r) => r.month),
        datasets: [
          {
            label: "Spend",
            data: payload.series.map((r) => r.spent ?? r.amount),
            backgroundColor: "#5eead4",
          },
        ],
      },
      options: {
        scales: {
          x: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
          y: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
        },
        plugins: { legend: { labels: { color: "#e8eefc" } } },
      },
    });
  } else if (type === "bar" && payload?.merchants) {
    copilotChart = safeNewChart(canvas, {
      type: "bar",
      data: {
        labels: payload.merchants.map((r) => r.description.slice(0, 24)),
        datasets: [
          {
            label: "Spend",
            data: payload.merchants.map((r) => r.spent),
            backgroundColor: "#a78bfa",
          },
        ],
      },
      options: {
        indexAxis: "y",
        scales: {
          x: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
          y: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
        },
        plugins: { legend: { labels: { color: "#e8eefc" } } },
      },
    });
  } else if (type === "line") {
    if (payload?.cashflow) {
      copilotChart = safeNewChart(canvas, {
        type: "line",
        data: {
          labels: payload.cashflow.map((r) => r.month),
          datasets: [
            {
              label: "Income",
              data: payload.cashflow.map((r) => r.income),
              borderColor: "#4ade80",
              tension: 0.25,
            },
            {
              label: "Expense",
              data: payload.cashflow.map((r) => r.expense),
              borderColor: "#fb7185",
              tension: 0.25,
            },
          ],
        },
        options: {
          scales: {
            x: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
            y: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
          },
          plugins: { legend: { labels: { color: "#e8eefc" } } },
        },
      });
    } else if (payload?.series) {
      copilotChart = safeNewChart(canvas, {
        type: "line",
        data: {
          labels: payload.series.map((r) => r.month),
          datasets: [
            {
              label: "Spend",
              data: payload.series.map((r) => r.spent ?? 0),
              borderColor: "#7c9cff",
              tension: 0.25,
              fill: true,
              backgroundColor: "rgba(124,156,255,0.15)",
            },
          ],
        },
        options: {
          scales: {
            x: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
            y: { ticks: { color: "#8ea0c3" }, grid: { color: "#1f2b45" } },
          },
          plugins: { legend: { labels: { color: "#e8eefc" } } },
        },
      });
    }
  }
}

function appendChat(role, text) {
  const log = document.getElementById("chat-log");
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

async function sendCopilot() {
  const input = document.getElementById("copilot-query");
  if (!input) return;
  const query = input.value.trim();
  if (!query) return;
  appendChat("user", query);
  input.value = "";
  try {
    const res = await fetchJson("/api/copilot/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    appendChat("bot", (res.insight || "No insight returned.").replace(/ • /g, "\n"));
    renderCopilotChart(res.chart, res.data || {});
  } catch (err) {
    appendChat("bot", err.message || "Request failed");
  }
}

async function boot() {
  try {
    await loadSummary();
    await loadHealthBlock();
    await loadSubscriptionsBlock();
    await loadAnomaliesBlock();
    await loadMonthlySpend();
    await loadCategoryPie();
    await loadCashflow();
    await loadSavings();
    await loadInsights();
  } catch {
    document.getElementById("insight-list").innerHTML =
      "<li>Upload a CSV from the home page to populate the dashboard.</li>";
  }
}

function bindCopilotUi() {
  document.getElementById("copilot-send")?.addEventListener("click", sendCopilot);
  document.getElementById("copilot-query")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendCopilot();
    }
  });
}

bindCopilotUi();
boot();
