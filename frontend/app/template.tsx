"use client";

import { motion, useReducedMotion } from "motion/react";

/**
 * Transição de entrada por rota (Next.js App Router). `template.tsx` remonta a
 * cada navegação, então cada página entra com um leve fade + subida. Com
 * `prefers-reduced-motion` só resta o fade.
 */
export default function Template({ children }: { children: React.ReactNode }) {
  const reduzir = useReducedMotion();

  return (
    <motion.div
      initial={reduzir ? { opacity: 0 } : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduzir ? 0.18 : 0.42, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}
