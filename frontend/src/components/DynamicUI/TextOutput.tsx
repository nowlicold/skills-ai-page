import ReactMarkdown from "react-markdown"
import { cn } from "@/lib/utils"

interface TextOutputProps {
  content: string
  className?: string
}

export function TextOutput({ content, className }: TextOutputProps) {
  return (
    <div
      className={cn(
        "prose prose-sm dark:prose-invert max-w-none break-words",
        className
      )}
    >
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  )
}
