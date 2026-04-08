import { Analytics } from "@vercel/analytics/react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppErrorBoundary } from "./components/app_error_boundary";
import { FirstVisitIntro } from "./components/first_visit_intro";
import { Navbar } from "./components/navbar";
import { AboutPage } from "./pages/about_page";
import { GithubBotPage } from "./pages/github_bot_page";
import { HomePage } from "./pages/home_page";
import { NotFoundPage } from "./pages/not_found_page";
import { ResultPage } from "./pages/result_page";

export function App() {
  return (
    <BrowserRouter>
      <AppErrorBoundary>
        <div className="min-h-screen bg-background text-text_primary">
          <FirstVisitIntro />
          <Navbar />
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/github" element={<GithubBotPage />} />
            <Route path="/history" element={<Navigate to="/" replace />} />
            <Route path="/result" element={<ResultPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
          <Analytics />
        </div>
      </AppErrorBoundary>
    </BrowserRouter>
  );
}
