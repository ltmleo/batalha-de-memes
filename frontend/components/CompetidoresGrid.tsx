"use client";

import { motion, useReducedMotion } from "motion/react";
import { useMemo, useState } from "react";

import { MemeCard } from "@/components/MemeCard";
import type { Meme } from "@/lib/types";

function normalizar(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

export function CompetidoresGrid({
  memes,
  onFocusBracket,
  focusedId,
}: {
  memes: Meme[];
  onFocusBracket?: (id: number) => void;
  focusedId?: number | null;
}) {
  const [q, setQ] = useState("");
  const [tag, setTag] = useState<string | null>(null);
  const reduzir = useReducedMotion();

  const tags = useMemo(() => {
    const contagem = new Map<string, number>();
    for (const m of memes) for (const t of m.tags) contagem.set(t, (contagem.get(t) ?? 0) + 1);
    return [...contagem.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 14);
  }, [memes]);

  const filtrados = useMemo(() => {
    const termo = normalizar(q.trim());
    return memes.filter((m) => {
      if (tag && !m.tags.includes(tag)) return false;
      if (!termo) return true;
      return (
        normalizar(m.nome).includes(termo) ||
        normalizar(m.historia ?? "").includes(termo) ||
        normalizar(m.origem ?? "").includes(termo) ||
        m.tags.some((t) => normalizar(t).includes(termo))
      );
    });
  }, [memes, q, tag]);

  return (
    <div>
      <div className="toolbar glass">
        <label className="search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
            <circle cx="11" cy="11" r="7" />
            <path d="m21 21-4.3-4.3" strokeLinecap="round" />
          </svg>
          <span className="sr-only">Buscar competidor</span>
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar por nome, origem ou história…"
          />
        </label>
        <div className="filter-tags">
          <button
            type="button"
            className={`chip${tag === null ? " chip--active" : ""}`}
            onClick={() => setTag(null)}
          >
            todos
          </button>
          {tags.map(([t, n]) => (
            <button
              key={t}
              type="button"
              className={`chip${tag === t ? " chip--active" : ""}`}
              onClick={() => setTag(tag === t ? null : t)}
            >
              {t} <span className="chip-n">{n}</span>
            </button>
          ))}
        </div>
        <span className="count">
          {filtrados.length} de {memes.length}
        </span>
      </div>

      {filtrados.length === 0 ? (
        <div className="empty-box">Nenhum competidor encontrado para “{q}”.</div>
      ) : (
        <motion.div
          key={tag ?? "todos"}
          className="grid"
          initial={reduzir ? { opacity: 0 } : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: reduzir ? 0.18 : 0.4, ease: [0.16, 1, 0.3, 1] }}
        >
          {filtrados.map((m) => (
            <MemeCard
              key={m.id}
              meme={m}
              onFocusBracket={onFocusBracket}
              focused={focusedId === m.id}
            />
          ))}
        </motion.div>
      )}
    </div>
  );
}
