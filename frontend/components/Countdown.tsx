"use client";

import { Fragment, useEffect, useState } from "react";

// Cronômetro digital da votação. O alvo é o próximo domingo 23:59 (hora local);
// o primeiro render é neutro ("--") e só o cliente conta, evitando divergência
// de hidratação no export estático.

const ETAPAS = ["dias", "horas", "min", "seg"] as const;

function alvoFechamento(): number {
  const agora = new Date();
  const alvo = new Date(agora);
  const ateDomingo = (7 - alvo.getDay()) % 7;
  alvo.setDate(alvo.getDate() + ateDomingo);
  alvo.setHours(23, 59, 59, 0);
  if (alvo.getTime() <= agora.getTime()) alvo.setDate(alvo.getDate() + 7);
  return alvo.getTime();
}

function duplas(ms: number): string[] {
  const s = Math.max(0, Math.floor(ms / 1000));
  return [
    Math.floor(s / 86400),
    Math.floor((s % 86400) / 3600),
    Math.floor((s % 3600) / 60),
    s % 60,
  ].map((n) => String(n).padStart(2, "0"));
}

export function Countdown() {
  const [valores, setValores] = useState<string[] | null>(null);

  useEffect(() => {
    const alvo = alvoFechamento();
    const tick = () => setValores(duplas(alvo - Date.now()));
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, []);

  const digitos = valores ?? ["--", "--", "--", "--"];

  return (
    <div className="crono" role="timer" aria-label="tempo restante de votação">
      {digitos.map((valor, i) => (
        <Fragment key={ETAPAS[i]}>
          {i > 0 ? (
            <span className="crono-sep" aria-hidden>
              :
            </span>
          ) : null}
          <span className="crono-bloco">
            <b>{valor}</b>
            <small>{ETAPAS[i]}</small>
          </span>
        </Fragment>
      ))}
    </div>
  );
}
