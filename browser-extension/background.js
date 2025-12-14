// Claudsidian Browser Extension - Background Service Worker
// Service worker for Manifest V3 that handles:
// - One-click capture (clicking the extension icon)
// - Context menu for right-click options
// - Research subject capture flow

const API_URL = "http://localhost:8765";

// =============================================================================
// Extension Icon Click Handler - Direct Capture
// =============================================================================

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.url) {
    showNotification(false, null, "No URL to capture");
    return;
  }

  // Skip chrome:// and other internal URLs
  if (tab.url.startsWith("chrome://") || tab.url.startsWith("about:") || tab.url.startsWith("edge://")) {
    showNotification(false, null, "Cannot capture browser internal pages");
    return;
  }

  await captureUrl(tab.url, tab.title || "Untitled");
});

// =============================================================================
// Context Menu Setup
// =============================================================================

chrome.runtime.onInstalled.addListener(() => {
  // Remove existing menu items first
  chrome.contextMenus.removeAll(() => {
    // Context menu on page/link
    chrome.contextMenus.create({
      id: "claudsidian-capture",
      title: "Capture with Claudsidian",
      contexts: ["page", "link"],
    });

    chrome.contextMenus.create({
      id: "claudsidian-research",
      title: "Add to Research Subject",
      contexts: ["page", "link"],
    });

    chrome.contextMenus.create({
      id: "separator1",
      type: "separator",
      contexts: ["page", "link"],
    });

    chrome.contextMenus.create({
      id: "claudsidian-options",
      title: "Open Capture Options...",
      contexts: ["page", "link"],
    });
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const url = info.linkUrl || info.pageUrl;
  const title = tab?.title || "Untitled";

  if (info.menuItemId === "claudsidian-capture") {
    await captureUrl(url, title);
  } else if (info.menuItemId === "claudsidian-research") {
    // Open research subject popup
    openResearchPopup(url, title);
  } else if (info.menuItemId === "claudsidian-options") {
    // Open the full options popup
    openOptionsPopup();
  }
});

// =============================================================================
// Capture Functions
// =============================================================================

async function captureUrl(url, title) {
  showNotification(null, null, `Capturing: ${title.slice(0, 50)}...`, true);

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
      showNotification(true, data.title);
    } else if (response.status === 409) {
      showNotification(false, null, `Already captured: ${data.existing_note}`);
    } else {
      showNotification(false, null, data.message || "Capture failed");
    }
  } catch (error) {
    if (error.name === "TypeError" && error.message.includes("fetch")) {
      showNotification(false, null, "Cannot connect to Claudsidian server. Is it running?");
    } else {
      showNotification(false, null, `Error: ${error.message}`);
    }
  }
}

async function captureToSubject(url, title, subjectName) {
  showNotification(null, null, `Capturing to ${subjectName}...`, true);

  try {
    const response = await fetch(`${API_URL}/capture`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url: url,
        source: "browser",
        research_subject: subjectName,  // Tell server to put in subject folder
      }),
    });

    const data = await response.json();

    if (response.ok) {
      showNotification(true, `${data.title} → ${subjectName}`);
    } else if (response.status === 409) {
      showNotification(false, null, `Already captured: ${data.existing_note}`);
    } else {
      showNotification(false, null, data.message || "Capture failed");
    }
  } catch (error) {
    showNotification(false, null, `Error: ${error.message}`);
  }
}

// =============================================================================
// Popup Helpers
// =============================================================================

function openResearchPopup(url, title) {
  // Store URL and title for the popup to use
  chrome.storage.local.set({
    pendingResearchCapture: { url, title }
  }, () => {
    // Open the research popup
    chrome.action.setPopup({ popup: "research-popup.html" });
    chrome.action.openPopup();

    // Reset popup after a delay (so next click captures directly)
    setTimeout(() => {
      chrome.action.setPopup({ popup: "" });
    }, 100);
  });
}

function openOptionsPopup() {
  chrome.action.setPopup({ popup: "popup.html" });
  chrome.action.openPopup();

  // Reset popup after a delay
  setTimeout(() => {
    chrome.action.setPopup({ popup: "" });
  }, 100);
}

// =============================================================================
// Notifications
// =============================================================================

function showNotification(success, title, error, isLoading = false) {
  let notificationTitle, notificationMessage;

  if (isLoading) {
    notificationTitle = "Claudsidian";
    notificationMessage = error; // error param is used as message for loading
  } else if (success) {
    notificationTitle = "Captured!";
    notificationMessage = title || "Page captured successfully";
  } else {
    notificationTitle = "Capture Failed";
    notificationMessage = error || "Unknown error";
  }

  chrome.notifications.create({
    type: "basic",
    iconUrl: "icons/icon48.png",
    title: notificationTitle,
    message: notificationMessage,
  });
}

// =============================================================================
// Message Handler (for popups)
// =============================================================================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "CAPTURE_RESULT") {
    showNotification(message.success, message.title, message.error);
  } else if (message.type === "CAPTURE_TO_SUBJECT") {
    captureToSubject(message.url, message.title, message.subjectName);
  } else if (message.type === "GET_PENDING_CAPTURE") {
    chrome.storage.local.get("pendingResearchCapture", (result) => {
      sendResponse(result.pendingResearchCapture || null);
    });
    return true; // Keep channel open for async response
  }
});

// =============================================================================
// Server Status Check
// =============================================================================

async function checkServerStatus() {
  try {
    const response = await fetch(`${API_URL}/status`);
    if (response.ok) {
      console.log("Claudsidian server is running");
    }
  } catch (error) {
    console.log("Claudsidian server is not running");
  }
}

checkServerStatus();
