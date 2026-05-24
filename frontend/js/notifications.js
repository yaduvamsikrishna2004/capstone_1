import { uid } from "./utils.js";

export function createNotifier(stackElement) {
  function show(message, type = "info", title = "Notice", duration = 3000) {
    if (!stackElement) return;
    const id = uid("toast");
    const toast = document.createElement("article");
    toast.className = `toast ${type}`;
    toast.dataset.toastId = id;
    toast.innerHTML = `<strong>${title}</strong><small>${message}</small>`;
    stackElement.appendChild(toast);

    setTimeout(() => {
      const existing = stackElement.querySelector(`[data-toast-id="${id}"]`);
      if (existing) {
        existing.style.opacity = "0";
        existing.style.transform = "translateX(8px)";
        setTimeout(() => existing.remove(), 220);
      }
    }, duration);
  }

  return {
    success(message, title = "Success") {
      show(message, "success", title);
    },
    error(message, title = "Error") {
      show(message, "error", title, 4500);
    },
    info(message, title = "Info") {
      show(message, "info", title);
    },
  };
}
