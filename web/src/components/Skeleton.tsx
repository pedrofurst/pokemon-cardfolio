import type { CSSProperties } from "react";

interface SkeletonProps {
  className?: string;
  style?: CSSProperties;
}

export function Skeleton({ className, style }: SkeletonProps) {
  const classNames = className ? `skeleton ${className}` : "skeleton";

  return <div className={classNames} style={style} aria-hidden />;
}

const SKELETON_SLAB_HEIGHT_PX = 150;

export function SkeletonSlab() {
  return (
    <Skeleton
      className="skeleton--slab"
      style={{ height: SKELETON_SLAB_HEIGHT_PX }}
    />
  );
}

interface SkeletonCardGridProps {
  count?: number;
}

export function SkeletonCardGrid({ count = 8 }: SkeletonCardGridProps) {
  const placeholders = Array.from({ length: count }, (_, index) => index);

  return (
    <div className="card-grid" aria-hidden>
      {placeholders.map((placeholderIndex) => (
        <Skeleton key={placeholderIndex} className="skeleton--tile" />
      ))}
    </div>
  );
}
