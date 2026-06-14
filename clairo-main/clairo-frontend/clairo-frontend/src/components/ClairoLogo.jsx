import { useId } from "react";

/** Tight viewBox around glyph so 1em height matches adjacent cap height. */
const LOGO_VIEWBOX = "18 20 64 68";

export default function ClairoLogo({
  size = 48,
  inline = false,
  className = "",
  title = "CLΔIRO",
}) {
  const glowId = useId().replace(/:/g, "");

  const classes = [
    "brand-logo",
    inline ? "brand-logo--inline" : "brand-logo--standalone",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const sizeProps = inline
    ? {}
    : { width: size, height: size };

  return (
    <svg
      {...sizeProps}
      viewBox={LOGO_VIEWBOX}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={classes}
      role="img"
      aria-label={title}
      preserveAspectRatio="xMidYMid meet"
    >
      {!inline && (
        <defs>
          <filter
            id={`clairo-logo-glow-${glowId}`}
            x="-30%"
            y="-30%"
            width="160%"
            height="160%"
          >
            <feGaussianBlur stdDeviation="1.2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
      )}

      <g
        {...(!inline && {
          filter: `url(#clairo-logo-glow-${glowId})`,
        })}
      >
        <path
          d="M 19 78 L 50 21"
          stroke="currentColor"
          strokeWidth="6.25"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M 81 78 L 50 21"
          stroke="currentColor"
          strokeWidth="6.25"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M 19 78 L 37.5 78"
          stroke="currentColor"
          strokeWidth="6.25"
          strokeLinecap="round"
        />
        <path
          d="M 62.5 78 L 81 78"
          stroke="currentColor"
          strokeWidth="6.25"
          strokeLinecap="round"
        />
        <path
          fill="currentColor"
          d="M 50 49.5
             L 52.4 67.5
             L 50 87.5
             L 47.6 67.5
             Z
             M 50 66.5
             L 39.5 71.5
             L 50 75.5
             L 60.5 71.5
             Z"
        />
      </g>
    </svg>
  );
}
