"use client";

import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";

// useLayoutEffect measures before paint, so the chart never shows a frame at its
// fallback width. It doesn't run on the server, where there is nothing to
// measure, so fall back to useEffect there to avoid React's SSR warning.
const useMeasureEffect = typeof window !== "undefined" ? useLayoutEffect : useEffect;

interface TrendChartPoint {
  t: string;
  v: number;
}

interface TrendChartProps {
  points: TrendChartPoint[];
  height?: number;
  accent?: string;
  ariaLabel?: string;
}

const FALLBACK_WIDTH = 300;
const VERTICAL_PADDING_RATIO = 0.14;
const FALLBACK_PATH_LENGTH = 1000;
const END_POINT_RADIUS = 4;

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

function buildLinePath(coordinates: Array<[number, number]>): string {
  return coordinates
    .map(([x, y], index) => `${index === 0 ? "M" : "L"}${x},${y}`)
    .join(" ");
}

export function TrendChart({ points, height = 96, accent, ariaLabel }: TrendChartProps) {
  const gradientId = `trend-gradient-${useId()}`;
  const lineRef = useRef<SVGPathElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [pathLength, setPathLength] = useState(FALLBACK_PATH_LENGTH);
  const [isDrawn, setIsDrawn] = useState(false);
  // The viewBox tracks the rendered pixel width so one SVG unit is always one
  // pixel. Without this the chart stretches a fixed-width viewBox across the
  // container, which turns the end-point circle into an ellipse and makes
  // stroke widths differ between the horizontal and vertical axes.
  const [chartWidth, setChartWidth] = useState(FALLBACK_WIDTH);

  useMeasureEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    function measure(width: number) {
      if (width > 0) {
        setChartWidth(width);
      }
    }

    measure(container.getBoundingClientRect().width);

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        measure(entry.contentRect.width);
      }
    });
    observer.observe(container);

    return () => observer.disconnect();
  }, []);

  const strokeColor = accent ?? "var(--brand)";
  const hasEnoughHistory = points.length >= 2;

  const values = points.map((point) => point.v);
  const minValue = hasEnoughHistory ? Math.min(...values) : 0;
  const maxValue = hasEnoughHistory ? Math.max(...values) : 0;
  const valueRange = maxValue - minValue;
  const verticalPadding = height * VERTICAL_PADDING_RATIO;
  const usableHeight = height - verticalPadding * 2;

  // Inset by the marker radius so the end-point dot isn't clipped at the edges.
  const horizontalInset = END_POINT_RADIUS;
  const usableWidth = Math.max(chartWidth - horizontalInset * 2, 1);

  const coordinates: Array<[number, number]> = hasEnoughHistory
    ? points.map((point, index) => {
        const x = horizontalInset + (index / (points.length - 1)) * usableWidth;
        const normalized = valueRange === 0 ? 0.5 : (point.v - minValue) / valueRange;
        const y = verticalPadding + (1 - normalized) * usableHeight;
        return [x, y];
      })
    : [];

  const linePath = buildLinePath(coordinates);
  const lastCoordinate = coordinates[coordinates.length - 1];
  const firstCoordinate = coordinates[0];
  const areaPath =
    linePath && lastCoordinate && firstCoordinate
      ? `${linePath} L${lastCoordinate[0]},${height} L${firstCoordinate[0]},${height} Z`
      : "";

  useEffect(() => {
    if (!hasEnoughHistory || !lineRef.current) {
      return;
    }

    const measuredLength = lineRef.current.getTotalLength();
    setPathLength(measuredLength);

    if (prefersReducedMotion()) {
      setIsDrawn(true);
      return;
    }

    setIsDrawn(false);
    const frame = requestAnimationFrame(() => {
      setIsDrawn(true);
    });

    return () => cancelAnimationFrame(frame);
  }, [hasEnoughHistory, linePath]);

  if (!hasEnoughHistory) {
    return (
      <div ref={containerRef} className="trend-chart trend-chart--empty" style={{ height }}>
        <svg
          viewBox={`0 0 ${chartWidth} ${height}`}
          width="100%"
          height={height}
          aria-hidden="true"
        >
          <line
            x1={0}
            y1={height / 2}
            x2={chartWidth}
            y2={height / 2}
            stroke="var(--line)"
            strokeWidth={1.5}
            strokeDasharray="4 4"
          />
        </svg>
        <p className="trend-chart__caption">Not enough history yet — refresh a few times.</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="trend-chart" style={{ height }}>
      <svg
        viewBox={`0 0 ${chartWidth} ${height}`}
        width="100%"
        height={height}
        role="img"
        aria-label={ariaLabel ?? "Trend chart"}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={strokeColor} stopOpacity={0.18} />
            <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
          </linearGradient>
        </defs>
        <path
          d={areaPath}
          fill={`url(#${gradientId})`}
          stroke="none"
          className="trend-area"
          style={{ opacity: isDrawn ? 1 : 0 }}
        />
        <path
          ref={lineRef}
          d={linePath}
          fill="none"
          stroke={strokeColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="trend-line"
          style={{
            strokeDasharray: pathLength,
            strokeDashoffset: isDrawn ? 0 : pathLength,
          }}
        />
        {lastCoordinate && (
          <circle
            cx={lastCoordinate[0]}
            cy={lastCoordinate[1]}
            r={END_POINT_RADIUS}
            fill={strokeColor}
          />
        )}
      </svg>
    </div>
  );
}
