/* =============================================================
   Heart Disease Prediction — JavaScript
   Handles: password toggle, prediction fetch,
            chart init, sidebar, form UX, drag-drop
============================================================= */

// ─── Global chart instances ───
let accuracyChart = null;
let lossChart = null;

/* ─────────────────────────────────────────
   PASSWORD TOGGLE
───────────────────────────────────────── */
function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const isHidden = input.type === "password";
  input.type = isHidden ? "text" : "password";
  btn.innerHTML = isHidden
    ? `<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074l-1.78-1.781zm4.261 4.26l1.514 1.515a2.003 2.003 0 012.45 2.45l1.514 1.514a4 4 0 00-5.478-5.478z" clip-rule="evenodd"/><path d="M12.454 16.697L9.75 13.992a4 4 0 01-3.742-3.741L2.335 6.578A9.98 9.98 0 00.458 10c1.274 4.057 5.065 7 9.542 7 .847 0 1.669-.105 2.454-.303z"/></svg>`
    : `<svg viewBox="0 0 20 20" fill="currentColor"><path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/><path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"/></svg>`;
}

/* ─────────────────────────────────────────
   PREDICTION
───────────────────────────────────────── */
async function makePrediction(event) {
  event.preventDefault();

  const form = document.getElementById("predictForm");
  const btn = document.getElementById("predictBtn");
  const resultDiv = document.getElementById("predictionResult");

  // Button loading state
  btn.disabled = true;
  btn.innerHTML = `<svg class="spin" viewBox="0 0 24 24" style="width:18px;height:18px;"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" stroke-dasharray="32" stroke-dashoffset="12"/></svg> Analyzing…`;

  const formData = new FormData(form);

  try {
    const response = await fetch("/predict", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok || data.error) {
      showPredictionError(data.error || "Prediction failed.");
    } else {
      showPredictionResult(data);
    }
  } catch (err) {
    showPredictionError("Network error. Please try again.");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg viewBox="0 0 20 20" fill="currentColor" style="width:18px;height:18px;"><path fill-rule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clip-rule="evenodd"/></svg> Predict Now`;
  }
}

function showPredictionResult(data) {
  const resultDiv = document.getElementById("predictionResult");
  const iconEl = document.getElementById("resultIcon");
  const labelEl = document.getElementById("resultLabel");
  const probEl = document.getElementById("resultProbability");
  const barFill = document.getElementById("probBarFill");

  const isHigh = data.risk_level === "high";

  iconEl.innerHTML = isHigh ? "🫀" : "✅";
  iconEl.className = `result-icon ${isHigh ? "risk-high" : "risk-low"}`;
  labelEl.textContent = data.label;
  probEl.textContent = `Confidence Score: ${data.probability.toFixed(1)}% probability of heart disease`;

  resultDiv.className = `prediction-result ${isHigh ? "result-high" : "result-low"}`;
  resultDiv.classList.remove("hidden");

  // Animate bar after brief delay
  barFill.style.width = "0%";
  setTimeout(() => {
    barFill.style.width = `${data.probability}%`;
    barFill.style.background = isHigh
      ? "linear-gradient(90deg, #22c55e, #eab308, #f43f5e)"
      : "linear-gradient(90deg, #22c55e, #4ade80)";
  }, 50);

  resultDiv.scrollIntoView({ behavior: "smooth", block: "center" });
}

function showPredictionError(message) {
  const container = document.getElementById("flashContainer") || createFlashContainer();
  const div = document.createElement("div");
  div.className = "alert alert-error flash-toast";
  div.innerHTML = `<span class="alert-icon">✗</span>${message}<button class="alert-close" onclick="this.parentElement.remove()">×</button>`;
  container.appendChild(div);
  div.scrollIntoView({ behavior: "smooth", block: "center" });
}

function createFlashContainer() {
  const c = document.createElement("div");
  c.id = "flashContainer";
  c.className = "flash-container";
  const main = document.querySelector(".main-content");
  main.insertBefore(c, main.firstChild);
  return c;
}

/* ─────────────────────────────────────────
   RESET FORM
───────────────────────────────────────── */
function resetForm() {
  const form = document.getElementById("predictForm");
  if (form) form.reset();
  const result = document.getElementById("predictionResult");
  if (result) result.classList.add("hidden");
}

/* ─────────────────────────────────────────
   TRAINING BUTTON UX
───────────────────────────────────────── */
function startTraining(event, btn) {
  if (btn.disabled) return;
  const textEl = btn.querySelector(".btn-text");
  const loaderEl = btn.querySelector(".btn-loader");
  if (textEl) textEl.classList.add("hidden");
  if (loaderEl) loaderEl.classList.remove("hidden");
  
  // Disable asynchronously so the browser form submission isn't cancelled
  setTimeout(() => {
    btn.disabled = true;
  }, 10);
}

/* ─────────────────────────────────────────
   CHARTS
───────────────────────────────────────── */
function initCharts(history) {
  if (!history || !history.accuracy || history.accuracy.length === 0) return;

  const gridColor = "rgba(255,255,255,0.05)";
  const tickColor = "#475569";
  const legendColor = "#94a3b8";

  const sharedOptions = {
    responsive: true,
    maintainAspectRatio: true,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: {
        labels: { color: legendColor, font: { family: "Inter", size: 11 }, padding: 16 }
      },
      tooltip: {
        backgroundColor: "#1a1a2e",
        borderColor: "rgba(255,255,255,0.08)",
        borderWidth: 1,
        titleColor: "#f1f5f9",
        bodyColor: "#94a3b8",
        padding: 10,
        callbacks: {
          label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(4)}`
        }
      }
    },
    scales: {
      x: {
        ticks: { color: tickColor, font: { size: 10 } },
        grid: { color: gridColor },
        title: { display: true, text: "Epoch", color: tickColor, font: { size: 11 } }
      },
      y: {
        ticks: { color: tickColor, font: { size: 10 } },
        grid: { color: gridColor },
        beginAtZero: false,
      }
    }
  };

  const epochs = history.accuracy.map((_, i) => i + 1);

  // Accuracy Chart
  const accCtx = document.getElementById("accuracyChart");
  if (accCtx) {
    if (accuracyChart) accuracyChart.destroy();
    accuracyChart = new Chart(accCtx.getContext("2d"), {
      type: "line",
      data: {
        labels: epochs,
        datasets: [
          {
            label: "Train Accuracy",
            data: history.accuracy,
            borderColor: "#22c55e",
            backgroundColor: "rgba(34,197,94,0.1)",
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.3,
            fill: true,
          },
          {
            label: "Val Accuracy",
            data: history.val_accuracy,
            borderColor: "#3b82f6",
            backgroundColor: "rgba(59,130,246,0.1)",
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.3,
            fill: true,
          }
        ]
      },
      options: {
        ...sharedOptions,
        scales: {
          ...sharedOptions.scales,
          y: { ...sharedOptions.scales.y, min: 0, max: 1,
            title: { display: true, text: "Accuracy", color: tickColor, font: { size: 11 } }
          }
        }
      }
    });
  }

  // Loss Chart
  const lossCtx = document.getElementById("lossChart");
  if (lossCtx) {
    if (lossChart) lossChart.destroy();
    lossChart = new Chart(lossCtx.getContext("2d"), {
      type: "line",
      data: {
        labels: epochs,
        datasets: [
          {
            label: "Train Loss",
            data: history.loss,
            borderColor: "#f43f5e",
            backgroundColor: "rgba(244,63,94,0.1)",
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.3,
            fill: true,
          },
          {
            label: "Val Loss",
            data: history.val_loss,
            borderColor: "#f97316",
            backgroundColor: "rgba(249,115,22,0.1)",
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.3,
            fill: true,
          }
        ]
      },
      options: {
        ...sharedOptions,
        scales: {
          ...sharedOptions.scales,
          y: { ...sharedOptions.scales.y,
            title: { display: true, text: "Loss", color: tickColor, font: { size: 11 } }
          }
        }
      }
    });
  }
}

/* ─────────────────────────────────────────
   SIDEBAR
───────────────────────────────────────── */
function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");
  sidebar.classList.toggle("open");
  overlay.classList.toggle("open");
}

function scrollToSection(event, sectionId) {
  event.preventDefault();
  const el = document.getElementById(sectionId);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });

  // Update active nav link
  document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
  const link = document.querySelector(`[data-section="${sectionId}"]`);
  if (link) link.classList.add("active");

  // Close sidebar on mobile
  if (window.innerWidth <= 768) toggleSidebar();
}

/* ─────────────────────────────────────────
   ACTIVE NAV ON SCROLL (Intersection Observer)
───────────────────────────────────────── */
function initScrollSpy() {
  const sections = document.querySelectorAll(".content-section");
  if (!sections.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
        const link = document.querySelector(`[data-section="${id}"]`);
        if (link) link.classList.add("active");
      }
    });
  }, { threshold: 0.3 });

  sections.forEach(s => observer.observe(s));
}

/* ─────────────────────────────────────────
   DRAG & DROP for file upload
───────────────────────────────────────── */
function initDropZone() {
  const zone = document.getElementById("dropZone");
  const input = document.getElementById("dataset_file");
  if (!zone || !input) return;

  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("dragover");
  });

  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));

  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith(".csv")) {
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      document.getElementById("selectedFileName").textContent = `Selected: ${file.name}`;
    } else {
      alert("Please drop a .csv file.");
    }
  });
}

function triggerUpload(input) {
  const nameEl = document.getElementById("selectedFileName");
  if (input.files.length > 0 && nameEl) {
    nameEl.textContent = `Selected: ${input.files[0].name}`;
  }
}

/* ─────────────────────────────────────────
   AUTO-DISMISS FLASH MESSAGES
───────────────────────────────────────── */
function autoDismissFlash() {
  setTimeout(() => {
    document.querySelectorAll(".flash-toast").forEach(el => {
      el.style.transition = "opacity 0.4s ease";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 400);
    });
  }, 6000);
}

/* ─────────────────────────────────────────
   INIT ON DOM READY
───────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  initScrollSpy();
  initDropZone();
  autoDismissFlash();
});
