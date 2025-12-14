// Claudsidian Browser Extension - Research Subject Popup

const API_URL = "http://localhost:8765";

// State
let pendingCapture = null;
let subjects = [];

// DOM Elements
let currentUrlEl;
let loadingState;
let mainContent;
let subjectSelect;
let newSubjectSection;
let newSubjectName;
let captureBtn;
let cancelBtn;
let statusEl;

document.addEventListener("DOMContentLoaded", init);

async function init() {
  // Get DOM elements
  currentUrlEl = document.getElementById("current-url");
  loadingState = document.getElementById("loading-state");
  mainContent = document.getElementById("main-content");
  subjectSelect = document.getElementById("subject-select");
  newSubjectSection = document.getElementById("new-subject-section");
  newSubjectName = document.getElementById("new-subject-name");
  captureBtn = document.getElementById("capture-btn");
  cancelBtn = document.getElementById("cancel-btn");
  statusEl = document.getElementById("status");

  // Set up event listeners
  subjectSelect.addEventListener("change", onSubjectChange);
  newSubjectName.addEventListener("input", updateCaptureButton);
  captureBtn.addEventListener("click", onCapture);
  cancelBtn.addEventListener("click", () => window.close());

  // Get pending capture from background
  chrome.runtime.sendMessage({ type: "GET_PENDING_CAPTURE" }, async (response) => {
    if (response) {
      pendingCapture = response;
      currentUrlEl.textContent = truncateUrl(response.url, 50);
      currentUrlEl.title = response.url;
    } else {
      // Fallback: get current tab URL
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tabs[0]) {
        pendingCapture = {
          url: tabs[0].url,
          title: tabs[0].title || "Untitled"
        };
        currentUrlEl.textContent = truncateUrl(tabs[0].url, 50);
        currentUrlEl.title = tabs[0].url;
      }
    }

    // Load subjects
    await loadSubjects();
  });
}

function truncateUrl(url, maxLength) {
  if (!url) return "No URL";
  if (url.length <= maxLength) return url;
  return url.substring(0, maxLength - 3) + "...";
}

async function loadSubjects() {
  try {
    const response = await fetch(`${API_URL}/subjects`);

    if (!response.ok) {
      throw new Error("Failed to load subjects");
    }

    const data = await response.json();
    subjects = data.subjects || [];

    // Populate dropdown
    subjectSelect.innerHTML = `
      <option value="">Choose a subject...</option>
      <option value="__new__">+ Create New Subject</option>
    `;

    for (const subject of subjects) {
      const option = document.createElement("option");
      option.value = subject.name;

      // Build display text
      let displayText = subject.name.replace(/-/g, " ");

      // Add badges
      const badges = [];
      if (!subject.has_wizard_complete) {
        badges.push("⚙️ setup pending");
      }
      if (subject.note_count > 0) {
        badges.push(`${subject.note_count} notes`);
      }

      if (badges.length > 0) {
        displayText += ` (${badges.join(", ")})`;
      }

      option.textContent = displayText;
      subjectSelect.appendChild(option);
    }

    // Show main content
    loadingState.classList.add("hidden");
    mainContent.classList.remove("hidden");

  } catch (error) {
    console.error("Failed to load subjects:", error);
    loadingState.textContent = "Cannot connect to Claudsidian server";
    showStatus("error", "Make sure 'claudsidian serve' is running");
  }
}

function onSubjectChange() {
  const value = subjectSelect.value;

  if (value === "__new__") {
    newSubjectSection.classList.add("show");
    newSubjectName.focus();
  } else {
    newSubjectSection.classList.remove("show");
  }

  updateCaptureButton();
}

function updateCaptureButton() {
  const selectedValue = subjectSelect.value;

  if (selectedValue === "__new__") {
    // Need a name for new subject
    captureBtn.disabled = !newSubjectName.value.trim();
  } else {
    // Need an existing subject selected
    captureBtn.disabled = !selectedValue;
  }
}

async function onCapture() {
  if (!pendingCapture) {
    showStatus("error", "No URL to capture");
    return;
  }

  const selectedValue = subjectSelect.value;
  let subjectName;

  if (selectedValue === "__new__") {
    // Create new subject first
    const newName = newSubjectName.value.trim();
    if (!newName) {
      showStatus("error", "Please enter a subject name");
      return;
    }

    captureBtn.disabled = true;
    captureBtn.textContent = "Creating...";
    showStatus("loading", "Creating subject...");

    try {
      const response = await fetch(`${API_URL}/subjects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName })
      });

      const data = await response.json();

      if (!data.success && !response.ok) {
        showStatus("error", data.message || "Failed to create subject");
        captureBtn.disabled = false;
        captureBtn.textContent = "Capture";
        return;
      }

      subjectName = data.name;
    } catch (error) {
      showStatus("error", `Error: ${error.message}`);
      captureBtn.disabled = false;
      captureBtn.textContent = "Capture";
      return;
    }
  } else {
    subjectName = selectedValue;
  }

  // Now capture to the subject
  captureBtn.textContent = "Capturing...";
  showStatus("loading", `Capturing to ${subjectName}...`);

  try {
    const response = await fetch(`${API_URL}/capture`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: pendingCapture.url,
        source: "browser",
        research_subject: subjectName
      })
    });

    const data = await response.json();

    if (response.ok) {
      showStatus("success", `Captured: ${data.title}`);

      // Notify background to show notification
      chrome.runtime.sendMessage({
        type: "CAPTURE_RESULT",
        success: true,
        title: `${data.title} → ${subjectName}`
      });

      // Close popup after brief delay
      setTimeout(() => window.close(), 1500);

    } else if (response.status === 409) {
      showStatus("error", `Already captured: ${data.existing_note}`);
      captureBtn.disabled = false;
      captureBtn.textContent = "Capture";
    } else {
      showStatus("error", data.message || "Capture failed");
      captureBtn.disabled = false;
      captureBtn.textContent = "Capture";
    }

  } catch (error) {
    showStatus("error", `Error: ${error.message}`);
    captureBtn.disabled = false;
    captureBtn.textContent = "Capture";
  }
}

function showStatus(type, message) {
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
  statusEl.classList.remove("hidden");
}
