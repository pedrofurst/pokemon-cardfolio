"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { OpportunitiesResponse, Signal } from "@/lib/types";

function SignalList({ signals, emptyMessage }: { signals: Signal[]; emptyMessage: string }) {
  if (signals.length === 0) {
    return <p>{emptyMessage}</p>;
  }
  return (
    <ul>
      {signals.map((signal, index) => (
        <li key={`${signal.card_id}-${index}`}>
          <Link href={`/card/${signal.card_id}`}>{signal.card_name}</Link> — {signal.detail}
          {" "}(current ${signal.current_price?.toFixed(2) ?? "?"} · reference $
          {signal.reference_price?.toFixed(2) ?? "?"})
        </li>
      ))}
    </ul>
  );
}

export default function OpportunitiesPage() {
  const [data, setData] = useState<OpportunitiesResponse | null>(null);

  useEffect(() => {
    async function load() {
      setData(await api.listOpportunities());
    }
    load();
  }, []);

  return (
    <main style={{ padding: 24 }}>
      <h1>Opportunities</h1>
      <Link href="/">Back to collection</Link>
      {data && (
        <>
          <section>
            <h2>Movers</h2>
            <SignalList
              signals={data.movers}
              emptyMessage="Nothing yet — add cards and refresh prices"
            />
          </section>
          <section>
            <h2>Deals</h2>
            <SignalList
              signals={data.deals}
              emptyMessage="Nothing yet — add cards and refresh prices"
            />
          </section>
          <section>
            <h2>Target hits</h2>
            <SignalList
              signals={data.target_hits}
              emptyMessage="Nothing yet — add cards and refresh prices"
            />
          </section>
        </>
      )}
    </main>
  );
}
