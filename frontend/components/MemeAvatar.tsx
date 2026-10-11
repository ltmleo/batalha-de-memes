import type { CSSProperties } from "react";

import { hueForId, iniciais } from "@/lib/format";

/** Estilo com a matiz (hue) estável do meme — usado por cards, slots e avatares. */
export function hueStyle(id: number): CSSProperties {
  return { "--hue": hueForId(id) } as CSSProperties;
}

export function MemeAvatar({ id, nome }: { id: number; nome: string }) {
  return (
    <span className="avatar" style={hueStyle(id)} aria-hidden>
      {iniciais(nome)}
    </span>
  );
}
