"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function SiteHeader({ torneioId }: { torneioId?: number }) {
  const pathname = usePathname();
  const ativo = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <header className="site-header">
      <div className="wrap">
        <Link href="/" className="brand" aria-label="Batalha de Memes — início">
          <span className="logo" aria-hidden>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
              <path d="M12 3v18" />
              <path d="M4 7h8" />
              <path d="M4 17h8" />
              <path d="M12 12h8" />
              <path d="M20 9.5v5" />
            </svg>
          </span>
          <b>Batalha de Memes</b>
        </Link>

        <nav className="nav" aria-label="Navegação principal">
          {torneioId ? (
            <Link href={`/torneio/${torneioId}`} data-ativo={ativo("/torneio")}>
              Chaveamento
            </Link>
          ) : null}
          <Link href="/competidores" data-ativo={ativo("/competidores")}>
            Competidores
          </Link>
        </nav>
      </div>
    </header>
  );
}
