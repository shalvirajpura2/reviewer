import { Link } from "react-router-dom";

import { BrandLogo } from "./brand_logo";

const footer_links = [
  { label: "Home", to: "/", external: false },
  { label: "How it works", to: "/about", external: false },
  { label: "GitHub", to: "https://github.com/shalvirajpura2/reviewer", external: true },
  { label: "Builder", to: "https://shalvirajpura.xyz", external: true },
] as const;

export function SiteFooter() {
  return (
    <footer className="site-footer site-footer-minimal">
      <Link to="/" className="footer-minimal-brand" aria-label="Reviewer home">
        <BrandLogo className="footer-logo-mark" />
        <span className="footer-logo-word">Reviewer</span>
      </Link>
      <div className="footer-minimal-links">
        {footer_links.map((footer_link) =>
          footer_link.external ? (
            <a key={footer_link.label} href={footer_link.to} target="_blank" rel="noreferrer" className="footer-minimal-link">
              {footer_link.label}
            </a>
          ) : (
            <Link key={footer_link.label} to={footer_link.to} className="footer-minimal-link">
              {footer_link.label}
            </Link>
          )
        )}
      </div>
    </footer>
  );
}
