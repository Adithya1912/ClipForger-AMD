const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export type CaptionStyle = "formal" | "sarcastic" | "humorous_tech" | "humorous_non_tech";
export type JobStatus = "queued" | "processing" | "complete" | "failed";

export type CaptionSegment = {
  start: number;
  end: number;
  text: string;
};

export type StyleOutput = {
  style: CaptionStyle;
  styled_caption: string;
  summary: string;
  tone_notes: string;
  confidence: number;
  evaluation: {
    accuracy: number;
    tone_match: number;
    hallucination_risk: "low" | "medium" | "high" | string;
    notes: string;
  };
};

export type JobResult = {
  job_id: string;
  status: JobStatus;
  progress: number;
  message: string;
  filename: string;
  video_path: string;
  duration_seconds?: number | null;
  transcript?: string | null;
  caption_track: CaptionSegment[];
  transcript_provider?: string | null;
  visual_summary?: string | null;
  visual_provider?: string | null;
  generation_provider?: string | null;
  captioned_video_path?: string | null;
  base_summary?: string | null;
  style_outputs: StyleOutput[];
  error?: string | null;
};

export class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, init);
  } catch {
    throw new ApiError("Cannot reach the Caption Lab backend. Check that it is running.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail ?? `Request failed (${response.status})`, response.status);
  }
  return (await response.json()) as T;
}

export async function uploadVideo(file: File): Promise<JobResult> {
  const formData = new FormData();
  formData.append("file", file);
  return request<JobResult>("/api/videos", { method: "POST", body: formData });
}

export async function generateCaptions(jobId: string): Promise<void> {
  await request(`/api/jobs/${encodeURIComponent(jobId)}/generate`, { method: "POST" });
}

export async function getJob(jobId: string): Promise<JobResult> {
  return request<JobResult>(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export async function getResults(jobId: string): Promise<JobResult> {
  return request<JobResult>(`/api/jobs/${encodeURIComponent(jobId)}/results`);
}

export async function listJobs(): Promise<JobResult[]> {
  return request<JobResult[]>("/api/jobs");
}

export async function updateStyleOutput(
  jobId: string,
  style: CaptionStyle,
  patch: { styled_caption?: string; summary?: string },
): Promise<JobResult> {
  return request<JobResult>(`/api/jobs/${encodeURIComponent(jobId)}/style-outputs`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ style, ...patch }),
  });
}

export function exportUrl(jobId: string, format: "submission" | "json" | "srt" | "vtt" | "txt"): string {
  return `${BASE_URL}/api/jobs/${encodeURIComponent(jobId)}/export?format=${format}`;
}

export function captionedVideoUrl(jobId: string): string {
  return `${BASE_URL}/api/jobs/${encodeURIComponent(jobId)}/captioned-video`;
}

export const STYLE_LABEL: Record<CaptionStyle, string> = {
  formal: "Formal",
  sarcastic: "Sarcastic",
  humorous_tech: "Humorous Tech",
  humorous_non_tech: "Humorous Non-Tech",
};

export const PROCESS_STEPS = [
  "Uploading video",
  "Extracting audio",
  "Building timed caption track",
  "Rendering captioned video",
  "Generating styled captions",
  "Generating formal summary",
  "Generating sarcastic summary",
  "Generating humorous-tech summary",
  "Generating humorous-non-tech summary",
];
