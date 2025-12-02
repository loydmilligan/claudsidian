// Claudsidian Browser Extension - Popup Script

const API_URL = "http://localhost:8765";

// DOM Elements
let currentUrlEl;
let captureBtn;
let statusEl;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", init);

async function init() {
  currentUrlEl = document.getElementById("current-url");
  captureBtn = document.getElementById("capture-btn");
  statusEl = document.getElementById("status");

  // Get current tab URL
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  const currentUrl = tabs[0]?.url || "";

  // Display URL (truncate if long)
  currentUrlEl.textContent = truncateUrl(currentUrl, 50);
  currentUrlEl.title = currentUrl; // Full URL on hover

  // Set up capture button
  captureBtn.addEventListener("click", () => captureUrl(currentUrl));
}

function truncateUrl(url, maxLength) {
  if (url.length <= maxLength) return url;
  return url.substring(0, maxLength - 3) + "...";
}

async function captureUrl(url) {
  // Disable button and show loading
  captureBtn.disabled = true;
  captureBtn.textContent = "Capturing...";
  showStatus("loading", "Sending to Claudsidian...");

  try {
    const response = await fetch(`${API_URL}/capture`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url: url,
        source: "browser",
      }),
    });

    const data = await response.json();

    if (response.ok) {
      // Success
      showStatus("success", `Captured: ${data.title}\n→ ${data.note_path}`);
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
