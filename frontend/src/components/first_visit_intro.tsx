import { useEffect, useState } from "react";

const intro_storage_key = "reviewer_intro_seen_v1";
const intro_duration_ms = 1700;
const fade_duration_ms = 320;

function get_should_show_intro() {
  try {
    return window.localStorage.getItem(intro_storage_key) !== "seen";
  } catch {
    return false;
  }
}

export function FirstVisitIntro() {
  const [should_render, set_should_render] = useState(get_should_show_intro);
  const [is_exiting, set_is_exiting] = useState(false);

  useEffect(() => {
    if (!should_render) {
      return;
    }

    let hide_timeout = 0;
    let remove_timeout = 0;

    hide_timeout = window.setTimeout(() => {
      set_is_exiting(true);
    }, intro_duration_ms);

    remove_timeout = window.setTimeout(() => {
      try {
        window.localStorage.setItem(intro_storage_key, "seen");
      } catch {}

      set_should_render(false);
    }, intro_duration_ms + fade_duration_ms);

    return () => {
      window.clearTimeout(hide_timeout);
      window.clearTimeout(remove_timeout);
    };
  }, [should_render]);

  if (!should_render) {
    return null;
  }

  return (
    <div className={`intro-overlay ${is_exiting ? "is-exiting" : ""}`} aria-hidden="true">
      <div className="intro-shell">
        <svg className="intro-mark" viewBox="0 0 256 256" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle className="intro-ring" cx="128" cy="128" r="84" />
          <path className="intro-arc" d="M128 44 A84 84 0 0 1 204 96" />
          <path className="intro-r-mark" d="M104 82V174" />
          <path className="intro-r-mark" d="M104 82H146 C164 82 176 94 176 112 C176 130 164 142 146 142 H120" />
          <path className="intro-r-mark" d="M122 142L176 190" />
        </svg>
        <div className="intro-wordmark">Reviewer</div>
      </div>
    </div>
  );
}
