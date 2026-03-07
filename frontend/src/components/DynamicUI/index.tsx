import type { UiConfig } from "@/types/api"
import { LinkOutput } from "./LinkOutput"
import { ProgressBar } from "./ProgressBar"
import { TextOutput } from "./TextOutput"

interface DynamicUIProps {
  uiConfig: UiConfig
  data: {
    status?: "running" | "success" | "error"
    progress?: number
    content?: string
    url?: string
  }
}

export function DynamicUI({ uiConfig, data }: DynamicUIProps) {
  if (uiConfig.supports_progress && data.status === "running") {
    return <ProgressBar progress={data.progress} status={data.status} />
  }
  if (data.url && uiConfig.output_types?.includes("url")) {
    return <LinkOutput url={data.url} />
  }
  if (data.content) {
    return <TextOutput content={data.content} />
  }
  return null
}

export { ProgressBar, LinkOutput, TextOutput }
