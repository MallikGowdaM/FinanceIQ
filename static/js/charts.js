/**
 * charts.js — Shared Chart.js helper utilities for FinanceIQ Dashboard
 *
 * Provides:
 *  - Global Chart.js defaults (dark theme)
 *  - Factory functions: renderBar, renderDoughnut, renderLineChart,
 *    renderScatter, renderHorizontalBar
 *  - renderHeatmap() — canvas-free HTML table-based heatmap for correlations
 *  - destroyChart() — cleans up before re-render
 *  - getTickerColors() — consistent per-ticker colour palette
 *  - getCsrfToken() — reads Django CSRF cookie for POST requests
 */

// ─── Global Chart.js Defaults ─────────────────────────────────────────────────
Chart.defaults.color = "#94a3b8";
Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.plugins.legend.labels.boxWidth = 12;
Chart.defaults.plugins.legend.labels.padding = 16;
Chart.defaults.plugins.tooltip.backgroundColor = "#1a1d2e";
Chart.defaults.plugins.tooltip.borderColor = "#2d3148";
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.titleColor = "#e2e8f0";
Chart.defaults.plugins.tooltip.bodyColor = "#94a3b8";
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.scale.grid.color = "rgba(45,49,72,0.8)";
Chart.defaults.scale.ticks.color = "#94a3b8";

// ─── Chart Registry ───────────────────────────────────────────────────────────
const _chartRegistry = {};

/**
 * Destroy an existing chart before re-rendering to avoid Canvas re-use errors.
 * @param {string} canvasId
 */
function destroyChart(canvasId) {
  if (_chartRegistry[canvasId]) {
    _chartRegistry[canvasId].destroy();
    delete _chartRegistry[canvasId];
  }
}

// ─── Colour Palette ───────────────────────────────────────────────────────────
const TICKER_COLORS = [
  "#6366f1", "#10b981", "#f59e0b", "#ef4444", "#06b6d4",
  "#8b5cf6", "#ec4899", "#84cc16", "#f97316", "#14b8a6",
];

/**
 * Return a consistent colour array for a list of ticker labels.
 * @param {string[]} tickers
 * @returns {string[]}
 */
function getTickerColors(tickers) {
  return tickers.map((_, i) => TICKER_COLORS[i % TICKER_COLORS.length]);
}

// ─── Shared Axis Config ───────────────────────────────────────────────────────
function _yAxis(label) {
  return {
    grid: { color: "rgba(45,49,72,0.6)" },
    title: label ? { display: true, text: label, color: "#94a3b8", font: { size: 11 } } : undefined,
  };
}
function _xAxis(label) {
  return {
    grid: { color: "rgba(45,49,72,0.6)" },
    title: label ? { display: true, text: label, color: "#94a3b8", font: { size: 11 } } : undefined,
  };
}

// ─── renderBar ────────────────────────────────────────────────────────────────
/**
 * Render a vertical bar chart.
 * @param {string} canvasId
 * @param {object} chartData  — Chart.js data object {labels, datasets}
 * @param {object} opts       — {yLabel, tooltipSuffix}
 */
function renderBar(canvasId, chartData, opts = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const chart = new Chart(ctx, {
    type: "bar",
    data: chartData,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: chartData.datasets.length > 1 },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label || ""}: ${ctx.parsed.y}${opts.tooltipSuffix || ""}`,
          },
        },
      },
      scales: {
        y: _yAxis(opts.yLabel),
        x: _xAxis(opts.xLabel),
      },
    },
  });
  _chartRegistry[canvasId] = chart;
  return chart;
}

// ─── renderHorizontalBar ──────────────────────────────────────────────────────
/**
 * Render a horizontal bar chart (indexAxis: 'y').
 */
function renderHorizontalBar(canvasId, chartData, opts = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const chart = new Chart(ctx, {
    type: "bar",
    data: chartData,
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: chartData.datasets.length > 1 },
      },
      scales: {
        x: _xAxis(opts.xLabel),
        y: { grid: { display: false } },
      },
    },
  });
  _chartRegistry[canvasId] = chart;
  return chart;
}

// ─── renderDoughnut ───────────────────────────────────────────────────────────
/**
 * Render a doughnut / pie chart.
 */
function renderDoughnut(canvasId, chartData, opts = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const chart = new Chart(ctx, {
    type: "doughnut",
    data: chartData,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "55%",
      plugins: {
        legend: {
          position: "bottom",
          labels: { padding: 12, boxWidth: 10 },
        },
        tooltip: {
          callbacks: {
            label: ctx => {
              const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
              const pct = ((ctx.parsed / total) * 100).toFixed(1);
              return ` ${ctx.label}: ${ctx.parsed.toLocaleString()} (${pct}%)`;
            },
          },
        },
      },
    },
  });
  _chartRegistry[canvasId] = chart;
  return chart;
}

// ─── renderLineChart ──────────────────────────────────────────────────────────
/**
 * Render a multi-line time-series chart.
 */
function renderLineChart(canvasId, chartData, opts = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const chart = new Chart(ctx, {
    type: "line",
    data: chartData,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: true } },
      scales: {
        y: _yAxis(opts.yLabel),
        x: {
          ..._xAxis(opts.xLabel),
          ticks: {
            maxTicksLimit: 10,
            color: "#94a3b8",
            // Only show every Nth label to avoid crowding
            callback: function(val, index) {
              const labels = this.chart.data.labels;
              const step = Math.ceil(labels.length / 10);
              return index % step === 0 ? labels[index] : "";
            },
          },
        },
      },
    },
  });
  _chartRegistry[canvasId] = chart;
  return chart;
}

// ─── renderScatter ────────────────────────────────────────────────────────────
/**
 * Render a scatter plot (each dataset = one series/group).
 */
function renderScatter(canvasId, chartData, opts = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const chart = new Chart(ctx, {
    type: "scatter",
    data: chartData,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: true } },
      scales: {
        y: _yAxis(opts.yLabel),
        x: _xAxis(opts.xLabel),
      },
    },
  });
  _chartRegistry[canvasId] = chart;
  return chart;
}

// ─── renderHeatmap ────────────────────────────────────────────────────────────
/**
 * Render a correlation heatmap as an HTML table (no canvas needed).
 * Colour interpolates red(-1) → white(0) → green(+1).
 *
 * @param {string} containerId  — ID of the div container
 * @param {string[]} labels     — ticker labels
 * @param {number[][]} matrix   — NxN correlation matrix
 */
function renderHeatmap(containerId, labels, matrix) {
  const container = document.getElementById(containerId);
  if (!container || !labels.length) return;

  function corrColor(val) {
    // Interpolate between red, neutral grey, and green
    const r = val > 0
      ? Math.round(239 - val * 120)
      : Math.round(239);
    const g = val > 0
      ? Math.round(68 + val * 117)
      : Math.round(68 + (1 + val) * 120);
    const b = val > 0
      ? Math.round(68)
      : Math.round(68 + (1 + val) * 50);
    const alpha = 0.15 + Math.abs(val) * 0.65;
    return `rgba(${r},${g},${b},${alpha})`;
  }

  let html = `<table class="corr-heatmap"><thead><tr><th></th>`;
  labels.forEach(l => { html += `<th>${l}</th>`; });
  html += `</tr></thead><tbody>`;

  matrix.forEach((row, i) => {
    html += `<tr><th>${labels[i]}</th>`;
    row.forEach(val => {
      const display = typeof val === "number" ? val.toFixed(2) : "—";
      const textColor = Math.abs(val) > 0.5 ? "#e2e8f0" : "#94a3b8";
      html += `<td style="background:${corrColor(val)};color:${textColor};font-weight:600">${display}</td>`;
    });
    html += `</tr>`;
  });
  html += `</tbody></table>`;
  container.innerHTML = html;
}

// ─── CSRF Token ───────────────────────────────────────────────────────────────
/**
 * Read the Django CSRF token from cookies.
 * Required for all POST requests via fetch().
 * @returns {string}
 */
function getCsrfToken() {
  const name = "csrftoken";
  const cookies = document.cookie.split(";");
  for (let cookie of cookies) {
    const [key, val] = cookie.trim().split("=");
    if (key === name) return decodeURIComponent(val);
  }
  // Fallback: read from hidden input (if present)
  const input = document.querySelector("[name=csrfmiddlewaretoken]");
  return input ? input.value : "";
}
