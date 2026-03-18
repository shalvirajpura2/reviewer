import type { SVGProps } from "react";

type BrandLogoProps = SVGProps<SVGSVGElement> & {
  compact?: boolean;
};

export function BrandLogo({ compact = false, className, ...props }: BrandLogoProps) {
  return (
    <svg
      viewBox={compact ? "0 0 64 64" : "0 0 256 256"}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className={className}
      {...props}
    >
      {compact ? (
        <>
          <circle
            cx="32"
            cy="32"
            r="21"
            stroke="var(--brand-ring, #2A2F3A)"
            strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray="116 28"
            transform="rotate(-90 32 32)"
          />
          <path
            d="M32 11 A21 21 0 0 1 51 24"
            stroke="var(--brand-accent, #22D3EE)"
            strokeWidth="5"
            strokeLinecap="round"
            fill="none"
          />
        </>
      ) : (
        <>
          <circle
            cx="128"
            cy="128"
            r="84"
            stroke="var(--brand-ring, #2A2F3A)"
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray="460 80"
            transform="rotate(-90 128 128)"
          />
          <path
            d="M128 44 A84 84 0 0 1 204 96"
            stroke="var(--brand-accent, #22D3EE)"
            strokeWidth="12"
            strokeLinecap="round"
            fill="none"
          />
          <path d="M104 82V174" stroke="var(--brand-mark, #E6EAF0)" strokeWidth="12" strokeLinecap="round" />
          <path
            d="M104 82H146 C164 82 176 94 176 112 C176 130 164 142 146 142 H120"
            stroke="var(--brand-mark, #E6EAF0)"
            strokeWidth="12"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path d="M122 142L176 190" stroke="var(--brand-mark, #E6EAF0)" strokeWidth="12" strokeLinecap="round" />
        </>
      )}
    </svg>
  );
}
