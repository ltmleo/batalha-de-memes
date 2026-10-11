"use client";

import { MotionConfig } from "motion/react";

/**
 * Aplica a preferência de movimento do usuário a todos os componentes `motion`:
 * com `reducedMotion="user"` o Framer Motion remove transformações/animações de
 * layout e mantém apenas fades (Tier 3) quando o SO pede menos movimento.
 */
export function MotionProvider({ children }: { children: React.ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
