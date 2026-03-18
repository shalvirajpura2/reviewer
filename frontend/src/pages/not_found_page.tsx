import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="page active">
      <div className="app-shell-status">
        <div className="app-shell-status-card">
          <div className="app-shell-status-label">404</div>
          <h1 className="app-shell-status-title">This page does not exist.</h1>
          <p className="app-shell-status-copy">The link is missing or no longer valid. Go back to the homepage and start a new review.</p>
          <div className="app-shell-status-actions">
            <Link to="/" className="app-shell-status-button">
              Go home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
