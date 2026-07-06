import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/upload-policy")({
  component: InfoPage,
});

function InfoPage() {
  return (
    <main className="px-6 pb-24 md:px-12">
      <section className="mx-auto max-w-3xl pt-12">
        <h1 className="text-display text-5xl font-extrabold">Short clips only.</h1>
        <p className="mt-4 text-muted-foreground">The backend can enforce the Track 2 duration window, but local duration limits are configurable in the backend environment file.</p>
      </section>
    </main>
  );
}
