"use client";

import { useCallback, useEffect, useRef } from "react";
import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";

interface TiltCardProps {
  children: ReactNode;
  className?: string;
}

const MAX_TILT_DEGREES = 6;

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function TiltCard({ children, className }: TiltCardProps) {
  const elementRef = useRef<HTMLDivElement | null>(null);
  const frameRef = useRef<number | null>(null);

  const applyTilt = useCallback((clientX: number, clientY: number) => {
    const element = elementRef.current;
    if (!element) {
      return;
    }

    const rect = element.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) {
      return;
    }

    const offsetX = (clientX - rect.left) / rect.width;
    const offsetY = (clientY - rect.top) / rect.height;
    const rotateY = (offsetX - 0.5) * 2 * MAX_TILT_DEGREES;
    const rotateX = (0.5 - offsetY) * 2 * MAX_TILT_DEGREES;

    element.style.setProperty("--rx", `${rotateX}deg`);
    element.style.setProperty("--ry", `${rotateY}deg`);
    element.style.setProperty("--gx", `${offsetX * 100}%`);
    element.style.setProperty("--gy", `${offsetY * 100}%`);
  }, []);

  const resetTilt = useCallback(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }

    element.style.setProperty("--rx", "0deg");
    element.style.setProperty("--ry", "0deg");
  }, []);

  const cancelPendingFrame = useCallback(() => {
    if (frameRef.current !== null) {
      cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
    }
  }, []);

  const handlePointerMove = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (prefersReducedMotion()) {
        return;
      }

      const { clientX, clientY } = event;
      cancelPendingFrame();
      frameRef.current = requestAnimationFrame(() => {
        frameRef.current = null;
        applyTilt(clientX, clientY);
      });
    },
    [applyTilt, cancelPendingFrame]
  );

  const handlePointerLeave = useCallback(() => {
    cancelPendingFrame();
    resetTilt();
  }, [cancelPendingFrame, resetTilt]);

  useEffect(() => {
    return () => {
      cancelPendingFrame();
    };
  }, [cancelPendingFrame]);

  const classNames = className ? `tilt ${className}` : "tilt";

  return (
    <div
      ref={elementRef}
      className={classNames}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
    >
      {children}
    </div>
  );
}
