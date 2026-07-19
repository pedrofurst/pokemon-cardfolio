"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";

type ToastTone = "ok" | "error";

interface ToastRecord {
  id: number;
  message: string;
  tone: ToastTone;
}

interface ToastContextValue {
  toast: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const TOAST_DURATION_MS = 2500;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const nextIdRef = useRef(0);
  const timeoutsRef = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: number) => {
    const timeout = timeoutsRef.current.get(id);
    if (timeout) {
      clearTimeout(timeout);
      timeoutsRef.current.delete(id);
    }
    setToasts((currentToasts) => currentToasts.filter((toastRecord) => toastRecord.id !== id));
  }, []);

  const toast = useCallback(
    (message: string, tone: ToastTone = "ok") => {
      const id = nextIdRef.current;
      nextIdRef.current += 1;
      setToasts((currentToasts) => [...currentToasts, { id, message, tone }]);

      const timeout = setTimeout(() => {
        dismiss(id);
      }, TOAST_DURATION_MS);
      timeoutsRef.current.set(id, timeout);
    },
    [dismiss]
  );

  useEffect(() => {
    const timeouts = timeoutsRef.current;
    return () => {
      timeouts.forEach((timeout) => clearTimeout(timeout));
      timeouts.clear();
    };
  }, []);

  const contextValue = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <div className="toast-wrap" aria-live="polite">
        {toasts.map((toastRecord) => (
          <div
            key={toastRecord.id}
            className={`toast toast--${toastRecord.tone}`}
            role="status"
          >
            {toastRecord.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
