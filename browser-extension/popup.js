// Claudsidian Browser Extension - Popup Script

const API_URL = "http://localhost:8765";

// DOM Elements
let currentUrlEl;
let captureBtn;
let statusEl;
let modelSelect;
let modelStats;
let inboxCheck;
let toggleAdvanced;
let advancedOptions;
let temperatureSlider;
let tempValue;

// Model data cache
let modelsData = null;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", init);

async function init() {
  // Get DOM elements
  currentUrlEl = document.getElementById("current-url");
  captureBtn = document.getElementById("capture-btn");
  statusEl = document.getElementById("status");
  modelSelect = document.getElementById("model-select");
  modelStats = document.getElementById("model-stats");
  inboxCheck = document.getElementById("inbox-check");
  toggleAdvanced = document.getElementById("toggle-advanced");
  advancedOptions = document.getElementById("advanced-options");
  temperatureSlider = document.getElementById("temperature");
  tempValue = document.getElementById("temp-value");

  // Get current tab URL
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  const currentUrl = tabs[0]?.url || "";

  // Display URL (truncate if long)
  currentUrlEl.textContent = truncateUrl(currentUrl, 50);
  currentUrlEl.title = currentUrl; // Full URL on hover

  // Set up event listeners
  captureBtn.addEventListener("click", () => captureUrl(currentUrl));

  // Model selection change - show stats
  modelSelect.addEventListener("change", updateModelStats);

  // Inbox checkbox - disable model options when checked
  inboxCheck.addEventListener("change", () => {
    const disabled = inboxCheck.checked;
    modelSelect.disabled = disabled;
    temperatureSlider.disabled = disabled;
    if (disabled) {
      modelStats.textContent = "";
    } else {
      updateModelStats();
    }
  });

  // Toggle advanced options
  toggleAdvanced.addEventListener("click", () => {
    advancedOptions.classList.toggle("show");
    const arrow = toggleAdvanced.querySelector("span");
    arrow.innerHTML = advancedOptions.classList.contains("show") ? "&#9650;" : "&#9660;";
  });

  // Temperature slider
  temperatureSlider.addEventListener("input", () => {
    const val = (temperatureSlider.value / 100).toFixed(1);
    tempValue.textContent = val;
  });

  // Load models from API
  await loadModels();
}

function truncateUrl(url, maxLength) {
  if (url.length <= maxLength) return url;
  return url.substring(0, maxLength - 3) + "...";
}

async function loadModels() {
  try {
    const response = await fetch(`${API_URL}/models`);
    if (response.ok) {
      modelsData = await response.json();

      // Populate model select
      modelsData.models.forEach(model => {
        const option = document.createElement("option");
        option.value = model.id;
        option.textContent = model.name;
        // Add capture count as hint
        if (model.captures > 0) {
          option.textContent += ` (${model.captures})`;
        }
        modelSelect.appendChild(option);
      });

      // Select default if matches
      if (modelsData.default_model) {
        modelSelect.value = modelsData.default_model;
        updateModelStats();
      }
    }
  } catch (error) {
    console.log("Could not load models:", error);
    // Keep default option only
  }
}

function updateModelStats() {
  if (!modelsData || !modelSelect.value) {
    modelStats.textContent = "";
    return;
  }

  const model = modelsData.models.find(m => m.id === modelSelect.value);
  if (model) {
    let stats = [];
    if (model.avg_cost > 0) {
      stats.push(`$${model.avg_cost.toFixed(4)}/cap`);
    }
    if (model.avg_rating) {
      stats.push(`${model.avg_rating.toFixed(1)}★`);
    }
    modelStats.textContent = stats.join(" · ");
  } else {
    modelStats.textContent = "";
  }
}

async function captureUrl(url) {
  // Disable button and show loading
  captureBtn.disabled = true;
  captureBtn.textContent = inboxCheck.checked ? "Quick capturing..." : "Capturing...";
  showStatus("loading", "Sending to Claudsidian...");

  try {
    // Build request body
    const body = {
      url: url,
      source: "browser",
    };

    // Add inbox mode flag
    if (inboxCheck.checked) {
      body.skip_ai = true;
    } else {
      // Add model override if not default
      if (modelSelect.value) {
        body.model = modelSelect.value;
      }

      // Add temperature if advanced options shown and not default
      if (advancedOptions.classList.contains("show")) {
        const temp = parseFloat((temperatureSlider.value / 100).toFixed(1));
        if (temp !== 0.7) {
          body.temperature = temp;
        }
      }
    }

    const response = await fetch(`${API_URL}/capture`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    if (response.ok) {
      // Success
      const mode = inboxCheck.checked ? " [Quick]" : "";
      showStatus("success", `Captured${mode}: ${data.title}\n→ ${data.note_path}`);
    } else if (response.status === 409) {
      // Duplicate
      showStatus("error", `Already captured:\n${data.existing_note}`);
    } else {
      // Error
      showStatus("error", data.message || "Capture failed");
    }
  } catch (error) {
    // Network error - server probably not running
    if (error.name === "TypeError" && error.message.includes("fetch")) {
      showStatus("error", "Cannot connect to Claudsidian server.\nMake sure 'claudsidian serve' is running.");
    } else {
      showStatus("error", `Error: ${error.message}`);
    }
  } finally {
    captureBtn.disabled = false;
    captureBtn.textContent = "Capture Page";
  }
}

function showStatus(type, message) {
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
  statusEl.classList.remove("hidden");
}
