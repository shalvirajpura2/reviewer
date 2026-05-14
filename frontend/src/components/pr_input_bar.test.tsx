import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PrInputBar } from "./pr_input_bar";
import { button_by_text, change_input, click_element, create_deferred, render_component, run_timers, wait_for } from "../test/component_test_utils";
import { build_backend_metadata } from "../test/fixtures";
import { preview_pr } from "../lib/api";

vi.mock("../lib/api", () => ({
  preview_pr: vi.fn(),
}));

const preview_pr_mock = vi.mocked(preview_pr);
const valid_pr_url = "https://github.com/acme/reviewer/pull/42";

function render_input_bar() {
  return render_component(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<PrInputBar />} />
        <Route path="/result" element={<div>Result route opened</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PrInputBar", () => {
  beforeEach(() => {
    vi.useRealTimers();
    preview_pr_mock.mockReset();
    document.body.innerHTML = "";
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows validation errors without calling preview API", async () => {
    const view = await render_input_bar();
    const input = document.body.querySelector<HTMLInputElement>("input.pr-url");
    expect(input).not.toBeNull();

    await change_input(input!, "not-a-pr-url");
    await click_element(button_by_text("Preview"));

    expect(document.body.textContent).toContain("Use a full public GitHub pull request URL");
    expect(preview_pr_mock).not.toHaveBeenCalled();

    await view.unmount();
  });

  it("shows loading and API failure states for preview requests", async () => {
    const deferred = create_deferred<Awaited<ReturnType<typeof preview_pr>>>();
    preview_pr_mock.mockReturnValueOnce(deferred.promise);
    const view = await render_input_bar();
    const input = document.body.querySelector<HTMLInputElement>("input.pr-url");

    await change_input(input!, valid_pr_url);
    await click_element(button_by_text("Preview"));

    expect(button_by_text("Checking").disabled).toBe(true);

    deferred.reject(new Error("Preview service unavailable."));
    await wait_for(() => {
      expect(document.body.textContent).toContain("Preview service unavailable.");
    });

    await view.unmount();
  });

  it("opens the preview and navigates to the result page after confirmation", async () => {
    vi.useFakeTimers();
    preview_pr_mock.mockResolvedValueOnce({ metadata: build_backend_metadata() });
    const view = await render_input_bar();
    const input = document.body.querySelector<HTMLInputElement>("input.pr-url");

    await change_input(input!, valid_pr_url);
    await click_element(button_by_text("Preview"));

    await wait_for(() => {
      expect(document.body.textContent).toContain("Pull request preview");
      expect(document.body.textContent).toContain("Tighten review flow");
    });

    await click_element(button_by_text("Analyze this PR"));
    expect(document.body.textContent).toContain("Starting review");

    await run_timers(async () => {
      await vi.advanceTimersByTimeAsync(1050);
    });
    await wait_for(() => {
      expect(document.body.textContent).toContain("Result route opened");
    });

    expect(preview_pr_mock).toHaveBeenCalledWith(valid_pr_url);
    await view.unmount();
  });
});
