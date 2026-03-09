import { create } from "zustand"
import type { ChatMessage } from "@/types/api"
import * as api from "@/lib/api"

interface ChatState {
  skillName: string | null
  skillDescription: string
  messages: ChatMessage[]
  loading: boolean
  error: string | null
  lastExecuteParams: Record<string, unknown> | null
  setSkill: (name: string, description: string) => void
  sendMessage: (content: string) => Promise<void>
  executeWithParams: (params: Record<string, unknown>) => Promise<void>
  retryExecute: () => Promise<void>
  reset: () => void
  clearError: () => void
}

const createId = () => Math.random().toString(36).slice(2)

export const useChatStore = create<ChatState>((set, get) => ({
  skillName: null,
  skillDescription: "",
  messages: [],
  loading: false,
  error: null,
  lastExecuteParams: null,

  setSkill: (name, description) => {
    set({
      skillName: name,
      skillDescription: description,
      messages: [
        {
          id: createId(),
          role: "assistant",
          content: `这个 skill 可以帮你 ${description}，你想做什么？`,
        },
      ],
      error: null,
    })
  },

  sendMessage: async (content: string) => {
    const { skillName, messages } = get()
    if (!skillName) return
    set((s) => ({
      messages: [
        ...s.messages,
        { id: createId(), role: "user", content },
      ],
      loading: true,
      error: null,
    }))
    try {
      const history = [
        ...messages,
        { id: createId(), role: "user" as const, content },
      ]
      const res = await api.chat(
        skillName,
        history.map((m) => ({ role: m.role, content: m.content }))
      )
      set((s) => ({
        messages: [
          ...s.messages,
          {
            id: createId(),
            role: "assistant",
            content: res.message,
            ready_to_execute: res.ready_to_execute,
            parameters: res.parameters,
          },
        ],
        loading: false,
      }))
      if (res.ready_to_execute && res.parameters) {
        await get().executeWithParams(res.parameters)
      }
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "发送失败",
        loading: false,
      })
    }
  },

  executeWithParams: async (params: Record<string, unknown>) => {
    const { skillName } = get()
    if (!skillName) return
    set((s) => ({
      messages: [
        ...s.messages,
        {
          id: createId(),
          role: "assistant",
          content: "正在执行…",
        },
      ],
      loading: true,
      lastExecuteParams: params,
    }))
    try {
      const result = await api.execute(skillName, params)
      const content =
        result.status === "success"
          ? result.content ?? (result.url ? `[点击查看](${result.url})` : "完成")
          : result.error ?? "执行失败"
      const executionResult = {
        status: result.status,
        content: result.content,
        url: result.url,
        progress: result.progress,
        error: result.error,
        result_format: result.result_format,
        result_data: result.result_data,
      }
      set((s) => {
        const next = [...s.messages]
        const last = next[next.length - 1]
        if (last?.content === "正在执行…") {
          next[next.length - 1] = { ...last, content, executionResult }
        } else {
          next.push({
            id: createId(),
            role: "assistant",
            content,
            executionResult,
          })
        }
        return { messages: next, loading: false }
      })
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : "执行失败"
      set((s) => {
        const next = [...s.messages]
        const last = next[next.length - 1]
        if (last?.content === "正在执行…") {
          next[next.length - 1] = {
            ...last,
            content: errMsg,
            executionResult: { status: "error", error: errMsg },
          }
        } else {
          next.push({
            id: createId(),
            role: "assistant",
            content: errMsg,
            executionResult: { status: "error", error: errMsg },
          })
        }
        return { messages: next, loading: false }
      })
    }
  },

  retryExecute: async () => {
    const { lastExecuteParams, skillName } = get()
    if (!skillName || !lastExecuteParams) return
    set({ error: null })
    await get().executeWithParams(lastExecuteParams)
  },

  reset: () =>
    set({
      skillName: null,
      skillDescription: "",
      messages: [],
      loading: false,
      error: null,
      lastExecuteParams: null,
    }),

  clearError: () => set({ error: null }),
}))
