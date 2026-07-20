"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import { HoldingView, PricePoint } from "@/lib/types";
import { useMoney } from "@/components/Currency";
import { ConnectionError, PnLPill } from "@/components/ui";
import { TrendChart } from "@/components/TrendChart";
import { Reveal } from "@/components/Reveal";
import { useToast } from "@/components/Toast";

const HoloCard3D = dynamic(
  () => import("@/components/HoloCard3D").then((m) => m.HoloCard3D),
  { ssr: false, loading: () => <div className="panel panel--pad">Loading 3D…</div> }
);

export default function CardDetail() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { toast } = useToast();
  const { fmt } = useMoney();
  const [view, setView] = useState<HoldingView | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [history, setHistory] = useState<PricePoint[]>([]);
  const [loadError, setLoadError] = useState(false);
  const [selling, setSelling] = useState(false);
  const [saleQuantity, setSaleQuantity] = useState("1");
  const [salePrice, setSalePrice] = useState("");
  const [saleFee, setSaleFee] = useState("0");
  const [saleError, setSaleError] = useState<string | null>(null);
  const [submittingSale, setSubmittingSale] = useState(false);
  const [viewing3D, setViewing3D] = useState(false);
  const [confirmingArchive, setConfirmingArchive] = useState(false);
  const [archiving, setArchiving] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const [data, cardHistory] = await Promise.all([
          api.listHoldings(),
          api.getCardHistory(params.id),
        ]);
        if (!active) return;
        setView(data.items.find((i) => i.holding.card_id === params.id) ?? null);
        setHistory(cardHistory);
        setLoaded(true);
      } catch {
        if (active) setLoadError(true);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [params.id]);

  const backLink = (
    <Link href="/" className="back-link">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M15 18l-6-6 6-6" />
      </svg>
      Back to collection
    </Link>
  );

  if (loadError) {
    return (
      <div className="container">
        {backLink}
        <ConnectionError onRetry={() => window.location.reload()} />
      </div>
    );
  }

  if (!loaded) {
    return <div className="container">{backLink}<p style={{ color: "var(--muted)" }}>Loading…</p></div>;
  }

  if (!view) {
    return (
      <div className="container">
        {backLink}
        <div className="empty empty--panel">
          <div className="empty__title">Not in your collection</div>
          <p style={{ margin: 0 }}>
            This card ({params.id}) isn&apos;t among your holdings. You can still run a grading
            estimate for it.
          </p>
          <Link href={`/grading?card_id=${params.id}`} className="btn btn--primary" style={{ marginTop: 6 }}>
            Estimate grading
          </Link>
        </div>
      </div>
    );
  }

  const gain = view.pnl > 0;

  function openSellModal() {
    setSaleQuantity("1");
    setSalePrice(view!.current_price !== null ? String(view!.current_price) : "");
    setSaleFee("0");
    setSaleError(null);
    setSelling(true);
  }

  async function submitSale() {
    const holding = view!.holding;
    const quantity = Number(saleQuantity);
    const price = Number(salePrice);
    const fee = Number(saleFee);

    if (!Number.isInteger(quantity) || quantity < 1 || quantity > holding.quantity) {
      setSaleError(`Quantity must be between 1 and ${holding.quantity}.`);
      toast("Couldn't log the sale", "error");
      return;
    }
    if (Number.isNaN(price) || price < 0) {
      setSaleError("Enter a valid sale price.");
      toast("Couldn't log the sale", "error");
      return;
    }
    if (Number.isNaN(fee) || fee < 0) {
      setSaleError("Enter a valid fee.");
      toast("Couldn't log the sale", "error");
      return;
    }

    setSaleError(null);
    setSubmittingSale(true);
    try {
      await api.sellHolding(holding.id, { quantity, sale_price: price, fee });
      toast("Sale logged");
      router.push("/sales");
    } catch {
      setSaleError("Couldn't log the sale. Check the backend is running and try again.");
      toast("Couldn't log the sale", "error");
    } finally {
      setSubmittingSale(false);
    }
  }

  async function archive() {
    const holding = view!.holding;
    setArchiving(true);
    try {
      await api.archiveHolding(holding.id);
      toast("Card archived — its price history is kept.");
      router.push("/");
    } catch {
      toast("Couldn't archive that card.", "error");
    } finally {
      setArchiving(false);
      setConfirmingArchive(false);
    }
  }

  return (
    <div className="container">
      {backLink}
      <div className="grid-2">
        <Reveal index={0}>
          <div className={`tile${gain ? " tile--gain" : ""}`} style={{ maxWidth: 340 }}>
            <div className="tile__art">
              {view.card?.image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={view.card.image_url} alt={view.card?.name ?? "Card"} />
              ) : (
                <span className="tile__art--empty">No image</span>
              )}
              <span className="tile__sheen" aria-hidden />
            </div>
          </div>
        </Reveal>

        <div className="stack">
          <div>
            <div className="eyebrow">{view.card?.set_name || "Card"}</div>
            <h1 className="title">{view.card?.name ?? params.id}</h1>
            <div className="row wrap" style={{ marginTop: 10 }}>
              <span className="badge">{view.holding.condition}</span>
              {view.holding.variant !== "normal" && (
                <span className="badge badge--brand">{view.holding.variant}</span>
              )}
              {view.holding.is_graded && <span className="badge badge--gold">graded</span>}
              {view.holding.quantity > 1 && <span className="badge">×{view.holding.quantity}</span>}
            </div>
          </div>

          <Reveal index={1}>
            <div className="panel panel--pad">
              <TrendChart
                points={history.map((point) => ({ t: point.fetched_at, v: point.market_price }))}
                accent="var(--brand)"
                height={96}
                ariaLabel="Price history"
              />
            </div>
          </Reveal>

          <Reveal index={2}>
            <div className="panel panel--pad">
              <div className="ledger">
                <div className="ledger__row">
                  <span className="ledger__k">Current price</span>
                  <span className="ledger__v">
                    {view.current_price === null ? "Unpriced" : fmt(view.current_price)}
                  </span>
                </div>
                <div className="ledger__row">
                  <span className="ledger__k">Cost basis</span>
                  <span className="ledger__v">{fmt(view.holding.acquisition_cost)}</span>
                </div>
                <div className="ledger__row is-total">
                  <span className="ledger__k" style={{ color: "var(--ink)", fontWeight: 600 }}>
                    Unrealized P&amp;L
                  </span>
                  <PnLPill value={view.pnl} />
                </div>
              </div>
            </div>
          </Reveal>

          <div className="row wrap">
            <Link href={`/grading?card_id=${view.holding.card_id}`} className="btn btn--primary">
              Should I grade it?
            </Link>
            <Link href="/search" className="btn">
              Add another
            </Link>
            <button className="btn" onClick={openSellModal}>
              Log a sale
            </button>
            {view.card?.image_url && (
              <button className="btn" onClick={() => setViewing3D(true)}>
                View in 3D ✨
              </button>
            )}
            <button className="btn" onClick={() => setConfirmingArchive(true)}>
              Archive
            </button>
          </div>
        </div>
      </div>

      {viewing3D && view.card?.image_url && (
        <div className="modal-scrim" onClick={() => setViewing3D(false)}>
          <div className="modal modal--wide" onClick={(e) => e.stopPropagation()}>
            <HoloCard3D imageUrl={view.card.image_url} onClose={() => setViewing3D(false)} />
          </div>
        </div>
      )}

      {selling && (
        <div className="modal-scrim" onClick={() => setSelling(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal__head">
              <div>
                <div className="eyebrow">Log a sale</div>
                <div className="modal__title">{view.card?.name ?? params.id}</div>
                <div className="tile__set">{view.card?.set_name}</div>
              </div>
              {view.card?.image_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img className="modal__thumb" src={view.card.image_url} alt={view.card.name} />
              )}
            </div>
            <label className="field">
              <span className="label">Quantity sold</span>
              <input
                className="input num"
                inputMode="numeric"
                value={saleQuantity}
                onChange={(e) => setSaleQuantity(e.target.value)}
                autoFocus
              />
              <span className="hint">You have {view.holding.quantity} on hand.</span>
            </label>
            <label className="field">
              <span className="label">Sale price (USD, per card)</span>
              <input
                className="input num"
                inputMode="decimal"
                value={salePrice}
                onChange={(e) => setSalePrice(e.target.value)}
                placeholder="0.00"
              />
            </label>
            <label className="field">
              <span className="label">Fee (USD)</span>
              <input
                className="input num"
                inputMode="decimal"
                value={saleFee}
                onChange={(e) => setSaleFee(e.target.value)}
                placeholder="0.00"
              />
            </label>
            {saleError && <p className="alert">{saleError}</p>}
            <div className="row" style={{ justifyContent: "flex-end", marginTop: 4 }}>
              <button className="btn btn--ghost" onClick={() => setSelling(false)}>
                Cancel
              </button>
              <button className="btn btn--primary" onClick={submitSale} disabled={submittingSale}>
                {submittingSale ? "Logging…" : "Log sale"}
              </button>
            </div>
          </div>
        </div>
      )}

      {confirmingArchive && (
        <div className="modal-scrim" onClick={() => setConfirmingArchive(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal__head">
              <div>
                <div className="eyebrow">Archive card</div>
                <div className="modal__title">{view.card?.name ?? params.id}</div>
              </div>
            </div>
            <p style={{ color: "var(--muted)" }}>
              It leaves your collection and stops counting toward your totals. Its price
              history is kept, and you can restore it from the collection page.
            </p>
            <div className="row" style={{ justifyContent: "flex-end", marginTop: 4 }}>
              <button className="btn btn--ghost" onClick={() => setConfirmingArchive(false)}>
                Cancel
              </button>
              <button className="btn btn--primary" onClick={archive} disabled={archiving}>
                {archiving ? "Archiving…" : "Archive"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
