(() => {
  const key = "tracegate-site-theme";
  let theme = "light";
  try {
    const stored = window.localStorage.getItem(key);
    if (stored === "light" || stored === "dark") theme = stored;
  } catch {
    // Private browsing and hardened storage policies must not block rendering.
  }
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", theme === "dark" ? "#07100f" : "#f2f7f4");
})();
