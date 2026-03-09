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

function validateOne(
  p: ParameterSchema,
  value: unknown
): string | null {
  const raw = value === undefined || value === null ? "" : String(value).trim()
  if (p.required && !raw) {
    return `${p.label ?? p.name}为必填`
  }
  if (!raw) return null
  const type = p.type ?? "string"
  const maxLength = p.max_length
  if (typeof maxLength === "number" && raw.length > maxLength) {
    return `${p.label ?? p.name}长度不能超过 ${maxLength}`
  }
  if (type === "number") {
    if (Number.isNaN(Number(raw))) return `${p.label ?? p.name}应为数字`
    return null
  }
  if (type === "url") {
    if (!raw.startsWith("http://") && !raw.startsWith("https://")) {
      return `${p.label ?? p.name}应为有效 URL`
    }
    return null
  }
  if (type === "youtube_video_id") {
    const is11 = /^[a-zA-Z0-9_-]{11}$/.test(raw)
    const isLink = /youtube\.com|youtu\.be/.test(raw)
    if (!is11 && !isLink) return `${p.label ?? p.name}应为 YouTube 视频 ID 或链接`
    return null
  }
  return null
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
      const def = p.default
      init[p.name] =
        def !== undefined && def !== null
          ? def
          : ""
    }
    return init
  })
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const handleChange = (name: string, value: unknown) => {
    setValues((prev) => ({ ...prev, [name]: value }))
    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const next = { ...prev }
        delete next[name]
        return next
      })
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const errors: Record<string, string> = {}
    for (const p of parameters) {
      const err = validateOne(p, values[p.name])
      if (err) errors[p.name] = err
    }
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    const out: Record<string, unknown> = {}
    for (const p of parameters) {
      const v = values[p.name]
      if (v !== undefined && v !== null && String(v).trim() !== "") {
        out[p.name] = p.type === "number" ? Number(v) : String(v).trim()
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
      {Object.keys(fieldErrors).length > 0 && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {Object.values(fieldErrors).join("；")}
        </div>
      )}
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
            value={(values[p.name] as string | number) ?? ""}
            onChange={(e) => {
              const v = p.type === "number" ? e.target.valueAsNumber : e.target.value
              handleChange(p.name, v)
            }}
            className={cn(
              "w-full",
              fieldErrors[p.name] && "border-destructive focus-visible:ring-destructive"
            )}
            aria-invalid={!!fieldErrors[p.name]}
            aria-describedby={fieldErrors[p.name] ? `param-${p.name}-error` : undefined}
          />
          {fieldErrors[p.name] && (
            <p
              id={`param-${p.name}-error`}
              className="text-xs text-destructive"
              role="alert"
            >
              {fieldErrors[p.name]}
            </p>
          )}
        </div>
      ))}
      <Button type="submit" disabled={loading}>
        {loading ? "执行中…" : "执行"}
      </Button>
    </form>
  )
}
