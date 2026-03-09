import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { ParameterSchema } from "@/types/api"
import { cn } from "@/lib/utils"

export interface DynamicParamFormProps {
  parameters: ParameterSchema[]
  onSubmit: (values: Record<string, unknown>) => void
  loading?: boolean
  className?: string
}

export function DynamicParamForm({
  parameters,
  onSubmit,
  loading = false,
  className,
}: DynamicParamFormProps) {
  const [values, setValues] = useState<Record<string, unknown>>(() => {
    const init: Record<string, unknown> = {}
    for (const p of parameters) {
      init[p.name] = ""
    }
    return init
  })

  const handleChange = (name: string, value: unknown) => {
    setValues((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const out: Record<string, unknown> = {}
    for (const p of parameters) {
      const v = values[p.name]
      if (v !== undefined && v !== null && String(v).trim() !== "") {
        out[p.name] = typeof v === "number" ? v : String(v).trim()
      }
    }
    onSubmit(out)
  }

  if (parameters.length === 0) return null

  return (
    <form
      onSubmit={handleSubmit}
      className={cn("space-y-4", className)}
    >
      {parameters.map((p) => (
        <div key={p.name} className="space-y-1.5">
          <label
            htmlFor={`param-${p.name}`}
            className="text-sm font-medium leading-none"
          >
            {p.label ?? p.name}
            {p.required && <span className="text-destructive"> *</span>}
          </label>
          {p.description && (
            <p className="text-xs text-muted-foreground">{p.description}</p>
          )}
          <Input
            id={`param-${p.name}`}
            type={p.type === "number" ? "number" : p.type === "url" ? "url" : "text"}
            placeholder={
              p.placeholder ??
              (p.type === "youtube_video_id"
                ? "YouTube 链接或 11 位视频 ID"
                : undefined)
            }
            required={p.required ?? false}
            value={(values[p.name] as string) ?? ""}
            onChange={(e) => {
              const v = p.type === "number" ? e.target.valueAsNumber : e.target.value
              handleChange(p.name, v)
            }}
            className="w-full"
          />
        </div>
      ))}
      <Button type="submit" disabled={loading}>
        {loading ? "执行中…" : "执行"}
      </Button>
    </form>
  )
}
