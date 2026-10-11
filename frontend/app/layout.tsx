import "./globals.css";

export const metadata = {
  title: "Batalha de Memes",
  description: "Chaveamento e acompanhamento das batalhas de memes",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
