"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { SalesResponse } from "@/lib/types";
import { money } from "@/lib/format";
import { ConnectionError, EmptyState, PageHead, PnLPill } from "@/components/ui";
import { Reveal } from "@/components/Reveal";

export default function SalesPage() {
  const [data, setData] = useState<SalesResponse | null>(null);
  const [loadError, setLoadError] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await api.getSales());
      setLoadError(false);
    } catch {
      setLoadError(true);
    }
  }, []);

  useEffect(() => {
    async function run() {
      await load();
    }
    run();
  }, [load]);

  const items = data?.items ?? [];

  return (
    <div className="container">
      <PageHead
        eyebrow="Realized"
        title="Sales"
        subtitle="Every card you've sold, with the P&L it locked in."
      />

      {loadError && !data ? (
        <ConnectionError onRetry={load} />
      ) : data && items.length === 0 ? (
        <EmptyState
          title="No sales yet"
          action={
            <Link href="/" className="btn btn--primary">
              Go to your collection
            </Link>
          }
        >
          Log a sale from a card&apos;s detail page and it will show up here with the realized P&amp;L.
        </EmptyState>
      ) : (
        data && (
          <>
            <Reveal index={0}>
              <div className="panel panel--pad" style={{ marginBottom: 20 }}>
                <div className="ledger">
                  <div className="ledger__row">
                    <span className="ledger__k">Proceeds</span>
                    <span className="ledger__v">{money(data.summary.total_proceeds)}</span>
                  </div>
                  <div className="ledger__row">
                    <span className="ledger__k">Cost basis</span>
                    <span className="ledger__v">{money(data.summary.total_cost)}</span>
                  </div>
                  <div className="ledger__row">
                    <span className="ledger__k">Sales logged</span>
                    <span className="ledger__v">{data.summary.sales_count}</span>
                  </div>
                  <div className="ledger__row is-total">
                    <span className="ledger__k" style={{ color: "var(--ink)", fontWeight: 600 }}>
                      Realized P&amp;L
                    </span>
                    <PnLPill value={data.summary.realized_pnl} />
                  </div>
                </div>
              </div>
            </Reveal>

            <Reveal index={1}>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Card</th>
                      <th className="num">Qty</th>
                      <th className="num">Sale price</th>
                      <th className="num">Proceeds</th>
                      <th className="num">Realized</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((entry) => {
                      const proceeds =
                        entry.sale.sale_price * entry.sale.quantity - entry.sale.fee;
                      const realized = proceeds - entry.sale.cost_basis * entry.sale.quantity;
                      return (
                        <tr key={entry.sale.id}>
                          <td>
                            <Link href={`/card/${entry.sale.card_id}`} className="cell-name">
                              {entry.card?.name ?? entry.sale.card_id}
                            </Link>
                          </td>
                          <td className="num" style={{ fontFamily: "var(--font-mono)" }}>
                            {entry.sale.quantity}
                          </td>
                          <td className="num" style={{ fontFamily: "var(--font-mono)" }}>
                            {money(entry.sale.sale_price)}
                          </td>
                          <td className="num" style={{ fontFamily: "var(--font-mono)" }}>
                            {money(proceeds)}
                          </td>
                          <td className="num">
                            <PnLPill value={realized} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Reveal>
          </>
        )
      )}
    </div>
  );
}
