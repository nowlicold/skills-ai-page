export interface UiConfig {
  type: "chat"
  supports_progress?: boolean
  output_types?: ("text" | "markdown" | "url")[]
}

export interface SkillMetadata {
  name: string
  description: string
  created_at: string
  author?: string
  ui_config: UiConfig
}

/** 单次执行结果，用于在消息中展示 DynamicUI */
export interface ExecutionResultPayload {
  status: "success" | "error" | "running"
  content?: string
  url?: string
  progress?: number
  error?: string
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  ready_to_execute?: boolean
  parameters?: Record<string, unknown>
  /** 执行接口返回的完整结果，用于按 ui_config 渲染链接/进度/文本 */
  executionResult?: ExecutionResultPayload
}

export interface ChatResponse {
  message: string
  ready_to_execute?: boolean
  parameters?: Record<string, unknown>
}

export interface ExecuteResult {
  status: "success" | "error" | "running"
  content?: string
  url?: string
  progress?: number
  error?: string
}
