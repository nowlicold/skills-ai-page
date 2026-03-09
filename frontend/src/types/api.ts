export interface UiConfig {
  type: "chat"
  supports_progress?: boolean
  output_types?: ("text" | "markdown" | "url")[]
}

/** 用于动态表单：每个参数的 schema */
export interface ParameterSchema {
  name: string
  type: "string" | "number" | "url" | "youtube_video_id"
  label?: string
  placeholder?: string
  required?: boolean
  description?: string
  /** 默认值，用于表单初始值 */
  default?: string | number
  /** 最大长度（可选） */
  max_length?: number
}

export interface SkillMetadata {
  name: string
  description: string
  created_at: string
  author?: string
  ui_config: UiConfig
  /** 可选，用于动态生成填写表单 */
  parameters?: ParameterSchema[]
  /** 可选，该 skill 依赖的环境变量名（如 FELO_API_KEY），供部署方配置参考 */
  required_env?: string[]
}

/** 单次执行结果，用于在消息中展示 DynamicUI */
export interface ExecutionResultPayload {
  status: "success" | "error" | "running"
  content?: string
  url?: string
  progress?: number
  error?: string
  result_format?: string
  result_data?: Record<string, unknown>
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
  result_format?: string
  result_data?: Record<string, unknown>
}
