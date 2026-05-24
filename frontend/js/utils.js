export function qs(selector, root = document) {
  return root.querySelector(selector);
}

export function qsa(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

export function debounce(fn, wait = 220) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

export function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function uid(prefix = "id") {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2, 10)}`;
}

export function formatBytes(value = 0) {
  if (value === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  const sized = value / (1024 ** index);
  return `${sized.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export function formatDate(value = Date.now()) {
  const date = new Date(value);
  return date.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatTime(value = Date.now()) {
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function truncate(text = "", length = 70) {
  if (text.length <= length) return text;
  return `${text.slice(0, length).trim()}...`;
}

export function safeJsonParse(value, fallback = null) {
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

export function saveStorage(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

export function loadStorage(key, fallback = null) {
  const raw = localStorage.getItem(key);
  if (!raw) return fallback;
  return safeJsonParse(raw, fallback);
}

export function escapeHtml(input = "") {
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

const KEYWORDS = /\b(const|let|var|function|return|if|else|for|while|class|import|export|await|async|try|catch|finally|def|from|as|True|False|null|None|SELECT|FROM|WHERE|JOIN|GROUP|ORDER|BY|INSERT|UPDATE|DELETE)\b/g;
const NUMBERS = /\b(\d+(\.\d+)?)\b/g;
const STRINGS = /("[^"]*"|'[^']*')/g;

export function highlightCode(input = "") {
  return input
    .replace(STRINGS, "<span class=\"token string\">$1</span>")
    .replace(KEYWORDS, "<span class=\"token keyword\">$1</span>")
    .replace(NUMBERS, "<span class=\"token number\">$1</span>");
}

function renderInlineMarkdown(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, "<a href=\"$2\" target=\"_blank\" rel=\"noreferrer\">$1</a>");
}

function closeListIfNeeded(buffer) {
  if (!buffer.listType) return "";
  const closeTag = buffer.listType === "ol" ? "</ol>" : "</ul>";
  buffer.listType = null;
  return closeTag;
}

export function markdownToHtml(markdown = "") {
  const codeBlocks = [];
  const withTokens = markdown.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang = "", code = "") => {
    const escaped = escapeHtml(code.trim());
    const highlighted = highlightCode(escaped);
    const block = `<pre><code data-lang="${lang}">${highlighted}</code></pre>`;
    const token = `__CODE_BLOCK_${codeBlocks.length}__`;
    codeBlocks.push(block);
    return token;
  });

  const escaped = escapeHtml(withTokens);
  const lines = escaped.replace(/\r\n/g, "\n").split("\n");
  const output = [];
  const listBuffer = { listType: null };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const trimmed = line.trim();
    if (!trimmed) {
      output.push(closeListIfNeeded(listBuffer));
      continue;
    }

    const tableDivider = /^\|?[\s\-:|]+\|?$/.test(trimmed);
    const nextLine = lines[index + 1]?.trim() ?? "";
    const isTableRow = trimmed.includes("|") && nextLine.includes("|") && /^\|?[\s\-:|]+\|?$/.test(nextLine);
    if (isTableRow) {
      const headers = trimmed.split("|").map((cell) => cell.trim()).filter(Boolean);
      const rows = [];
      index += 2;
      while (index < lines.length && lines[index].includes("|")) {
        const row = lines[index].split("|").map((cell) => cell.trim()).filter(Boolean);
        if (!row.length) break;
        rows.push(row);
        index += 1;
      }
      index -= 1;
      output.push(closeListIfNeeded(listBuffer));
      const headerHtml = headers.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join("");
      const rowHtml = rows.map((row) => `<tr>${row.map((cell) => `<td>${renderInlineMarkdown(cell)}</td>`).join("")}</tr>`).join("");
      output.push(`<table><thead><tr>${headerHtml}</tr></thead><tbody>${rowHtml}</tbody></table>`);
      continue;
    }
    if (tableDivider) continue;

    const headingMatch = /^(#{1,6})\s+(.+)$/.exec(trimmed);
    if (headingMatch) {
      output.push(closeListIfNeeded(listBuffer));
      const level = headingMatch[1].length;
      output.push(`<h${level}>${renderInlineMarkdown(headingMatch[2])}</h${level}>`);
      continue;
    }

    const orderedMatch = /^(\d+)\.\s+(.+)$/.exec(trimmed);
    if (orderedMatch) {
      if (listBuffer.listType !== "ol") {
        output.push(closeListIfNeeded(listBuffer));
        output.push("<ol>");
        listBuffer.listType = "ol";
      }
      output.push(`<li>${renderInlineMarkdown(orderedMatch[2])}</li>`);
      continue;
    }

    const unorderedMatch = /^[-*]\s+(.+)$/.exec(trimmed);
    if (unorderedMatch) {
      if (listBuffer.listType !== "ul") {
        output.push(closeListIfNeeded(listBuffer));
        output.push("<ul>");
        listBuffer.listType = "ul";
      }
      output.push(`<li>${renderInlineMarkdown(unorderedMatch[1])}</li>`);
      continue;
    }

    output.push(closeListIfNeeded(listBuffer));
    output.push(`<p>${renderInlineMarkdown(trimmed)}</p>`);
  }

  output.push(closeListIfNeeded(listBuffer));
  let html = output.join("");
  codeBlocks.forEach((block, index) => {
    html = html.replace(`__CODE_BLOCK_${index}__`, block);
  });
  return html;
}

export function autosizeTextarea(element) {
  if (!element) return;
  element.style.height = "auto";
  element.style.height = `${Math.min(element.scrollHeight, 220)}px`;
}

export function smoothScrollToBottom(element) {
  if (!element) return;
  element.scrollTo({ top: element.scrollHeight, behavior: "smooth" });
}
