import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/admin")({
  component: InfoPage,
});

function InfoPage() {
  return (
    <main className="px-6 pb-24 md:px-12">
      <section className="mx-auto max-w-3xl pt-12">
        <p className="font-mono text-xs uppercase tracking-[0.28em] text-muted-foreground">Architecture</p>
        <h1 className="text-display mt-4 text-5xl font-extrabold">Focused caption pipeline.</h1>
        <p className="mt-4 text-muted-foreground">FastAPI stores jobs, extracts audio with FFmpeg, builds timed captions, renders a captioned MP4, calls Fireworks AI for four summary styles, and exports JSON/SRT/VTT.</p>
      </section>
    </main>
  );
}
