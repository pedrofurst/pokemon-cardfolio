import type { CSSProperties, ReactNode } from "react";

interface RevealCSSProperties extends CSSProperties {
  "--i"?: number;
}

interface RevealProps {
  children: ReactNode;
  index?: number;
  className?: string;
}

export function Reveal({ children, index = 0, className }: RevealProps) {
  const style: RevealCSSProperties = { "--i": index };
  const classNames = className ? `reveal ${className}` : "reveal";

  return (
    <div className={classNames} style={style}>
      {children}
    </div>
  );
}
