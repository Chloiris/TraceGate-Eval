import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { LanguageProvider } from "./i18n";
import { ThemeProvider } from "./theme";
import "./styles/tokens.css";
import "./styles/site.css";

const root = document.getElementById("root");
if (!root) throw new Error("TraceGate site root is missing");

createRoot(root).render(
  <StrictMode>
    <ThemeProvider>
      <LanguageProvider>
        <App />
      </LanguageProvider>
    </ThemeProvider>
  </StrictMode>,
);
