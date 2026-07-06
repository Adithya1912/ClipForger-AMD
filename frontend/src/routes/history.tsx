import { Link, createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { listJobs, type JobResult } from "@/lib/api/client";

export const Route = createFileRoute("/history")({
  component: HistoryPage,
});

function HistoryPage() {
  const [jobs, setJobs] = useState<JobResult[]>([]);

  useEffect(() => {
    listJobs().then(setJobs).catch(() => setJobs([]));
  }, []);

  return (
    <main className="px-6 pb-24 md:px-12">
      <section className="mx-auto max-w-5xl pt-10">
        <p className="font-mono text-xs uppercase tracking-[0.28em] text-muted-foreground">Caption jobs</p>
        <h1 className="text-display mt-4 text-5xl font-extrabold md:text-7xl">Recent runs.</h1>
        <div className="mt-8 space-y-3">
          {jobs.map((job) => (
            <Link
              key={job.job_id}
              to="/results/$jobId"
              params={{ jobId: job.job_id }}
              className="flex items-center justify-between rounded-lg border border-border bg-surface-1/70 p-4 hover:border-neon"
            >
              <div>
                <div className="font-semibold">{job.filename}</div>
                <div className="mt-1 font-mono text-xs uppercase tracking-widest text-muted-foreground">{job.message}</div>
              </div>
              <div className="font-mono text-xs uppercase tracking-widest text-neon">{job.status}</div>
            </Link>
          ))}
        </div>
        {jobs.length === 0 && <div className="mt-10 text-sm text-muted-foreground">No caption jobs yet.</div>}
      </section>
    </main>
  );
}
