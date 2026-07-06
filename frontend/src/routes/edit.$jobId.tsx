import { Link, createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/edit/$jobId")({
  component: EditRedirect,
});

function EditRedirect() {
  const { jobId } = Route.useParams();
  return (
    <main className="px-6 pb-24 md:px-12">
      <section className="mx-auto max-w-3xl pt-12">
        <p className="font-mono text-xs uppercase tracking-[0.28em] text-muted-foreground">Caption editing moved</p>
        <h1 className="text-display mt-4 text-5xl font-extrabold">Edit on the results cards.</h1>
        <Link to="/results/$jobId" params={{ jobId }} className="mt-6 inline-flex rounded-md bg-primary px-4 py-2 text-primary-foreground">
          Open results
        </Link>
      </section>
    </main>
  );
}
