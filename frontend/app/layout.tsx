import "./globals.css";

import { JetBrains_Mono, Space_Grotesk } from "next/font/google";

import { MotionProvider } from "@/components/MotionProvider";
import { SiteHeader } from "@/components/SiteHeader";
import { listarTorneios } from "@/lib/estado";

const sans = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata = {
  title: "Batalha de Memes",
  description:
    "Chaveamento animado da Batalha de Memes: veja todos os competidores, o caminho de cada meme e assista aos vídeos originais.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const torneios = listarTorneios();
  const torneioId = torneios[0]?.id;

  return (
    <html lang="pt-BR" className={`${sans.variable} ${mono.variable}`}>
      <body>
        <div className="aurora" aria-hidden>
          <span />
          <span />
          <span />
        </div>

        <MotionProvider>
          <SiteHeader torneioId={torneioId} />
          <main>{children}</main>
        </MotionProvider>
      </body>
    </html>
  );
}