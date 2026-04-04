import { describe, expect, it } from "vitest";

import { is_valid_github_pr_url, pr_url_validation_message } from "./pr_url";

describe("pr url validation", () => {
  it("accepts github and www.github hosts", () => {
    expect(is_valid_github_pr_url("https://github.com/acme/repo/pull/123")).toBe(true);
    expect(is_valid_github_pr_url("https://www.github.com/acme/repo/pull/123")).toBe(true);
  });

  it("rejects non-pull-request urls", () => {
    expect(pr_url_validation_message("https://github.com/acme/repo/issues/123")).toBe(
      "Use a full public GitHub pull request URL like https://github.com/owner/repo/pull/123."
    );
  });
});