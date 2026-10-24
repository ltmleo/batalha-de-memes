"use client";

import { useState } from "react";

import { REPO_URL } from "@/lib/site";

/**
 * Formulário de sugestão de candidato. Sem backend: o envio abre uma issue
 * pré-preenchida no GitHub do projeto (precisa de conta no GitHub), onde a
 * sugestão fica registrada e pode ser discutida antes de entrar no catálogo.
 */
export function SuggestForm() {
  const [nome, setNome] = useState("");
  const [dica, setDica] = useState("");

  const enviar = (e: React.FormEvent) => {
    e.preventDefault();
    const corpo = [
      "Candidato sugerido pelo site:",
      "",
      `- **Meme:** ${nome.trim() || "—"}`,
      `- **Vídeo original / dica:** ${dica.trim() || "—"}`,
    ].join("\n");
    const url =
      `${REPO_URL}/issues/new?labels=sugestao` +
      `&title=${encodeURIComponent(`Sugestão de meme: ${nome.trim()}`)}` +
      `&body=${encodeURIComponent(corpo)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  return (
    <form className="suggest-form" onSubmit={enviar}>
      <label className="suggest-field">
        <span>Nome do meme</span>
        <input
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          placeholder="ex.: Bora Bill"
          required
        />
      </label>
      <label className="suggest-field">
        <span>Dica de vídeo original (opcional)</span>
        <input
          value={dica}
          onChange={(e) => setDica(e.target.value)}
          placeholder="link ou trecho"
        />
      </label>
      <button className="btn btn--primary btn--sm" type="submit">
        Sugerir no GitHub ↗
      </button>
    </form>
  );
}
