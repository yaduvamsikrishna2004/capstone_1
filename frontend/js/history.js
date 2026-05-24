import { debounce, formatDate, loadStorage, saveStorage, truncate, uid } from "./utils.js";

const CHATS_KEY = "docassist_chats";
const CURRENT_CHAT_KEY = "docassist_current_chat";

function createDefaultChat() {
  return {
    id: uid("chat"),
    title: "New chat",
    createdAt: Date.now(),
    updatedAt: Date.now(),
    messages: [],
  };
}

export function createHistoryStore() {
  let chats = loadStorage(CHATS_KEY, []);
  let currentChatId = localStorage.getItem(CURRENT_CHAT_KEY);

  if (!Array.isArray(chats) || chats.length === 0) {
    const chat = createDefaultChat();
    chats = [chat];
    currentChatId = chat.id;
    persist();
  }

  if (!currentChatId || !chats.some((chat) => chat.id === currentChatId)) {
    currentChatId = chats[0].id;
    localStorage.setItem(CURRENT_CHAT_KEY, currentChatId);
  }

  function persist() {
    saveStorage(CHATS_KEY, chats);
    if (currentChatId) localStorage.setItem(CURRENT_CHAT_KEY, currentChatId);
  }

  function getChats() {
    return [...chats].sort((a, b) => b.updatedAt - a.updatedAt);
  }

  function getCurrentChat() {
    return chats.find((chat) => chat.id === currentChatId) || chats[0];
  }

  function createChat() {
    const chat = createDefaultChat();
    chats.push(chat);
    currentChatId = chat.id;
    persist();
    return chat;
  }

  function setCurrentChat(id) {
    if (!chats.some((chat) => chat.id === id)) return;
    currentChatId = id;
    persist();
  }

  function appendMessage(message) {
    const chat = getCurrentChat();
    if (!chat) return;
    chat.messages.push(message);
    chat.updatedAt = Date.now();
    if (chat.title === "New chat" && message.role === "user") {
      chat.title = truncate(message.content, 44);
    }
    persist();
  }

  function replaceMessage(messageId, patch) {
    const chat = getCurrentChat();
    if (!chat) return;
    const target = chat.messages.find((item) => item.id === messageId);
    if (!target) return;
    Object.assign(target, patch);
    chat.updatedAt = Date.now();
    persist();
  }

  function clearChatMessages(chatId) {
    const chat = chats.find((item) => item.id === chatId);
    if (!chat) return;
    chat.messages = [];
    chat.updatedAt = Date.now();
    chat.title = "New chat";
    persist();
  }

  return {
    getChats,
    getCurrentChat,
    createChat,
    setCurrentChat,
    appendMessage,
    replaceMessage,
    clearChatMessages,
  };
}

export function createHistoryListController({ listElement, searchInput, store, onSelect }) {
  let filtered = store.getChats();
  let renderedCount = 0;
  const pageSize = 14;

  function renderNextPage(reset = false) {
    if (reset) {
      listElement.innerHTML = "";
      renderedCount = 0;
    }

    const current = store.getCurrentChat();
    const chunk = filtered.slice(renderedCount, renderedCount + pageSize);
    chunk.forEach((chat) => {
      const button = document.createElement("button");
      button.className = "chat-history-item";
      button.type = "button";
      button.dataset.chatId = chat.id;
      if (current?.id === chat.id) button.classList.add("active");
      button.innerHTML = `
        <strong>${chat.title}</strong>
        <small>${chat.messages.length} messages · ${formatDate(chat.updatedAt)}</small>
      `;
      button.addEventListener("click", () => {
        store.setCurrentChat(chat.id);
        refresh();
        onSelect?.(chat.id);
      });
      listElement.appendChild(button);
    });
    renderedCount += chunk.length;
  }

  function refresh(query = "") {
    const normalized = query.trim().toLowerCase();
    filtered = store
      .getChats()
      .filter((chat) => chat.title.toLowerCase().includes(normalized) || chat.messages.some((item) => item.content.toLowerCase().includes(normalized)));

    if (!filtered.length) {
      listElement.innerHTML = "<div class=\"history-item\"><small>No chats found.</small></div>";
      renderedCount = 0;
      return;
    }
    renderNextPage(true);
  }

  listElement.addEventListener("scroll", () => {
    if (listElement.scrollTop + listElement.clientHeight >= listElement.scrollHeight - 18) {
      if (renderedCount < filtered.length) {
        renderNextPage(false);
      }
    }
  });

  const searchHandler = debounce((value) => refresh(value), 260);
  searchInput?.addEventListener("input", (event) => searchHandler(event.target.value));

  refresh();

  return {
    refresh,
  };
}
