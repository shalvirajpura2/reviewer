/// <reference types="vite/client" />

declare namespace JSX {
  interface IntrinsicElements {
    "lottie-player": {
      src?: string;
      background?: string;
      speed?: string | number;
      loop?: boolean;
      autoplay?: boolean;
      mode?: string;
      renderer?: string;
      className?: string;
      [key: string]: unknown;
    };
  }
}
