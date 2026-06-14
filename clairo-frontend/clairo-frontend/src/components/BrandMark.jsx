import ClairoLogo from "./ClairoLogo";

/** User-visible brand label — internal ids/routes stay unchanged. */
export const BRAND_NAME = "CLΔIRO";

export function BrandMark({ className = "", logoClassName = "" }) {
  return (
    <span className={`brand-mark ${className}`.trim()}>
      <span className="brand-mark__text" aria-hidden="true">
        CL
      </span>
      <span className="brand-mark__logo-wrap" aria-hidden="true">
        <ClairoLogo
          inline
          className={`brand-mark__logo ${logoClassName}`.trim()}
        />
      </span>
      <span className="brand-mark__text" aria-hidden="true">
        IRO
      </span>
      <span className="sr-only">{BRAND_NAME}</span>
    </span>
  );
}
