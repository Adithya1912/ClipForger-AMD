import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { getJob, PROCESS_STEPS, type JobResult } from "@/lib/api/client";

export const Route = createFileRoute("/process/$jobId")({
  component: ProcessPage,
});

function ProcessPage() {
  const { jobId } = Route.useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState<JobResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const next = await getJob(jobId);
        if (cancelled) return;
        setJob(next);
        if (next.status === "complete") {
          setTimeout(() => !cancelled && navigate({ to: "/results/$jobId", params: { jobId } }), 700);
          return;
        }
        if (next.status === "failed") {
          setError(next.error ?? next.message);
          return;
        }
        setTimeout(poll, 1500);
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : "Could not read job status");
      }
    }
    poll();
    return () => {
      cancelled = true;
    };
  }, [jobId, navigate]);

  const progress = job?.progress ?? 8;
  const activeIndex = Math.min(PROCESS_STEPS.length - 1, Math.floor((progress / 100) * PROCESS_STEPS.length));

  return (
    <main className="px-6 pb-24 md:px-12">
      <section className="mx-auto max-w-5xl pt-12">
        <p className="font-mono text-xs uppercase tracking-[0.28em] text-muted-foreground">Caption pipeline</p>
        <h1 className="text-display mt-4 text-5xl font-extrabold md:text-7xl">
          Forging <span className="neon-text">styled outputs</span>.
        </h1>
        <div className="mt-8 h-2 overflow-hidden rounded-full bg-surface-3">
          <motion.div className="h-full bg-neon" animate={{ width: `${progress}%` }} />
        </div>
        <div className="mt-3 font-mono text-xs uppercase tracking-widest text-muted-foreground">
          {progress}% | {job?.message ?? "Starting caption workflow"}
        </div>
        {error && <div className="mt-5 rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>}
        <div className="mt-10 grid gap-3 md:grid-cols-2">
          {PROCESS_STEPS.map((step, index) => (
            <div
              key={step}
              className={`rounded-lg border p-4 font-mono text-xs uppercase tracking-widest ${
                index < activeIndex
                  ? "border-neon/40 bg-neon/10 text-neon"
                  : index === activeIndex
                    ? "border-neon bg-surface-1 text-foreground"
                    : "border-border bg-surface-1/70 text-muted-foreground"
              }`}
            >
              {step}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
