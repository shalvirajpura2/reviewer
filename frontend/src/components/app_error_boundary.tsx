import { Component, type ErrorInfo, type ReactNode } from "react";
import { Link } from "react-router-dom";

type AppErrorBoundaryProps = {
  children: ReactNode;
};

type AppErrorBoundaryState = {
  has_error: boolean;
};

export class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = {
    has_error: false,
  };

  static getDerivedStateFromError() {
    return { has_error: true };
  }

  componentDidCatch(_error: Error, _error_info: ErrorInfo) {}

  render() {
    if (this.state.has_error) {
      return (
        <div className="app-shell-status">
          <div className="app-shell-status-card">
            <div className="app-shell-status-label">something went wrong</div>
            <h1 className="app-shell-status-title">Reviewer could not render this page.</h1>
            <p className="app-shell-status-copy">Refresh the page or go back home and try the analysis again.</p>
            <div className="app-shell-status-actions">
              <button type="button" className="app-shell-status-button" onClick={() => window.location.reload()}>
                Refresh
              </button>
              <Link to="/" className="app-shell-status-link">
                Go home
              </Link>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
