import { useEffect, useState } from "react";

export function CursorGlow() {
  const [pos, setPos] = useState({ x: -500, y: -500 });
  useEffect(() => {
    const handler = (e: MouseEvent) => setPos({ x: e.clientX, y: e.clientY });
    window.addEventListener("mousemove", handler);
    return () => window.removeEventListener("mousemove", handler);
  }, []);
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 z-0"
      style={{
        background: `radial-gradient(520px circle at ${pos.x}px ${pos.y}px, color-mix(in oklab, var(--neon) 28%, transparent) 0%, color-mix(in oklab, var(--neon) 14%, transparent) 36%, transparent 68%)`,
        transition: "background 80ms linear",
      }}
    />
  );
}
