import { cn } from "@/lib/utils"

interface SourceItem {
  title?: string
  url?: string
}

interface SourcesOutputProps {
  answer?: string
  sources: SourceItem[]
  className?: string
}

export function SourcesOutput({
  answer,
  sources,
  className,
}: SourcesOutputProps) {
  return (
    <div className={cn("space-y-3", className)}>
      {answer && (
        <div className="rounded-md border bg-muted/30 p-3 text-sm">
          {answer}
        </div>
      )}
      {sources.length > 0 && (
        <div className="space-y-1">
          <h4 className="text-xs font-medium text-muted-foreground">
            参考来源
          </h4>
          <ul className="space-y-1">
            {sources.map((s, i) => (
              <li key={i}>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary underline underline-offset-2 hover:opacity-80"
                >
                  {s.title || s.url || "链接"}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
