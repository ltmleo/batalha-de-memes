import "./globals.css";

import { JetBrains_Mono, Outfit, Space_Grotesk } from "next/font/google";

import { MotionProvider } from "@/components/MotionProvider";
import { SiteFooter } from "@/components/SiteFooter";
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

const display = Outfit({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

export const metadata = {
  title: "Copa do Meme — a Copa do Mundo da internet",
  description:
    "Batalha de memes em formato de Copa do Mundo: vote no ringue, acompanhe o chaveamento e visite o cemitério dos caídos.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const torneios = listarTorneios();

  return (
    <html lang="pt-BR" className={`${display.variable} ${sans.variable} ${mono.variable}`}>
      <body>
        <div className="aurora" aria-hidden>
          <span />
          <span />
          <span />
        </div>

        <MotionProvider>
          <SiteHeader />
          <main>{children}</main>
          <SiteFooter torneios={torneios} />
        </MotionProvider>
      </body>
    </html>
  );
}