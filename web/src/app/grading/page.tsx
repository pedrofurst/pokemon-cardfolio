"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { GradingResult } from "@/lib/types";
import { money, pct } from "@/lib/format";
import { PageHead } from "@/components/ui";

function recoMeta(recommendation: string): { label: string; cls: string } {
  if (recommendation === "GRADE") return { label: "Grade it", cls: "reco--grade" };
  if (recommendation === "DONT_GRADE") return { label: "Don't grade", cls: "reco--dont" };
  return { label: "Need more data", cls: "reco--insufficient" };
}

function parseOptionalNumber(value: string): number | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : Number(trimmed);
}

function GradingForm() {
  const searchParams = useSearchParams();
  const [cardId, setCardId] = useState(searchParams.get("card_id") ?? "");
  const [rawPrice, setRawPrice] = useState("");
  const [psa10Price, setPsa10Price] = useState("");
  const [psa9Price, setPsa9Price] = useState("");
  const [gradingCost, setGradingCost] = useState("25");
  const [sellingFeesPct, setSellingFeesPct] = useState("13");
  const [probPsa10, setProbPsa10] = useState("0.5");
  const [result, setResult] = useState<GradingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function evaluate() {
    setError(null);
    setLoading(true);
    try {
      const payload = {
        card_id: cardId.trim() === "" ? null : cardId.trim(),
        raw_price: parseOptionalNumber(rawPrice),
        psa10_price: parseOptionalNumber(psa10Price),
        psa9_price: parseOptionalNumber(psa9Price),
        grading_cost: Number(gradingCost) || 0,
        selling_fees_pct: Number(sellingFeesPct) || 0,
        prob_psa10: Number(probPsa10) || 0,
      };
      setResult(await api.evaluateGrading(payload));
    } catch {
      setError("Couldn't evaluate. Check the values and that the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  const reco = result ? recoMeta(result.recommendation) : null;

  return (
    <div className="container">
      <PageHead
        eyebrow="Decision"
        title="Should I grade it?"
        subtitle="Weigh expected graded proceeds against selling raw — net of grading cost and selling fees."
      />

      <div className="grid-2">
        <form
          className="panel panel--pad"
          onSubmit={(e) => {
            e.preventDefault();
            evaluate();
          }}
        >
          <div className="form-grid">
            <label className="field col-span">
              <span className="label">Card ID (optional)</span>
              <input
                className="input"
                value={cardId}
                onChange={(e) => setCardId(e.target.value)}
                placeholder="base1-4"
              />
              <span className="hint">If set and raw price is blank, we use its latest stored price.</span>
            </label>
            <label className="field">
              <span className="label">Raw price</span>
              <input className="input num" inputMode="decimal" value={rawPrice} onChange={(e) => setRawPrice(e.target.value)} placeholder="auto" />
            </label>
            <label className="field">
              <span className="label">Grading cost</span>
              <input className="input num" inputMode="decimal" value={gradingCost} onChange={(e) => setGradingCost(e.target.value)} />
            </label>
            <label className="field">
              <span className="label">PSA 10 price</span>
              <input className="input num" inputMode="decimal" value={psa10Price} onChange={(e) => setPsa10Price(e.target.value)} placeholder="0.00" />
            </label>
            <label className="field">
              <span className="label">PSA 9 price</span>
              <input className="input num" inputMode="decimal" value={psa9Price} onChange={(e) => setPsa9Price(e.target.value)} placeholder="0.00" />
            </label>
            <label className="field">
              <span className="label">Selling fees (%)</span>
              <input className="input num" inputMode="decimal" value={sellingFeesPct} onChange={(e) => setSellingFeesPct(e.target.value)} />
            </label>
            <label className="field">
              <span className="label">P(PSA 10)</span>
              <input className="input num" inputMode="decimal" value={probPsa10} onChange={(e) => setProbPsa10(e.target.value)} />
            </label>
            <span className="hint col-span">
              Grade probability is only applied when you enter both a PSA 10 and a PSA 9 price.
            </span>
          </div>
          {error && <p className="alert" style={{ marginTop: 14 }}>{error}</p>}
          <button className="btn btn--primary" type="submit" style={{ marginTop: 16, width: "100%", justifyContent: "center" }} disabled={loading}>
            {loading ? "Evaluating…" : "Evaluate"}
          </button>
        </form>

        <div className="panel panel--pad">
          {!result ? (
            <div className="empty" style={{ padding: "40px 12px" }}>
              <svg className="empty__glyph" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3l7 3v5c0 4.4-3 8-7 10-4-2-7-5.6-7-10V6l7-3Z" />
                <path d="m9 11 2 2 4-4" />
              </svg>
              <div className="empty__title">Your verdict shows here</div>
              <p style={{ margin: 0, maxWidth: "34ch" }}>Enter a raw price and at least a PSA 10 price, then hit Evaluate.</p>
            </div>
          ) : (
            <div className="stack">
              <div className="row" style={{ justifyContent: "space-between" }}>
                {reco && (
                  <span className={`reco ${reco.cls}`}>
                    <span className="reco__dot" />
                    {reco.label}
                  </span>
                )}
                {result.roi_pct !== null && (
                  <span className="badge badge--brand">ROI {pct(result.roi_pct)}</span>
                )}
              </div>
              <p style={{ margin: 0, color: "var(--muted)" }}>{result.rationale}</p>
              <div className="ledger">
                <div className="ledger__row">
                  <span className="ledger__k">Sell raw (net)</span>
                  <span className="ledger__v">{money(result.raw_net)}</span>
                </div>
                <div className="ledger__row">
                  <span className="ledger__k">PSA 10 (net)</span>
                  <span className="ledger__v">{money(result.psa10_net)}</span>
                </div>
                <div className="ledger__row">
                  <span className="ledger__k">PSA 9 (net)</span>
                  <span className="ledger__v">{money(result.psa9_net)}</span>
                </div>
                <div className="ledger__row">
                  <span className="ledger__k">Expected graded (net)</span>
                  <span className="ledger__v">{money(result.expected_graded_net)}</span>
                </div>
                <div className="ledger__row is-total">
                  <span className="ledger__k" style={{ color: "var(--ink)", fontWeight: 600 }}>
                    Uplift vs. raw
                  </span>
                  <span
                    className="ledger__v"
                    style={{
                      color:
                        result.uplift === null
                          ? "var(--ink)"
                          : result.uplift > 0
                          ? "var(--gain)"
                          : result.uplift < 0
                          ? "var(--loss)"
                          : "var(--ink)",
                    }}
                  >
                    {money(result.uplift)}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function GradingPage() {
  return (
    <Suspense fallback={<div className="container">Loading…</div>}>
      <GradingForm />
    </Suspense>
  );
}
