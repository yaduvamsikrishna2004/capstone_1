import { checkHealth, checkNotificationHealth, getApiBaseUrl, getChatHistory, sendEmail, sendSMS, sendWhatsapp, setApiBaseUrl } from "./api.js";
import { createChatController } from "./chat.js";
import { createHistoryListController, createHistoryStore } from "./history.js";
import { createNotifier } from "./notifications.js";
import { initTheme } from "./theme.js";
import { createUploadController } from "./upload.js";
import { formatBytes, formatDate, loadStorage, qs, qsa, saveStorage } from "./utils.js";

const USER_KEY = "docassist_user_id";
const DOCS_KEY = "docassist_documents";

const notifier = createNotifier(qs("#toastStack"));
initTheme(qs("#themeToggleBtn"));

const state = {
  userId: localStorage.getItem(USER_KEY) || "web_user",
  documents: loadStorage(DOCS_KEY, []),
  uploadQueueCount: 0,
  serverHistoryOffset: 0,
  serverHistoryPageSize: 20,
  serverHistoryItems: [],
  notifications: {
    email: true,
    whatsapp: true,
    sms: true,
  },
};

const elements = {
  sidebar: qs("#sidebar"),
  newChatBtn: qs("#newChatBtn"),
  chatHistoryList: qs("#chatHistoryList"),
  chatSearchInput: qs("#chatSearchInput"),
  chatMessages: qs("#chatMessages"),
  loadOlderBtn: qs("#loadOlderMessagesBtn"),
  chatInput: qs("#chatInput"),
  sendBtn: qs("#sendBtn"),
  charCount: qs("#charCount"),
  typingIndicator: qs("#typingIndicator"),
  welcomeScreen: qs("#welcomeScreen"),
  uploadStage: qs("#uploadStage"),
  fileChipStrip: qs("#fileChipStrip"),
  fileChipList: qs("#fileChipList"),
  addFileChipBtn: qs("#addFileChipBtn"),
  fileInput: qs("#fileInput"),
  dropzone: qs("#dropzone"),
  uploadQueue: qs("#uploadQueue"),
  uploadNowBtn: qs("#uploadNowBtn"),
  clearQueueBtn: qs("#clearUploadQueueBtn"),
  attachFromComposerBtn: qs("#attachFromComposerBtn"),
  voicePlaceholderBtn: qs("#voicePlaceholderBtn"),
  documentList: qs("#documentList"),
  documentStatus: qs("#documentStatus"),
  healthPill: qs("#healthPill"),
  loadMoreHistoryBtn: qs("#loadMoreHistoryBtn"),
  serverHistoryList: qs("#serverHistoryList"),
  sidebarCollapseBtn: qs("#sidebarCollapseBtn"),
  mobileSidebarToggle: qs("#mobileSidebarToggle"),
  documentDrawerToggle: qs("#documentDrawerToggle"),
  documentDrawerClose: qs("#documentDrawerClose"),
  documentDrawer: qs("#documentDrawer"),
  drawerBackdrop: qs("#drawerBackdrop"),
  settingsBtn: qs("#settingsBtn"),
  logoutBtn: qs("#logoutBtn"),
  apiBaseInput: qs("#apiBaseInput"),
  userIdInput: qs("#userIdInput"),
  saveSettingsBtn: qs("#saveSettingsBtn"),
};

const historyStore = createHistoryStore();

function setDrawerOpen(value) {
  document.body.classList.toggle("drawer-open", value);
  elements.drawerBackdrop.classList.toggle("hidden", !value);
}

function renderFileChips() {
  elements.fileChipList.innerHTML = "";
  if (!state.documents.length) {
    elements.fileChipStrip.classList.add("hidden");
    return;
  }

  state.documents
    .slice(0, 16)
    .forEach((doc) => {
      const chip = document.createElement("span");
      chip.className = "file-chip";
      chip.innerHTML = `?? ${doc.name} <button type="button" data-name="${doc.name}">×</button>`;
      chip.querySelector("button")?.addEventListener("click", () => {
        state.documents = state.documents.filter((item) => item.name !== doc.name);
        saveStorage(DOCS_KEY, state.documents);
        renderDocumentList();
      });
      elements.fileChipList.appendChild(chip);
    });

  elements.fileChipStrip.classList.remove("hidden");
}

function updateUploadVisibility() {
  const shouldShowUpload = state.uploadQueueCount > 0 || state.documents.length === 0;
  elements.uploadStage.classList.toggle("hidden", !shouldShowUpload);
}

function renderDocumentList() {
  const list = state.documents;
  if (!list.length) {
    elements.documentList.innerHTML = "<div class=\"doc-item\"><small>No uploaded documents yet.</small></div>";
    elements.documentStatus.textContent = state.uploadQueueCount > 0
      ? `${state.uploadQueueCount} file(s) ready for upload`
      : "No documents uploaded";
    renderFileChips();
    updateUploadVisibility();
    return;
  }

  elements.documentList.innerHTML = "";
  list
    .sort((a, b) => b.uploadedAt - a.uploadedAt)
    .slice(0, 20)
    .forEach((doc) => {
      const item = document.createElement("article");
      item.className = "doc-item";
      item.innerHTML = `
        <strong title="${doc.name}">${doc.name}</strong>
        <small>${formatBytes(doc.size)} - ${formatDate(doc.uploadedAt)}</small>
      `;
      elements.documentList.appendChild(item);
    });

  elements.documentStatus.textContent = `${list.length} document(s) indexed`;
  renderFileChips();
  updateUploadVisibility();
}

function openModal(id) {
  qs(`#${id}`)?.classList.remove("hidden");
}

function closeModal(id) {
  qs(`#${id}`)?.classList.add("hidden");
}

function bindModalControls() {
  qsa("[data-modal-target]").forEach((button) => {
    button.addEventListener("click", () => openModal(button.dataset.modalTarget));
  });

  qsa("[data-close-modal]").forEach((button) => {
    button.addEventListener("click", () => closeModal(button.dataset.closeModal));
  });

  qsa(".modal-overlay").forEach((overlay) => {
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) overlay.classList.add("hidden");
    });
  });
}

function setSidebarMobile(value) {
  document.body.classList.toggle("sidebar-mobile-open", value);
}

function toggleSidebarCollapse() {
  document.body.classList.toggle("sidebar-collapsed");
}

function initHealthPolling() {
  async function run() {
    try {
      const result = await checkHealth();
      elements.healthPill.classList.remove("error");
      elements.healthPill.classList.add("ok");
      elements.healthPill.querySelector("span:last-child").textContent = result.status === "ok" ? "API healthy" : "API status unknown";
    } catch {
      elements.healthPill.classList.remove("ok");
      elements.healthPill.classList.add("error");
      elements.healthPill.querySelector("span:last-child").textContent = "API unavailable";
    }
  }

  run();
  setInterval(run, 60000);
}

function validatePhone(value) {
  const compact = value.trim().replace(/\s+/g, "").replace(/-/g, "");
  const candidate = compact.toLowerCase().startsWith("whatsapp:") ? compact.slice("whatsapp:".length) : compact;
  return /^\+?[1-9]\d{7,14}$/.test(candidate);
}

function getChannelReady(channel) {
  return Boolean(state.notifications[channel]);
}

function setChannelActionsEnabled(channel, enabled) {
  const modalTrigger = qs(`[data-modal-target="${channel}Modal"]`);
  const submitButton = qs(`#${channel}Form button[type='submit']`);
  if (modalTrigger) modalTrigger.disabled = !enabled;
  if (submitButton) submitButton.disabled = !enabled;
}

async function submitDelivery(formElement, channel) {
  if (!getChannelReady(channel)) {
    notifier.error(`${channel.toUpperCase()} is not configured in backend environment variables.`);
    return;
  }

  const formData = new FormData(formElement);
  const recipient = `${formData.get("recipient") || ""}`.trim();
  const message = `${formData.get("message") || ""}`.trim();
  const subject = `${formData.get("subject") || "AI Generated Summary"}`.trim();

  if (!recipient || !message) {
    notifier.error("Recipient and message are required.");
    return;
  }

  if (channel !== "email" && !validatePhone(recipient)) {
    notifier.error("Recipient phone must be in valid international format.");
    return;
  }

  const submitBtn = formElement.querySelector("button[type='submit']");
  submitBtn.disabled = true;
  submitBtn.textContent = "Sending...";

  const payload = {
    destination: recipient,
    message,
    subject,
    user_id: state.userId,
  };

  try {
    let response;
    if (channel === "email") response = await sendEmail(payload);
    if (channel === "whatsapp") response = await sendWhatsapp(payload);
    if (channel === "sms") response = await sendSMS(payload);

    const providerId = response?.provider_id ? ` Provider ID: ${response.provider_id}` : "";
    notifier.success(`${channel.toUpperCase()} sent successfully.${providerId}`);
    formElement.reset();
    closeModal(`${channel}Modal`);
  } catch (error) {
    notifier.error(error.message || `Failed to send ${channel}.`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = channel === "email" ? "Send Email" : channel === "whatsapp" ? "Send WhatsApp" : "Send SMS";
  }
}

function bindDeliveryForms() {
  qs("#emailForm").addEventListener("submit", (event) => {
    event.preventDefault();
    submitDelivery(event.currentTarget, "email");
  });

  qs("#whatsappForm").addEventListener("submit", (event) => {
    event.preventDefault();
    submitDelivery(event.currentTarget, "whatsapp");
  });

  qs("#smsForm").addEventListener("submit", (event) => {
    event.preventDefault();
    submitDelivery(event.currentTarget, "sms");
  });
}

function hydrateModalDefaults() {
  elements.apiBaseInput.value = getApiBaseUrl();
  elements.userIdInput.value = state.userId;

  elements.settingsBtn.addEventListener("click", () => openModal("settingsModal"));
  elements.saveSettingsBtn.addEventListener("click", () => {
    const url = elements.apiBaseInput.value.trim();
    const userId = elements.userIdInput.value.trim() || "web_user";

    if (!url) {
      notifier.error("API Base URL cannot be empty.");
      return;
    }

    setApiBaseUrl(url);
    state.userId = userId;
    localStorage.setItem(USER_KEY, userId);
    notifier.success("Settings saved.");
    closeModal("settingsModal");
    initHealthPolling();
    refreshNotificationHealth();
    loadServerHistory(true);
  });
}

async function refreshNotificationHealth() {
  try {
    const payload = await checkNotificationHealth();
    const channels = payload?.channels || {};
    state.notifications.email = Boolean(channels?.email?.configured);
    state.notifications.whatsapp = Boolean(channels?.whatsapp?.configured);
    state.notifications.sms = Boolean(channels?.sms?.configured);

    setChannelActionsEnabled("email", state.notifications.email);
    setChannelActionsEnabled("whatsapp", state.notifications.whatsapp);
    setChannelActionsEnabled("sms", state.notifications.sms);

    const disabledChannels = Object.entries(state.notifications)
      .filter(([, configured]) => !configured)
      .map(([name]) => name.toUpperCase());

    if (disabledChannels.length) {
      notifier.info(`Configure backend env vars for: ${disabledChannels.join(", ")}`);
    }
  } catch (error) {
    notifier.error(error.message || "Unable to validate notification endpoints.");
  }
}

function renderServerHistoryChunk(items, reset = false) {
  if (reset) {
    elements.serverHistoryList.innerHTML = "";
  }

  if (!items.length && reset) {
    elements.serverHistoryList.innerHTML = "<div class=\"history-item\"><small>No history records found.</small></div>";
    return;
  }

  items.forEach((item) => {
    const article = document.createElement("article");
    article.className = "history-item";
    article.innerHTML = `
      <strong>${item.query ? item.query.slice(0, 56) : "Chat Query"}</strong>
      <small>${formatDate(item.created_at)} - ${item.user_id}</small>
    `;
    elements.serverHistoryList.appendChild(article);
  });
}

async function loadServerHistory(reset = false) {
  if (reset) {
    state.serverHistoryOffset = 0;
    state.serverHistoryItems = [];
    elements.serverHistoryList.innerHTML = "<div class=\"history-item skeleton\" style=\"height:54px\"></div><div class=\"history-item skeleton\" style=\"height:54px\"></div>";
  }

  try {
    const limit = state.serverHistoryOffset + state.serverHistoryPageSize;
    const payload = await getChatHistory(limit);
    const items = Array.isArray(payload.items) ? payload.items : [];
    state.serverHistoryItems = items;
    const chunk = items.slice(state.serverHistoryOffset, state.serverHistoryOffset + state.serverHistoryPageSize);
    renderServerHistoryChunk(chunk, reset);
    state.serverHistoryOffset += chunk.length;
    elements.loadMoreHistoryBtn.disabled = state.serverHistoryOffset >= items.length;
  } catch (error) {
    notifier.error(error.message || "Unable to load server history.");
  }
}

const historyController = createHistoryListController({
  listElement: elements.chatHistoryList,
  searchInput: elements.chatSearchInput,
  store: historyStore,
  onSelect: () => {
    chatController.resetVisible();
    chatController.renderMessages();
  },
});

const chatController = createChatController({
  chatListEl: elements.chatMessages,
  typingEl: elements.typingIndicator,
  loadOlderBtn: elements.loadOlderBtn,
  chatInputEl: elements.chatInput,
  sendBtn: elements.sendBtn,
  charCountEl: elements.charCount,
  welcomeEl: elements.welcomeScreen,
  historyStore,
  notifier,
  getUserId: () => state.userId,
});

createUploadController({
  dropzoneEl: elements.dropzone,
  fileInputEl: elements.fileInput,
  uploadQueueEl: elements.uploadQueue,
  uploadNowBtn: elements.uploadNowBtn,
  clearQueueBtn: elements.clearQueueBtn,
  notifier,
  onUploadComplete: (documents) => {
    state.documents = [...documents, ...state.documents];
    saveStorage(DOCS_KEY, state.documents);
    renderDocumentList();
  },
  onStatusChange: (count) => {
    state.uploadQueueCount = count;
    if (!state.documents.length && !count) {
      elements.documentStatus.textContent = "No documents uploaded";
    } else if (count > 0) {
      elements.documentStatus.textContent = `${count} file(s) ready for upload`;
    } else {
      elements.documentStatus.textContent = `${state.documents.length} document(s) indexed`;
    }
    updateUploadVisibility();
  },
});

function bindMainActions() {
  elements.newChatBtn.addEventListener("click", () => {
    historyStore.createChat();
    historyController.refresh(elements.chatSearchInput.value);
    chatController.resetVisible();
    chatController.renderMessages();
    notifier.info("New chat created.");
  });

  qsa(".quick-action").forEach((button) => {
    button.addEventListener("click", () => {
      chatController.sendPrompt(button.dataset.prompt || "");
      setDrawerOpen(false);
    });
  });

  qsa("[data-prompt]", elements.welcomeScreen).forEach((button) => {
    button.addEventListener("click", () => chatController.sendPrompt(button.dataset.prompt || ""));
  });

  elements.attachFromComposerBtn.addEventListener("click", () => elements.fileInput.click());
  elements.addFileChipBtn.addEventListener("click", () => elements.fileInput.click());
  elements.voicePlaceholderBtn.addEventListener("click", () => notifier.info("Voice input can be integrated here."));
  elements.loadMoreHistoryBtn.addEventListener("click", () => loadServerHistory(false));

  elements.sidebarCollapseBtn.addEventListener("click", toggleSidebarCollapse);
  elements.mobileSidebarToggle.addEventListener("click", () => setSidebarMobile(true));

  elements.documentDrawerToggle.addEventListener("click", () => setDrawerOpen(true));
  elements.documentDrawerClose.addEventListener("click", () => setDrawerOpen(false));
  elements.drawerBackdrop.addEventListener("click", () => setDrawerOpen(false));

  document.addEventListener("click", (event) => {
    if (window.innerWidth <= 1080) {
      const withinSidebar = elements.sidebar.contains(event.target);
      const clickedToggle = event.target.closest("#mobileSidebarToggle");
      if (!withinSidebar && !clickedToggle) setSidebarMobile(false);
    }
  });

  elements.logoutBtn.addEventListener("click", () => {
    localStorage.removeItem(USER_KEY);
    notifier.success("Logged out from frontend session.");
  });
}

function bootstrap() {
  bindModalControls();
  bindDeliveryForms();
  hydrateModalDefaults();
  bindMainActions();
  renderDocumentList();
  initHealthPolling();
  refreshNotificationHealth();
  loadServerHistory(true);

  const currentChat = historyStore.getCurrentChat();
  const latestAssistant = [...(currentChat?.messages || [])].reverse().find((message) => message.role === "assistant");
  if (latestAssistant) {
    qs("textarea[name='message']", qs("#emailForm")).value = latestAssistant.content;
    qs("textarea[name='message']", qs("#whatsappForm")).value = latestAssistant.content;
    qs("textarea[name='message']", qs("#smsForm")).value = latestAssistant.content;
  }
  chatController.renderMessages();
}

bootstrap();
