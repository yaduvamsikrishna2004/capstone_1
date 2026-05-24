import { sendMessage } from "./api.js";
import { autosizeTextarea, escapeHtml, formatTime, markdownToHtml, smoothScrollToBottom, uid } from "./utils.js";

const RENDER_BATCH = 28;

export function createChatController({
  chatListEl,
  typingEl,
  loadOlderBtn,
  chatInputEl,
  sendBtn,
  charCountEl,
  welcomeEl,
  historyStore,
  notifier,
  getUserId,
}) {
  let visibleCount = RENDER_BATCH;
  let busy = false;

  function getCurrentMessages() {
    const chat = historyStore.getCurrentChat();
    return chat?.messages || [];
  }

  function toggleWelcome() {
    const hasMessages = getCurrentMessages().length > 0;
    welcomeEl.classList.toggle("hidden", hasMessages);
  }

  function formatAssistantSections(content = "") {
    const normalized = content.trim();
    if (!normalized) return normalized;

    let value = normalized;
    value = value.replace(/^\s*direct answer\s*:?\s*/i, "#### ?? Direct Answer\n");
    value = value.replace(/\n\s*key points?\s*:?\s*/i, "\n\n#### ? Key Insights\n");
    value = value.replace(/\n\s*confidence note\s*:?\s*/i, "\n\n#### ?? Confidence\n");
    value = value.replace(/\n\s*confidence\s*:?\s*/i, "\n\n#### ?? Confidence\n");
    return value;
  }

  function createMessageElement(message) {
    const article = document.createElement("article");
    article.className = `chat-message ${message.role}`;
    article.dataset.messageId = message.id;

    const actionMarkup = message.role === "assistant"
      ? `
        <div class="msg-actions">
          <button class="msg-action" data-action="copy">?? Copy</button>
          <button class="msg-action" data-action="regen">?? Regenerate</button>
          <button class="msg-action" data-action="up">??</button>
          <button class="msg-action" data-action="down">??</button>
        </div>`
      : "";

    const bodyMarkup = message.role === "assistant"
      ? markdownToHtml(formatAssistantSections(message.content))
      : `<p>${escapeHtml(message.content)}</p>`;

    article.innerHTML = `
      <div class="msg-meta">
        <span><span class="msg-role">${message.role === "assistant" ? "Assistant" : "You"}</span> - ${formatTime(message.createdAt)}</span>
      </div>
      <div class="msg-content">${bodyMarkup}</div>
      ${actionMarkup}
    `;

    if (message.role === "assistant") {
      article.querySelector("[data-action='copy']")?.addEventListener("click", async () => {
        await navigator.clipboard.writeText(message.content);
        notifier.success("Response copied to clipboard.");
      });

      article.querySelector("[data-action='regen']")?.addEventListener("click", () => {
        const all = getCurrentMessages();
        const index = all.findIndex((entry) => entry.id === message.id);
        if (index <= 0) return;
        const prevUser = [...all.slice(0, index)].reverse().find((entry) => entry.role === "user");
        if (!prevUser) return;
        runSend(prevUser.content, true);
      });

      article.querySelector("[data-action='up']")?.addEventListener("click", (event) => {
        event.currentTarget.classList.toggle("active");
      });

      article.querySelector("[data-action='down']")?.addEventListener("click", (event) => {
        event.currentTarget.classList.toggle("active");
      });
    }

    return article;
  }

  function renderMessages() {
    const messages = getCurrentMessages();
    chatListEl.innerHTML = "";
    const sliced = messages.slice(Math.max(messages.length - visibleCount, 0));
    sliced.forEach((message) => chatListEl.appendChild(createMessageElement(message)));

    loadOlderBtn.classList.toggle("hidden", messages.length <= visibleCount);
    toggleWelcome();
    smoothScrollToBottom(chatListEl);
  }

  function setTyping(isTyping) {
    typingEl.classList.toggle("hidden", !isTyping);
    if (isTyping) smoothScrollToBottom(chatListEl);
  }

  async function streamAssistantText(messageId, fullText) {
    let cursor = 0;
    while (cursor <= fullText.length) {
      const step = Math.max(1, Math.floor(Math.random() * 8));
      const content = fullText.slice(0, cursor);
      historyStore.replaceMessage(messageId, { content });
      renderMessages();
      cursor += step;
      // eslint-disable-next-line no-await-in-loop
      await new Promise((resolve) => setTimeout(resolve, 14));
    }
  }

  async function runSend(text, isRegenerate = false) {
    const prompt = text.trim();
    if (!prompt || busy) return;
    busy = true;
    sendBtn.disabled = true;
    setTyping(true);

    if (!isRegenerate) {
      historyStore.appendMessage({
        id: uid("msg"),
        role: "user",
        content: prompt,
        createdAt: Date.now(),
      });
      chatInputEl.value = "";
      autosizeTextarea(chatInputEl);
      updateCharCount();
      renderMessages();
    }

    const assistantMessageId = uid("msg");
    historyStore.appendMessage({
      id: assistantMessageId,
      role: "assistant",
      content: "",
      createdAt: Date.now(),
    });
    renderMessages();

    try {
      const response = await sendMessage(prompt, getUserId());
      await streamAssistantText(assistantMessageId, response.answer || "");
      historyStore.replaceMessage(assistantMessageId, {
        content: response.answer || "",
        sources: response.sources || [],
        retrievedCount: response.retrieved_count || 0,
      });
      renderMessages();
    } catch (error) {
      historyStore.replaceMessage(assistantMessageId, {
        content: `Request failed: ${error.message || "Unknown error."}`,
      });
      renderMessages();
      notifier.error(error.message || "Failed to fetch response.");
    } finally {
      setTyping(false);
      busy = false;
      sendBtn.disabled = !chatInputEl.value.trim();
    }
  }

  function updateCharCount() {
    const count = chatInputEl.value.length;
    charCountEl.textContent = `${count} / 8000`;
    sendBtn.disabled = !chatInputEl.value.trim() || busy;
    autosizeTextarea(chatInputEl);
  }

  sendBtn.addEventListener("click", () => runSend(chatInputEl.value));

  chatInputEl.addEventListener("input", updateCharCount);
  chatInputEl.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      runSend(chatInputEl.value);
    }
  });

  loadOlderBtn.addEventListener("click", () => {
    visibleCount += RENDER_BATCH;
    renderMessages();
  });

  updateCharCount();

  return {
    renderMessages,
    sendPrompt: (prompt) => runSend(prompt),
    resetVisible: () => {
      visibleCount = RENDER_BATCH;
    },
  };
}
