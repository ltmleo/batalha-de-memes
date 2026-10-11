"use client";

import { motion, useReducedMotion } from "motion/react";

/**
 * Revela o conteúdo quando ele entra na viewport (scroll reveal). Respeita
 * `prefers-reduced-motion` (apenas fade). Um IntersectionObserver por elemento —
 * use em blocos, não em listas gigantes.
 */
export function Reveal({
  children,
  delay = 0,
  y = 16,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  y?: number;
  className?: string;
}) {
  const reduzir = useReducedMotion();

  return (
    <motion.div
      className={className}
      initial={reduzir ? { opacity: 0 } : { opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "0px 0px -10% 0px" }}
      transition={{
        duration: reduzir ? 0.18 : 0.5,
        delay: reduzir ? 0 : delay,
        ease: [0.16, 1, 0.3, 1],
      }}
    >
      {children}
    </motion.div>
  );
}
