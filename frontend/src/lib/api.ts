import type { ChatResponse, ExecuteResult, SkillMetadata } from "@/types/api"

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error((err as { detail?: string }).detail ?? res.statusText)
  }
  return res.json() as Promise<T>
}

export async function listSkills(): Promise<SkillMetadata[]> {
  return fetchApi<SkillMetadata[]>("/api/skills")
}

export interface UploadSkillOptions {
  sourceHint?: string
  originUrl?: string
}

export interface ImportFromUrlOptions {
  sourceHint?: string
}

export async function importSkillFromUrl(
  url: string,
  options?: ImportFromUrlOptions
): Promise<SkillMetadata> {
  return fetchApi<SkillMetadata>("/api/skills/import-from-url", {
    method: "POST",
    body: JSON.stringify({
      url: url.trim(),
      source_hint: options?.sourceHint?.trim() || undefined,
    }),
  })
}

export async function uploadSkill(
  file: File,
  options?: UploadSkillOptions
): Promise<SkillMetadata> {
  const form = new FormData()
  form.append("file", file)
  if (options?.sourceHint?.trim()) form.append("source_hint", options.sourceHint.trim())
  if (options?.originUrl?.trim()) form.append("origin_url", options.originUrl.trim())
  const res = await fetch(`${API_BASE}/api/skills/upload`, {
    method: "POST",
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error((err as { detail?: string }).detail ?? res.statusText)
  }
  return res.json() as Promise<SkillMetadata>
}

export async function chat(
  skillName: string,
  messages: { role: string; content: string }[]
): Promise<ChatResponse> {
  return fetchApi<ChatResponse>(`/api/chat`, {
    method: "POST",
    body: JSON.stringify({ skill_name: skillName, messages }),
  })
}

export async function execute(
  skillName: string,
  parameters: Record<string, unknown>,
  options?: { executionMode?: "sdk_only" | "auto" }
): Promise<ExecuteResult> {
  const execution_mode =
    options?.executionMode === "sdk_only" ? "sdk_only" : undefined
  return fetchApi<ExecuteResult>(`/api/execute`, {
    method: "POST",
    body: JSON.stringify({
      skill_name: skillName,
      parameters,
      ...(execution_mode ? { execution_mode } : {}),
    }),
  })
}
