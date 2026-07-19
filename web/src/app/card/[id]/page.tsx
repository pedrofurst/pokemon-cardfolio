"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { HoldingView } from "@/lib/types";

export default function CardDetail() {
  const params = useParams<{ id: string }>();
  const [view, setView] = useState<HoldingView | null>(null);

  useEffect(() => {
    api.listHoldings().then((data) => {
      setView(data.items.find((i) => i.holding.card_id === params.id) ?? null);
    });
  }, [params.id]);

  if (!view) return <main style={{ padding: 24 }}>Loading…</main>;
  return (
    <main style={{ padding: 24 }}>
      <h1>{view.card?.name ?? params.id}</h1>
      <img src={view.card?.image_url} alt={view.card?.name ?? ""} width={200} />
      <p>Current price: ${view.current_price?.toFixed(2) ?? "?"}</p>
      <p>P&amp;L: ${view.pnl.toFixed(2)}</p>
      <p>
        <Link href={`/grading?card_id=${params.id}`}>Grade?</Link>
      </p>
    </main>
  );
}
