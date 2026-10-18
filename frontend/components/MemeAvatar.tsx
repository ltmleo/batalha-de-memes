import type { CSSProperties } from "react";

import { hueForId } from "@/lib/format";

/** Estilo com a matiz (hue) estável do meme — usado por cards, slots e avatares. */
export function hueStyle(id: number): CSSProperties {
  return { "--hue": hueForId(id) } as CSSProperties;
}
