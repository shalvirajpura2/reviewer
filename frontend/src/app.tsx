import { lazy, Suspense } from "react";
import { Analytics } from "@vercel/analytics/react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppErrorBoundary } from "./components/app_error_boundary";
import { FirstVisitIntro } from "./components/first_visit_intro";
import { Navbar } from "./components/navbar";

const AboutPage = lazy(() => import("./pages/about_page").then((module) => ({ default: module.AboutPage })));
const GithubBotPage = lazy(() => import("./pages/github_bot_page").then((module) => ({ default: module.GithubBotPage })));
const HomePage = lazy(() => import("./pages/home_page").then((module) => ({ default: module.HomePage })));
const NotFoundPage = lazy(() => import("./pages/not_found_page").then((module) => ({ default: module.NotFoundPage })));
const ResultPage = lazy(() => import("./pages/result_page").then((module) => ({ default: module.ResultPage })));

function RouteLoadingFallback() {
  return (
    <div className="app-shell-status">
      <div className="app-shell-status-card">
        <div className="app-shell-status-label">loading</div>
        <h1 className="app-shell-status-title">Opening Reviewer.</h1>
        <p className="app-shell-status-copy">The next page is loading now.</p>
      </div>
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AppErrorBoundary>
        <div className="min-h-screen bg-background text-text_primary">
          <FirstVisitIntro />
          <Navbar />
          <Suspense fallback={<RouteLoadingFallback />}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/about" element={<AboutPage />} />
              <Route path="/github" element={<GithubBotPage />} />
              <Route path="/history" element={<Navigate to="/" replace />} />
              <Route path="/result" element={<ResultPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Suspense>
          <Analytics />
        </div>
      </AppErrorBoundary>
    </BrowserRouter>
  );
}
