import { useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { DynamicUI, TextOutput } from "@/components/DynamicUI"
import { useChatStore } from "@/store/useChatStore"
import { useSkillsStore } from "@/store/useSkillsStore"
import { Send } from "lucide-react"
import { cn } from "@/lib/utils"
import type { UiConfig } from "@/types/api"

const DEFAULT_UI_CONFIG: UiConfig = {
  type: "chat",
  supports_progress: false,
  output_types: ["text", "markdown"],
}

export function Chat() {
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const {
    skillName,
    messages,
    loading,
    error,
    sendMessage,
    clearError,
  } = useChatStore()
  const { skills } = useSkillsStore()
  const uiConfig = skillName
    ? (skills.find((s) => s.name === skillName)?.ui_config ?? DEFAULT_UI_CONFIG)
    : DEFAULT_UI_CONFIG

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const value = inputRef.current?.value?.trim()
    if (!value || loading) return
    inputRef.current!.value = ""
    sendMessage(value)
  }

  if (!skillName) {
    return (
      <p className="text-muted-foreground">请从首页选择一个 skill 使用</p>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1 px-4">
        <div className="space-y-6 py-4">
          {messages.map((m) => (
            <div
              key={m.id}
              className={cn(
                "flex",
                m.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              <div
                className={cn(
                  "max-w-[85%] rounded-lg px-4 py-2",
                  m.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                )}
              >
                {m.role === "assistant" ? (
                  m.executionResult ? (
                    <DynamicUI
                      uiConfig={uiConfig}
                      data={{
                        status: m.executionResult.status,
                        progress: m.executionResult.progress,
                        content: m.executionResult.content ?? m.content,
                        url: m.executionResult.url,
                        result_format: m.executionResult.result_format,
                        result_data: m.executionResult.result_data,
                      }}
                    />
                  ) : (
                    <TextOutput content={m.content} />
                  )
                ) : (
                  <p className="whitespace-pre-wrap">{m.content}</p>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="rounded-lg bg-muted px-4 py-2 text-muted-foreground">
                思考中…
              </div>
            </div>
          )}
        </div>
        <div ref={bottomRef} />
      </ScrollArea>

      {error && (
        <div className="border-t px-4 py-2 text-sm text-destructive">
          {error}
          <Button variant="ghost" size="sm" onClick={clearError}>
            关闭
          </Button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex gap-2 border-t p-4">
        <Input
          ref={inputRef}
          placeholder="输入消息…"
          disabled={loading}
          className="flex-1"
        />
        <Button type="submit" size="icon" disabled={loading}>
          <Send className="size-4" />
        </Button>
      </form>
    </div>
  )
}
