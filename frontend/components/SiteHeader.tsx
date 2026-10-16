"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/#ringue", rotulo: "batalhas", marca: "#ringue" },
  { href: "/#chave", rotulo: "chaveamento", marca: "/torneio" },
  { href: "/#cemiterio", rotulo: "cemitério dos caídos", marca: "#cemiterio" },
  { href: "/#var", rotulo: "regras (var)", marca: "#var" },
];

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="site-header">
      <div className="wrap">
        <Link href="/" className="brand" aria-label="Copa do Meme — início">
          <span className="logo" aria-hidden>
            <svg viewBox="0 0 48 48" fill="none">
              <defs>
                <linearGradient id="trofeu-ouro" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor="#fff2b0" />
                  <stop offset="0.55" stopColor="#ffd93d" />
                  <stop offset="1" stopColor="#e09a00" />
                </linearGradient>
              </defs>
              <path
                d="M13 11H7.5a6 6 0 0 0 6.2 10"
                stroke="#e09a00"
                strokeWidth="2.6"
                strokeLinecap="round"
              />
              <path
                d="M35 11h5.5a6 6 0 0 1-6.2 10"
                stroke="#e09a00"
                strokeWidth="2.6"
                strokeLinecap="round"
              />
              <path
                d="M12 8.5h24v9.5a12 12 0 0 1-24 0z"
                fill="url(#trofeu-ouro)"
                stroke="#8a5a00"
                strokeWidth="2"
              />
              <circle cx="20" cy="16.4" r="1.9" fill="#4a2c00" />
              <circle cx="28" cy="16.4" r="1.9" fill="#4a2c00" />
              <path
                d="M20.4 20.6c1.7 2.1 5.5 2.1 7.2 0"
                stroke="#4a2c00"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
              <path d="M24 30v6" stroke="#8a5a00" strokeWidth="3.2" strokeLinecap="round" />
              <path d="M18 36.5h12l-1.4 5h-9.2z" fill="url(#trofeu-ouro)" stroke="#8a5a00" strokeWidth="2" strokeLinejoin="round" />
            </svg>
          </span>
          <b className="brand-nome">
            copa do <em>meme</em>
          </b>
        </Link>

        <nav className="nav" aria-label="Navegação principal">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              data-ativo={l.marca.startsWith("/") ? pathname.startsWith(l.marca) : undefined}
            >
              {l.rotulo}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
