import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";

import { galleryItems } from "../data/gallery";
import { copy, useLanguage } from "../i18n";
import { ProductPicture, Reveal, SectionHeader } from "./Primitives";

export function ProductGallery() {
  const { language } = useLanguage();
  const text = copy[language].gallery;
  const [selected, setSelected] = useState<number | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const reduced = useReducedMotion();

  const close = () => setSelected(null);
  const previous = () => setSelected((value) => value === null ? null : (value - 1 + galleryItems.length) % galleryItems.length);
  const next = () => setSelected((value) => value === null ? null : (value + 1) % galleryItems.length);

  useEffect(() => {
    if (selected === null) return;
    document.body.classList.add("lightbox-open");
    closeRef.current?.focus();
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
      if (event.key === "ArrowLeft") previous();
      if (event.key === "ArrowRight") next();
    };
    window.addEventListener("keydown", handleKey);
    return () => {
      window.removeEventListener("keydown", handleKey);
      document.body.classList.remove("lightbox-open");
    };
  }, [selected]);

  const current = selected === null ? null : galleryItems[selected];

  return (
    <section id="evidence" className="gallery section" aria-labelledby="gallery-title">
      <div className="shell">
        <SectionHeader eyebrow={text.eyebrow} title={text.title} body={text.body} />
        <div className="gallery__grid">
          {galleryItems.map((item, index) => (
            <Reveal className={`gallery-card gallery-card--${index % 5}`} delay={(index % 4) * 0.035} key={item.id}>
              <button type="button" onClick={() => setSelected(index)} aria-label={`${text.open}: ${item.title[language]}`}>
                <span className="gallery-card__image">
                  <ProductPicture id={item.id} alt={`${item.title[language]} — ${item.scopeLabel[language]}`} sizes="(max-width: 760px) 92vw, (max-width: 1200px) 45vw, 390px" />
                </span>
                <span className="gallery-card__copy">
                  <small>{item.scopeLabel[language]}</small>
                  <strong>{item.title[language]}</strong>
                  <span>{item.description[language]}</span>
                </span>
                <span className="gallery-card__open" aria-hidden="true">↗</span>
              </button>
            </Reveal>
          ))}
        </div>
      </div>
      <AnimatePresence>
        {current && (
          <motion.div
            className="lightbox"
            role="dialog"
            aria-modal="true"
            aria-labelledby="lightbox-title"
            initial={reduced ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onPointerDown={(event) => { if (event.currentTarget === event.target) close(); }}
          >
            <motion.div className="lightbox__panel" initial={reduced ? false : { opacity: 0, y: 18, scale: 0.985 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 12, scale: 0.99 }}>
              <div className="lightbox__top">
                <div><small>{current.scopeLabel[language]}</small><h3 id="lightbox-title">{current.title[language]}</h3></div>
                <button ref={closeRef} type="button" onClick={close} aria-label={text.close}>×</button>
              </div>
              <div className="lightbox__image"><ProductPicture id={current.id} alt={`${current.title[language]} — ${current.scopeLabel[language]}`} sizes="92vw" /></div>
              <div className="lightbox__footer">
                <p>{current.description[language]}<small>Source: {current.source}</small></p>
                <div><button type="button" onClick={previous} aria-label={text.previous}>←</button><span>{String((selected ?? 0) + 1).padStart(2, "0")} / {galleryItems.length}</span><button type="button" onClick={next} aria-label={text.next}>→</button></div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
