"use client";

import { useState } from "react";

/**
 * Formulário de sugestão de candidato. Sem backend: o envio abre o app de
 * e-mail do visitante com a mensagem pronta (padrão de site estático).
 */
export function SuggestForm() {
  const [nome, setNome] = useState("");
  const [dica, setDica] = useState("");

  const enviar = (e: React.FormEvent) => {
    e.preventDefault();
    const corpo = [
      "Candidato sugerido pelo site:",
      "",
      `  Meme: ${nome.trim() || "—"}`,
      `  Dica de vídeo original: ${dica.trim() || "—"}`,
    ].join("\n");
    window.location.href =
      "mailto:?subject=" +
      encodeURIComponent("Sugestão de meme — Batalha de Memes") +
      "&body=" +
      encodeURIComponent(corpo);
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
        Sugerir candidato
      </button>
    </form>
  );
}