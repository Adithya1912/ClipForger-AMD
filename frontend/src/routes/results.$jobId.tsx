import { createFileRoute } from "@tanstack/react-router";
import { CheckCircle2, Copy, Download, Film, Gem, Save } from "lucide-react";
import { useEffect, useState } from "react";
import {
  captionedVideoUrl,
  exportUrl,
  getResults,
  STYLE_LABEL,
  updateStyleOutput,
  type JobResult,
  type StyleOutput,
} from "@/lib/api/client";

export const Route = createFileRoute("/results/$jobId")({
  component: ResultsPage,
});

function ResultsPage() {
  const { jobId } = Route.useParams();
  const [job, setJob] = useState<JobResult | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [reviewChecks, setReviewChecks] = useState<Record<string, boolean>>({});
  const [activeTab, setActiveTab] = useState<"captions" | "summaries">("captions");
  const [saveState, setSaveState] = useState<Record<string, "idle" | "saving" | "saved" | "error">>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getResults(jobId)
      .then((next) => {
        setJob(next);
        setDrafts(
          Object.fromEntries(
            next.style_outputs.flatMap((output) => [
              [`${output.style}:caption`, output.styled_caption],
              [`${output.style}:summary`, output.summary],
            ]),
          ),
        );
      })
      .catch((caught) => setError(caught instanceof Error ? caught.message : "Could not load results"));
  }, [jobId]);

  function setDraft(key: string, value: string, style: StyleOutput["style"]) {
    setDrafts((current) => ({ ...current, [key]: value }));
    setSaveState((current) => ({ ...current, [style]: "idle" }));
  }

  async function save(style: StyleOutput["style"]) {
    setSaveState((current) => ({ ...current, [style]: "saving" }));
    try {
      const next = await updateStyleOutput(jobId, style, {
        styled_caption: drafts[`${style}:caption`],
        summary: drafts[`${style}:summary`],
      });
      setJob(next);
      setDrafts((current) => {
        const output = next.style_outputs.find((item) => item.style === style);
        if (!output) return current;
        return {
          ...current,
          [`${style}:caption`]: output.styled_caption,
          [`${style}:summary`]: output.summary,
        };
      });
      setSaveState((current) => ({ ...current, [style]: "saved" }));
    } catch (caught) {
      setSaveState((current) => ({ ...current, [style]: "error" }));
      setError(caught instanceof Error ? caught.message : "Could not save edits");
    }
  }

  const isNvidia = job?.generation_provider === "nvidia";
  const isGemma = job?.generation_provider?.includes("gemma") || job?.generation_provider === "fireworks_gemma";
  const isOpenRouter = job?.generation_provider === "openrouter";
  const isGoogle = job?.generation_provider === "google";
  const gemmaEnabled = isNvidia || isGemma || isOpenRouter || isGoogle;

  return (
    <main className="px-6 pb-24 md:px-12">
      <section className="mx-auto max-w-7xl pt-10">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.28em] text-muted-foreground">Results</p>
            <h1 className="text-display mt-4 text-5xl font-extrabold md:text-7xl">
              Captioned video <span className="neon-text">ready</span>.
            </h1>
            <p className="mt-3 flex flex-wrap items-center gap-3 max-w-2xl text-sm leading-6 text-muted-foreground">
              {job?.filename ?? "Clip"} | 4 style-specific captions
              {gemmaEnabled && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-900/40 px-3 py-0.5 font-mono text-[10px] uppercase tracking-widest text-emerald-400 border border-emerald-700/50">
                  <Gem className="size-3" />
                  {isNvidia ? "Gemma (NVIDIA)" : isGoogle ? "Google Gemini" : isOpenRouter ? "Gemma 4 (OpenRouter)" : "Powered by Gemma"}
                </span>
              )}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <a
              href={exportUrl(jobId, "submission")}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 font-mono text-xs uppercase tracking-widest text-primary-foreground"
            >
              <Download className="size-4" />
              Submission JSON
            </a>
            {(["json", "srt", "vtt", "txt"] as const).map((format) => (
              <a
                key={format}
                href={exportUrl(jobId, format)}
                className="inline-flex items-center gap-2 rounded-md border border-border px-4 py-2 font-mono text-xs uppercase tracking-widest hover:border-neon"
              >
                <Download className="size-4" />
                {format}
              </a>
            ))}
          </div>
        </div>

        {error && <div className="mt-8 rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>}

        <div className="mt-8 flex w-full rounded-md border border-border bg-surface-1 p-1">
          {(["captions", "summaries"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 rounded px-4 py-3 text-center font-mono text-sm uppercase tracking-widest ${
                activeTab === tab ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {job && (
          <section className="mt-6 rounded-lg border border-border bg-surface-1/70 p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="size-4 text-neon" />
                  <div className="font-mono text-xs uppercase tracking-widest text-neon">Export readiness</div>
                </div>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Review captions, tone, and exports before recording the demo or submitting leaderboard outputs.
                </p>
              </div>
              <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                {Object.values(reviewChecks).filter(Boolean).length}/4 checked
              </div>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-4">
              {[
                ["captions", "Captions reviewed"],
                ["summaries", "Four styles reviewed"],
                ["tone", "Tone and accuracy checked"],
                ["exports", "Submission JSON ready"],
              ].map(([id, label]) => (
                <label
                  key={id}
                  className="flex min-h-14 cursor-pointer items-center gap-3 rounded-md border border-border bg-background/60 px-3 py-2 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={Boolean(reviewChecks[id])}
                    onChange={(event) => setReviewChecks((current) => ({ ...current, [id]: event.target.checked }))}
                    className="size-4 accent-primary"
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </section>
        )}

        {activeTab === "captions" && (
          <div className="mt-8 grid items-start gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="self-start rounded-lg border border-border bg-surface-1/80 p-4">
              {job?.captioned_video_path ? (
                <>
                  <video src={captionedVideoUrl(jobId)} controls className="aspect-video w-full rounded-md bg-black" />
                  <div className="mt-4 flex justify-center">
                    <a
                      href={captionedVideoUrl(jobId)}
                      download
                      className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 font-mono text-xs uppercase tracking-widest text-primary-foreground"
                    >
                      <Download className="size-4" />
                      Download video
                    </a>
                  </div>
                </>
              ) : (
                <div className="flex aspect-video w-full items-center justify-center rounded-md border border-border bg-background/60 text-sm text-muted-foreground">
                  Captioned video will appear here when FFmpeg rendering succeeds.
                </div>
              )}

              {job?.base_summary && (
                <div className="mt-5 rounded-lg border border-border bg-background/55 p-5">
                  <div className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Factual base</div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{job.base_summary}</p>
                  <div className="mt-3 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                    Gemma-first routing | 7 keyframes for visual context | 4 style-specific LLM calls | timed caption track | four judged style outputs
                  </div>
                  <div className="mt-1 font-mono text-[10px] uppercase tracking-widest text-muted-foreground/70">
                    Provider diagnostics are preserved in JSON export.
                  </div>
                  {job.visual_summary && <p className="mt-3 text-xs leading-5 text-muted-foreground">Visual: {job.visual_summary}</p>}
                </div>
              )}
            </div>

            <div className="self-start rounded-lg border border-border bg-surface-1/80 p-5">
              <div className="flex items-center gap-3">
                <Film className="size-4 text-neon" />
                <div className="font-mono text-xs uppercase tracking-widest text-neon">Timed caption track</div>
              </div>
              <div className="mt-4 max-h-[710px] space-y-3 overflow-auto pr-2">
                {job?.caption_track.length ? (
                  job.caption_track.map((segment, index) => (
                    <div key={`${segment.start}-${index}`} className="rounded-md border border-border bg-background/60 p-3">
                      <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                        {formatTime(segment.start)} - {formatTime(segment.end)}
                      </div>
                      <p className="mt-2 text-sm leading-6">{segment.text}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm leading-6 text-muted-foreground">No timed captions are available for this clip yet.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === "summaries" && (
          <div className="mt-8 grid gap-5 md:grid-cols-2">
            {job?.style_outputs.map((output) => {
              const captionDraft = drafts[`${output.style}:caption`] ?? output.styled_caption;
              const summaryDraft = drafts[`${output.style}:summary`] ?? output.summary;
              const isDirty = captionDraft !== output.styled_caption || summaryDraft !== output.summary;
              const currentSaveState = saveState[output.style] ?? "idle";

              return (
              <article key={output.style} className="rounded-lg border border-border bg-surface-1/80 p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="font-mono text-xs uppercase tracking-widest text-neon">{STYLE_LABEL[output.style]}</div>
                    <div className="mt-2 text-xs text-muted-foreground">{output.tone_notes}</div>
                  </div>
                  <div className="text-right font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                    Accuracy {Math.round(output.evaluation.accuracy * 100)}%
                    <br />
                    Tone {Math.round(output.evaluation.tone_match * 100)}%
                  </div>
                </div>
                <div className="mt-5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Styled Caption</div>
                <textarea
                  value={captionDraft}
                  onChange={(event) => setDraft(`${output.style}:caption`, event.target.value, output.style)}
                  className="mt-2 min-h-28 w-full resize-y rounded-md border border-border bg-background p-3 text-sm leading-6 outline-none focus:border-neon"
                />
                <div className="mt-5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Summary</div>
                <textarea
                  value={summaryDraft}
                  onChange={(event) => setDraft(`${output.style}:summary`, event.target.value, output.style)}
                  className="mt-2 min-h-44 w-full resize-y rounded-md border border-border bg-background p-3 text-sm leading-6 outline-none focus:border-neon"
                />
                <div className="mt-4 rounded-md border border-border bg-background/60 p-3 text-xs leading-5 text-muted-foreground">
                  Risk: {output.evaluation.hallucination_risk}. {output.evaluation.notes}
                </div>
                <div className="mt-4 flex gap-2">
                  <button
                    type="button"
                    onClick={() => navigator.clipboard?.writeText(`${captionDraft}\n\n${summaryDraft}`)}
                    className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 font-mono text-xs uppercase tracking-widest hover:border-neon"
                  >
                    <Copy className="size-4" />
                    Copy
                  </button>
                  <button
                    type="button"
                    onClick={() => save(output.style)}
                    disabled={currentSaveState === "saving" || !isDirty}
                    className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 font-mono text-xs uppercase tracking-widest text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Save className="size-4" />
                    {currentSaveState === "saving" ? "Saving" : currentSaveState === "saved" && !isDirty ? "Saved" : "Save"}
                  </button>
                  {isDirty && <span className="self-center font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Unsaved edits</span>}
                  {currentSaveState === "error" && <span className="self-center font-mono text-[10px] uppercase tracking-widest text-destructive">Save failed</span>}
                </div>
              </article>
              );
            })}
          </div>
        )}

        {!job && !error && <div className="mt-10 font-mono text-sm text-muted-foreground">Loading results...</div>}
      </section>
    </main>
  );
}

function formatTime(value: number): string {
  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60);
  return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
}
