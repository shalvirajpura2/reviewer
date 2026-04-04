export const sample_pr_url = "https://github.com/tailwindlabs/tailwindcss/pull/14776";

export function normalize_pr_url(value: string) {
  return value.trim();
}

export function is_valid_github_pr_url(value: string) {
  try {
    const url = new URL(normalize_pr_url(value));
    const segments = url.pathname.split("/").filter(Boolean);

    return (
      (url.protocol === "https:" || url.protocol === "http:") &&
      (url.hostname === "github.com" || url.hostname === "www.github.com") &&
      segments.length >= 4 &&
      segments[2] === "pull" &&
      /^\d+$/.test(segments[3] ?? "")
    );
  } catch {
    return false;
  }
}

export function pr_url_validation_message(value: string) {
  if (!normalize_pr_url(value)) {
    return "Enter a GitHub pull request URL.";
  }

  if (!is_valid_github_pr_url(value)) {
    return "Use a full public GitHub pull request URL like https://github.com/owner/repo/pull/123.";
  }

  return null;
}
