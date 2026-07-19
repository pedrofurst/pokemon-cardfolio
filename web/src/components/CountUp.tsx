"use client";

import { useEffect, useRef, useState } from "react";

interface CountUpProps {
  value: number;
  format: (value: number) => string;
  className?: string;
}

const ANIMATION_DURATION_MS = 500;

function easeOut(progress: number): number {
  return 1 - Math.pow(1 - progress, 3);
}

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function CountUp({ value, format, className }: CountUpProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const previousValueRef = useRef(0);
  const hasMountedRef = useRef(false);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    if (!Number.isFinite(value)) {
      return;
    }

    if (prefersReducedMotion()) {
      previousValueRef.current = value;
      hasMountedRef.current = true;
      const frame = requestAnimationFrame(() => setDisplayValue(value));
      return () => cancelAnimationFrame(frame);
    }

    const startValue = hasMountedRef.current ? previousValueRef.current : 0;
    hasMountedRef.current = true;
    const startTime = performance.now();

    function tick(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / ANIMATION_DURATION_MS, 1);
      const eased = easeOut(progress);
      const current = startValue + (value - startValue) * eased;
      setDisplayValue(current);

      if (progress < 1) {
        animationFrameRef.current = requestAnimationFrame(tick);
      } else {
        previousValueRef.current = value;
        animationFrameRef.current = null;
      }
    }

    animationFrameRef.current = requestAnimationFrame(tick);

    return () => {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [value]);

  if (!Number.isFinite(value)) {
    return <span className={className}>{format(value)}</span>;
  }

  return <span className={className}>{format(displayValue)}</span>;
}
