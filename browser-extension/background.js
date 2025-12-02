// Claudsidian Browser Extension - Background Service Worker
// Service worker for Manifest V3 that handles:
// - Message communication from popup
// - Browser notifications for capture results
// - Context menu integration for right-click capture

const API_URL = "http://localhost:8765";

// Listen for messages from popup or content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "CAPTURE_RESULT") {
    showNotification(message.success, message.title, message.error);
  }
  return true;
});

// Show notification for capture success or failure
function showNotification(success, title, error) {
  const notificationOptions = {
    type: "basic",
    iconUrl: "icons/icon48.png",
    title: success ? "Claudsidian" : "Capture Failed",
    message: success ? `Captured: ${title}` : error || "Unknown error",
  };

  chrome.notifications.create(notificationOptions);
}

// Optional: Context menu for right-click capture
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "claudsidian-capture",
    title: "Capture with Claudsidian",
    contexts: ["page", "link"],
  });
});

// Handle context menu click
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "claudsidian-capture") {
    const url = info.linkUrl || info.pageUrl;

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
      } else {
        showNotification(false, null, data.message || "Capture failed");
      }
    } catch (error) {
      showNotification(false, null, "Cannot connect to Claudsidian server");
    }
  }
});

// Check server status on startup
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

// Check server status when extension loads
checkServerStatus();
