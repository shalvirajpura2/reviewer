import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ResultPage } from "./result_page";
import { analyze_pr } from "../lib/api";
import { button_by_text, click_element, create_deferred, render_component, wait_for } from "../test/component_test_utils";
import { build_backend_analysis } from "../test/fixtures";

vi.mock("../lib/api", () => ({
  analyze_pr: vi.fn(),
}));

const analyze_pr_mock = vi.mocked(analyze_pr);
const result_path = "/result?pr_url=https%3A%2F%2Fgithub.com%2Facme%2Freviewer%2Fpull%2F42";

function render_result_page(initial_entry = result_path) {
  return render_component(
    <MemoryRouter initialEntries={[initial_entry]}>
      <Routes>
        <Route path="/" element={<div>Home route opened</div>} />
        <Route path="/result" element={<ResultPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ResultPage", () => {
  beforeEach(() => {
    analyze_pr_mock.mockReset();
    document.body.innerHTML = "";
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows loading state while analysis is pending", async () => {
    const deferred = create_deferred<Awaited<ReturnType<typeof analyze_pr>>>();
    analyze_pr_mock.mockReturnValueOnce(deferred.promise);
    const view = await render_result_page();

    expect(document.body.textContent).toContain("building your review");
    expect(document.body.textContent).toContain("Reading pull request metadata");

    deferred.resolve(build_backend_analysis());
    await wait_for(() => {
      expect(document.body.textContent).toContain("Tighten review flow");
      expect(document.body.textContent).toContain("Mergeable with routine review");
    });

    await view.unmount();
  });

  it("navigates home when the result URL is missing a PR URL", async () => {
    analyze_pr_mock.mockResolvedValueOnce(build_backend_analysis());
    const view = await render_result_page("/result");

    await wait_for(() => {
      expect(document.body.textContent).toContain("Home route opened");
    });
    expect(analyze_pr_mock).not.toHaveBeenCalled();

    await view.unmount();
  });

  it("keeps the current result visible when force refresh fails", async () => {
    analyze_pr_mock.mockResolvedValueOnce(build_backend_analysis());
    analyze_pr_mock.mockRejectedValueOnce(new Error("Live analysis failed."));
    const view = await render_result_page();

    await wait_for(() => {
      expect(document.body.textContent).toContain("Mergeable with routine review");
    });

    await click_element(button_by_text("Fetch fresh live analysis"));

    await wait_for(() => {
      expect(document.body.textContent).toContain("fresh analysis unavailable");
      expect(document.body.textContent).toContain("Live analysis failed.");
      expect(document.body.textContent).toContain("Mergeable with routine review");
    });

    expect(analyze_pr_mock).toHaveBeenNthCalledWith(1, "https://github.com/acme/reviewer/pull/42", false, expect.any(AbortSignal));
    expect(analyze_pr_mock).toHaveBeenNthCalledWith(2, "https://github.com/acme/reviewer/pull/42", true, expect.any(AbortSignal));

    await view.unmount();
  });
});
