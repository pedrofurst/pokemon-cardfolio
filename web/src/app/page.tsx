"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { CollectionResponse } from "@/lib/types";

export default function Home() {
  const [data, setData] = useState<CollectionResponse | null>(null);

  useEffect(() => {
    async function load() {
      setData(await api.listHoldings());
    }
    load();
  }, []);

  async function refresh() {
    await api.refreshPrices();
    setData(await api.listHoldings());
  }

  return (
    <main style={{ padding: 24 }}>
      <h1>My collection</h1>
      <nav>
        <Link href="/search">+ Add cards</Link>{" "}
        <Link href="/watchlist" style={{ marginLeft: 12 }}>Watchlist</Link>{" "}
        <Link href="/opportunities" style={{ marginLeft: 12 }}>Opportunities</Link>
      </nav>
      <button onClick={refresh} style={{ marginLeft: 12 }}>Refresh prices</button>
      {data && (
        <>
          <p>
            Cost ${data.summary.total_cost.toFixed(2)} · Value $
            {data.summary.total_value.toFixed(2)} · P&amp;L ${data.summary.pnl.toFixed(2)} (
            {data.summary.pnl_pct.toFixed(1)}%)
          </p>
          <table>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.holding.id}>
                  <td>
                    <Link href={`/card/${item.holding.card_id}`}>
                      {item.card?.name ?? item.holding.card_id}
                    </Link>
                  </td>
                  <td>{item.holding.condition}</td>
                  <td>${item.holding.acquisition_cost.toFixed(2)}</td>
                  <td>${item.current_price?.toFixed(2) ?? "?"}</td>
                  <td>${item.pnl.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </main>
  );
}
