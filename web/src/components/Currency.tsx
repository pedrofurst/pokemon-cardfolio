"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api } from "@/lib/api";

export type Currency = "USD" | "BRL";

const STORAGE_KEY = "cardfolio.currency";

interface CurrencyContextValue {
  currency: Currency;
  setCurrency: (currency: Currency) => void;
  rate: number | null;
}

const CurrencyContext = createContext<CurrencyContextValue | null>(null);

const usdFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const brlFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function readStoredCurrency(): Currency {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored === "BRL" ? "BRL" : "USD";
}

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [currency, setCurrencyState] = useState<Currency>("USD");
  const [rate, setRate] = useState<number | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function hydrate() {
      const [storedCurrency, fx] = await Promise.all([
        Promise.resolve(readStoredCurrency()),
        api.getFx().catch(() => null),
      ]);
      if (!isMounted) {
        return;
      }
      setCurrencyState(storedCurrency);
      if (fx) {
        setRate(fx.usd_brl);
      }
    }
    void hydrate();

    return () => {
      isMounted = false;
    };
  }, []);

  function setCurrency(nextCurrency: Currency) {
    setCurrencyState(nextCurrency);
    window.localStorage.setItem(STORAGE_KEY, nextCurrency);
  }

  const contextValue = useMemo(
    () => ({ currency, setCurrency, rate }),
    [currency, rate]
  );

  return (
    <CurrencyContext.Provider value={contextValue}>{children}</CurrencyContext.Provider>
  );
}

export function useCurrency(): CurrencyContextValue {
  const context = useContext(CurrencyContext);
  if (!context) {
    throw new Error("useCurrency must be used within a CurrencyProvider");
  }
  return context;
}

export function useMoney(): {
  fmt: (valueUsd: number | null | undefined) => string;
  fmtSigned: (valueUsd: number | null | undefined) => string;
} {
  const { currency, rate } = useCurrency();

  function fmt(valueUsd: number | null | undefined): string {
    if (valueUsd === null || valueUsd === undefined || Number.isNaN(valueUsd)) {
      return "—";
    }
    if (currency === "BRL" && rate) {
      return brlFormatter.format(valueUsd * rate);
    }
    return usdFormatter.format(valueUsd);
  }

  function fmtSigned(valueUsd: number | null | undefined): string {
    if (valueUsd === null || valueUsd === undefined || Number.isNaN(valueUsd)) {
      return "—";
    }
    const sign = valueUsd > 0 ? "+" : valueUsd < 0 ? "−" : "";
    const absoluteValueUsd = Math.abs(valueUsd);
    if (currency === "BRL" && rate) {
      return `${sign}${brlFormatter.format(absoluteValueUsd * rate)}`;
    }
    return `${sign}${usdFormatter.format(absoluteValueUsd)}`;
  }

  return { fmt, fmtSigned };
}
