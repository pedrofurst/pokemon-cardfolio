"use client";

import { useEffect, useRef, useState } from "react";

interface PackRevealProps {
  imageUrl: string;
  name: string;
  onDone: () => void;
}

const AUTO_DONE_MS = 2200;
const FLIP_DELAY_MS = 120;

export function PackReveal({ imageUrl, name, onDone }: PackRevealProps) {
  const [flipped, setFlipped] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const onDoneRef = useRef(onDone);

  useEffect(() => {
    onDoneRef.current = onDone;
  }, [onDone]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      const prefersReducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
      ).matches;
      if (prefersReducedMotion) {
        setReducedMotion(true);
        setFlipped(true);
      }
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    if (reducedMotion) {
      return;
    }
    const flipTimer = setTimeout(() => setFlipped(true), FLIP_DELAY_MS);
    return () => clearTimeout(flipTimer);
  }, [reducedMotion]);

  useEffect(() => {
    const doneTimer = setTimeout(() => onDoneRef.current(), AUTO_DONE_MS);
    return () => clearTimeout(doneTimer);
  }, []);

  return (
    <div className="modal-scrim pack-reveal" onClick={onDone} role="button" aria-label="Skip reveal">
      <div className="pack-reveal__stage">
        <span className={`pack-reveal__glow${flipped ? " is-lit" : ""}`} aria-hidden />
        <div className="pack-reveal__card">
          <div
            className={`pack-reveal__inner${flipped ? " is-flipped" : ""}${
              reducedMotion ? " pack-reveal__inner--static" : ""
            }`}
          >
            <div className="pack-reveal__face pack-reveal__face--back">
              <span className="pack-reveal__mark" aria-hidden>
                ?
              </span>
            </div>
            <div className="pack-reveal__face pack-reveal__face--front">
              {imageUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={imageUrl} alt={name} />
              ) : (
                <span className="tile__art--empty">No image</span>
              )}
              <span className={`pack-reveal__sheen${flipped ? " is-sweeping" : ""}`} aria-hidden />
            </div>
          </div>
        </div>
        <div className="pack-reveal__caption">
          <span className="eyebrow">Pulled</span>
          <h2 className="pack-reveal__name">{name}</h2>
        </div>
        <button
          className="btn btn--primary"
          onClick={(event) => {
            event.stopPropagation();
            onDone();
          }}
        >
          Done
        </button>
      </div>
    </div>
  );
}
