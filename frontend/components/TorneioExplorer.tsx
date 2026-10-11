"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState } from "react";

import { BracketView } from "@/components/BracketView";
import { CompetidoresGrid } from "@/components/CompetidoresGrid";
import type { Meme, TournamentDetail } from "@/lib/types";

type Aba = "chave" | "competidores";

export function TorneioExplorer({
  detail,
  competidores,
}: {
  detail: TournamentDetail;
  competidores: Meme[];
}) {
  const [aba, setAba] = useState<Aba>("chave");
  const [focusedId, setFocusedId] = useState<number | null>(null);
  const reduzir = useReducedMotion();

  const abas: { id: Aba; label: string }[] = [
    { id: "chave", label: "Chaveamento" },
    { id: "competidores", label: `Competidores (${competidores.length})` },
  ];

  function focar(id: number | null) {
    setFocusedId(id);
    if (id) setAba("chave");
  }

  return (
    <div>
      <div className="tabs" role="tablist" aria-label="Visões do torneio">
        {abas.map((a) => (
          <button
            key={a.id}
            type="button"
            role="tab"
            aria-selected={aba === a.id}
            className="tab"
            onClick={() => setAba(a.id)}
          >
            {aba === a.id ? (
              <motion.span
                layoutId="pilula-aba"
                className="tab-pill"
                transition={
                  reduzir
                    ? { duration: 0 }
                    : { type: "spring", stiffness: 520, damping: 40 }
                }
              />
            ) : null}
            <span className="tab-label">{a.label}</span>
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={aba}
          initial={reduzir ? { opacity: 0 } : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduzir ? { opacity: 0 } : { opacity: 0, y: -8 }}
          transition={{ duration: reduzir ? 0.16 : 0.28, ease: [0.16, 1, 0.3, 1] }}
        >
          {aba === "chave" ? (
            <BracketView detail={detail} focusedId={focusedId} onFocusChange={setFocusedId} />
          ) : (
            <CompetidoresGrid
              memes={competidores}
              focusedId={focusedId}
              onFocusBracket={focar}
            />
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
