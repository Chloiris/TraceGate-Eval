import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { LanguageProvider } from "./i18n";
import "./styles/tokens.css";
import "./styles/site.css";

const root = document.getElementById("root");
if (!root) throw new Error("TraceGate site root is missing");

createRoot(root).render(
  <StrictMode>
    <LanguageProvider>
      <App />
    </LanguageProvider>
  </StrictMode>,
);
