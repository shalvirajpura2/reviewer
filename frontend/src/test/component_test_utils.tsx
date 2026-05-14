import { act } from "react";
import { createRoot } from "react-dom/client";
import type { ReactNode } from "react";

declare global {
  var IS_REACT_ACT_ENVIRONMENT: boolean;
}

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

export function create_deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promise_resolve, promise_reject) => {
    resolve = promise_resolve;
    reject = promise_reject;
  });

  return { promise, resolve, reject };
}

export async function render_component(node: ReactNode) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);

  await act(async () => {
    root.render(node);
  });

  return {
    container,
    unmount: async () => {
      await act(async () => {
        root.unmount();
      });
      container.remove();
    },
  };
}

export async function click_element(element: HTMLElement) {
  await act(async () => {
    element.click();
  });
}

export async function change_input(input: HTMLInputElement, value: string) {
  await act(async () => {
    const value_setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
    value_setter?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

export async function wait_for(assertion: () => void, timeout_ms = 1000) {
  const started_at = Date.now();
  let last_error: unknown;

  while (Date.now() - started_at < timeout_ms) {
    try {
      assertion();
      return;
    } catch (error) {
      last_error = error;
      await act(async () => {
        await new Promise((resolve) => window.setTimeout(resolve, 10));
      });
    }
  }

  throw last_error;
}

export function button_by_text(label: string) {
  const buttons = Array.from(document.body.querySelectorAll("button"));
  const button = buttons.find((item) => item.textContent?.includes(label));
  if (!button) {
    throw new Error(`Button not found: ${label}`);
  }

  return button as HTMLButtonElement;
}
