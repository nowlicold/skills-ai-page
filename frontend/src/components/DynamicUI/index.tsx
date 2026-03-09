import type { UiConfig } from "@/types/api"
import { LinkOutput } from "./LinkOutput"
import { ListOutput } from "./ListOutput"
import { ProgressBar } from "./ProgressBar"
import { SourcesOutput } from "./SourcesOutput"
import { SubtitlesOutput } from "./SubtitlesOutput"
import { TextOutput } from "./TextOutput"
import { WebPageOutput } from "./WebPageOutput"

interface DynamicUIProps {
  uiConfig: UiConfig
  data: {
    status?: "running" | "success" | "error"
    progress?: number
    content?: string
    url?: string
    result_format?: string
    result_data?: Record<string, unknown>
  }
}

export function DynamicUI({ uiConfig, data }: DynamicUIProps) {
  if (uiConfig.supports_progress && data.status === "running") {
    return <ProgressBar progress={data.progress} status={data.status} />
  }
  if (data.url && uiConfig.output_types?.includes("url")) {
    return <LinkOutput url={data.url} />
  }
  const format = data.result_format
  const rd = data.result_data
  if (format === "youtube_subtitles" && rd && Array.isArray(rd.subtitles)) {
    return (
      <SubtitlesOutput
        title={rd.title as string | undefined}
        subtitles={rd.subtitles as { start?: number; end?: number; text?: string }[]}
      />
    )
  }
  if (format === "answer_sources" && rd) {
    return (
      <SourcesOutput
        answer={rd.answer as string | undefined}
        sources={(rd.sources as { title?: string; url?: string }[]) ?? []}
      />
    )
  }
  if (format === "web_page" && rd) {
    return (
      <WebPageOutput
        title={rd.title as string | undefined}
        content={rd.content as string | undefined}
      />
    )
  }
  if (format === "list" && rd && Array.isArray(rd.items)) {
    return (
      <ListOutput
        items={rd.items as { title?: string; url?: string; description?: string }[]}
      />
    )
  }
  if (data.content) {
    return <TextOutput content={data.content} />
  }
  return null
}

export {
  ProgressBar,
  LinkOutput,
  TextOutput,
  SubtitlesOutput,
  SourcesOutput,
  WebPageOutput,
  ListOutput,
}
