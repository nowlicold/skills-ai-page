import { cn } from "@/lib/utils"
import { TextOutput } from "./TextOutput"

interface WebPageOutputProps {
  title?: string
  content?: string
  className?: string
}

export function WebPageOutput({
  title,
  content,
  className,
}: WebPageOutputProps) {
  const hasContent = (content ?? "").trim().length > 0
  return (
    <div className={cn("space-y-2", className)}>
      {title && (
        <h3 className="text-sm font-semibold leading-tight">{title}</h3>
      )}
      {hasContent && <TextOutput content={content!} />}
      {!title && !hasContent && (
        <p className="text-muted-foreground text-sm">无内容</p>
      )}
    </div>
  )
}
