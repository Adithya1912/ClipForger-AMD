import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/pricing")({
  component: InfoPage,
});

function InfoPage() {
  return (
    <main className="px-6 pb-24 md:px-12">
      <section className="mx-auto max-w-3xl pt-12">
        <p className="font-mono text-xs uppercase tracking-[0.28em] text-muted-foreground">Hackathon build</p>
        <h1 className="text-display mt-4 text-5xl font-extrabold">Fireworks credits only.</h1>
        <p className="mt-4 text-muted-foreground">This submission has no billing surface. The demo is designed around the Track 2 Fireworks AI API compute requirement.</p>
      </section>
    </main>
  );
}
