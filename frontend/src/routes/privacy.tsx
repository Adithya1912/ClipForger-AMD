import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/privacy")({
  component: InfoPage,
});

function InfoPage() {
  return (
    <main className="px-6 pb-24 md:px-12">
      <section className="mx-auto max-w-3xl pt-12">
        <h1 className="text-display text-5xl font-extrabold">Local demo storage.</h1>
        <p className="mt-4 text-muted-foreground">Uploaded clips and generated caption jobs are stored in the configured backend storage directory for the demo run.</p>
      </section>
    </main>
  );
}
