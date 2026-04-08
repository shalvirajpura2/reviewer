import { Github, Star } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";

import { get_or_create_client_id, get_repo_stars, get_site_stats, record_site_visit } from "../lib/api";
import { cn } from "../lib/cn";
import { BrandLogo } from "./brand_logo";

const nav_items = [
  { to: "/", label: "Home" },
  { to: "/about", label: "How it works" },
] as const;

const repo_url = "https://github.com/shalvirajpura2/reviewer";
const install_app_url = "https://github.com/apps/reviewer-live";
const builder_url = "https://shalvirajpura.xyz";

function format_star_count(stars: number) {
  if (stars >= 1000) {
    const rounded = stars / 1000;
    return `${rounded >= 10 ? rounded.toFixed(0) : rounded.toFixed(1)}k`;
  }

  return stars.toLocaleString();
}

export function Navbar() {
  const [visitor_count, set_visitor_count] = useState("...");
  const [star_count, set_star_count] = useState<string | null>(null);
  const [is_star_loading, set_is_star_loading] = useState(true);

  useEffect(() => {
    let is_active = true;

    async function load_nav_data() {
      try {
        const client_id = get_or_create_client_id();
        await record_site_visit(client_id);
        const stats = await get_site_stats();

        if (is_active) {
          set_visitor_count(`#${stats.visitor_count.toLocaleString()}`);
        }
      } catch {
        if (is_active) {
          set_visitor_count("unavailable");
        }
      }

      try {
        const repo_stars = await get_repo_stars();

        if (is_active) {
          set_star_count(format_star_count(repo_stars.stars));
          set_is_star_loading(false);
        }
      } catch {
        if (is_active) {
          set_star_count(null);
          set_is_star_loading(false);
        }
      }
    }

    void load_nav_data();

    return () => {
      is_active = false;
    };
  }, []);

  const link_class_name = ({ isActive }: { isActive: boolean }) => cn("nav-tab", isActive && "active");
  const star_label = is_star_loading ? "loading" : star_count ?? "unavailable";

  return (
    <header>
      <nav className="site-nav">
        <div className="nav-left">
          <NavLink to="/" className="nav-logo" aria-label="Reviewer home">
            <BrandLogo className="nav-logo-mark" />
            <span className="nav-logo-word">Reviewer</span>
          </NavLink>
        </div>

        <div className="nav-center">
          <div className="nav-tabs">
            {nav_items.map((nav_item) => (
              <NavLink key={nav_item.to} to={nav_item.to} className={link_class_name} end={nav_item.to === "/"}>
                {nav_item.label}
              </NavLink>
            ))}
            <a href={install_app_url} target="_blank" rel="noreferrer" className="nav-tab">
              Install App
            </a>
            <a href={builder_url} target="_blank" rel="noreferrer" className="nav-tab">
              Builder
            </a>
          </div>
        </div>

        <div className="nav-right">
          <a
            href={repo_url}
            target="_blank"
            rel="noreferrer"
            className="visitor-pill nav-star-pill"
            aria-label="Open Reviewer repository on GitHub"
          >
            <Github className="nav-pill-icon" />
            <span>GitHub</span>
            <b className="nav-pill-count">
              <Star className="nav-pill-star" />
              {star_label}
            </b>
          </a>
          <div className="visitor-pill nav-visitor-pill">
            visitor <b>{visitor_count}</b>
          </div>
        </div>
      </nav>
    </header>
  );
}
