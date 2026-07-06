import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { FileVideo, Sparkles, Upload } from "lucide-react";
import { useState } from "react";
import { generateCaptions, uploadVideo } from "@/lib/api/client";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "ClipForger" },
      { name: "description", content: "Generate burned-in subtitles plus four judged caption and summary styles for short videos." },
    ],
  }),
  component: UploadPage,
});

function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const job = await uploadVideo(file);
      await generateCaptions(job.job_id);
      navigate({ to: "/process/$jobId", params: { jobId: job.job_id } });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not start caption job");
      setBusy(false);
    }
  }

  function acceptFile(next?: File) {
    if (next) setFile(next);
  }

  return (
    <main className="px-6 pb-24 md:px-12">
      <section className="mx-auto max-w-6xl pt-12 md:pt-20">
        <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}>
          <p className="font-mono text-xs uppercase tracking-[0.28em] text-muted-foreground">
            Track 2 Video Captioning
          </p>
          <h1 className="text-display mt-4 max-w-4xl text-5xl font-extrabold leading-none md:text-7xl">
            Captioned video plus four styled outputs. <span className="neon-text">One short clip.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-muted-foreground">
            Upload a video, burn the transcript into the clip, and generate formal, sarcastic,
            humorous-tech, and humorous-non-tech captions and summaries.
          </p>
        </motion.div>

        <div className="mt-10 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <label
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              acceptFile(event.dataTransfer.files?.[0]);
            }}
            className={`flex min-h-80 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed bg-surface-1/70 p-8 text-center transition ${
              dragging || file ? "border-neon neon-glow" : "border-border hover:border-neon-dim"
            }`}
          >
            <input
              type="file"
              accept="video/*"
              className="hidden"
              onChange={(event) => acceptFile(event.target.files?.[0])}
            />
            <Upload className="size-10 text-neon" />
            <div className="mt-5 text-2xl font-bold">Drop the judging clip here</div>
            <div className="mt-2 text-sm text-muted-foreground">MP4, MOV, MKV. Duration limits are configurable server-side.</div>
            {file && (
              <div className="mt-5 rounded-full border border-neon-dim px-4 py-2 font-mono text-xs text-neon">
                {file.name} | {(file.size / 1_000_000).toFixed(1)} MB
              </div>
            )}
          </label>

          <div className="grid gap-4">
            {[
              ["Formal", "Neutral, precise, and judge-friendly."],
              ["Sarcastic", "Dry wit without drifting away from the clip."],
              ["Humorous Tech", "Developer-flavored jokes with factual guardrails."],
              ["Humorous Non-Tech", "Broad humor for humans who do not read stack traces."],
            ].map(([title, copy]) => (
              <div key={title} className="rounded-lg border border-border bg-surface-1/70 p-5">
                <div className="flex items-center gap-3">
                  <Sparkles className="size-4 text-neon" />
                  <div className="font-mono text-xs uppercase tracking-widest">{title}</div>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{copy}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-4">
          <button
            onClick={start}
            disabled={!file || busy}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-3 font-mono text-xs font-bold uppercase tracking-widest text-primary-foreground disabled:opacity-40"
          >
            <FileVideo className="size-4" />
            {busy ? "Starting..." : "Generate styled outputs"}
          </button>
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            Styled outputs powered by Fireworks AI
          </span>
        </div>

        {error && <div className="mt-5 rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>}
      </section>
    </main>
  );
}
