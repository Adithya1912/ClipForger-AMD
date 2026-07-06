import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/terms")({
  component: InfoPage,
});

function InfoPage() {
  return (
    <main className="px-6 pb-24 md:px-12">
      <section className="mx-auto max-w-3xl pt-12">
        <h1 className="text-display text-5xl font-extrabold">Use permitted clips.</h1>
        <p className="mt-4 text-muted-foreground">Caption Lab is intended for the fixed hackathon clip set or video content you have permission to process.</p>
      </section>
    </main>
  );
}
