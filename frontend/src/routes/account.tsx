import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/account")({
  component: InfoPage,
});

function InfoPage() {
  return (
    <main className="px-6 pb-24 md:px-12">
      <section className="mx-auto max-w-3xl pt-12">
        <p className="font-mono text-xs uppercase tracking-[0.28em] text-muted-foreground">Caption Lab</p>
        <h1 className="text-display mt-4 text-5xl font-extrabold">No account required.</h1>
        <p className="mt-4 text-muted-foreground">This hackathon build keeps the workflow local-first: upload, render captions, edit summaries, and export.</p>
      </section>
    </main>
  );
}
