const THEME_KEY = "docassist_theme";

export function initTheme(toggleButton) {
  const preferred = localStorage.getItem(THEME_KEY);
  const initial = preferred === "light" || preferred === "dark" ? preferred : "dark";
  applyTheme(initial);

  toggleButton?.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(next);
    localStorage.setItem(THEME_KEY, next);
  });
}

export function applyTheme(value) {
  document.documentElement.dataset.theme = value;
}
