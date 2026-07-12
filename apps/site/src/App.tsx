import { lazy, Suspense, useEffect, useState } from "react";

import { Hero } from "./components/Hero";
import { Navigation } from "./components/Navigation";
import { useLanguage } from "./i18n";

const BelowFold = lazy(() => import("./components/BelowFold"));

export default function App() {
  const { language } = useLanguage();
  const [belowFoldReady, setBelowFoldReady] = useState(false);

  useEffect(() => {
    const start = () => setBelowFoldReady(true);
    const idleWindow = window as unknown as {
      requestIdleCallback?: (callback: IdleRequestCallback, options?: IdleRequestOptions) => number;
      cancelIdleCallback?: (id: number) => void;
    };
    if (idleWindow.requestIdleCallback) {
      const idleId = idleWindow.requestIdleCallback(start, { timeout: 700 });
      return () => idleWindow.cancelIdleCallback?.(idleId);
    }
    const timeoutId = window.setTimeout(start, 0);
    return () => window.clearTimeout(timeoutId);
  }, []);

  return (
    <div className="site" data-language={language}>
      <Navigation />
      <main id="main">
        <Hero />
        {belowFoldReady && (
          <Suspense fallback={<div className="section-loading" aria-live="polite">Loading product experience…</div>}>
            <BelowFold />
          </Suspense>
        )}
      </main>
    </div>
  );
}
