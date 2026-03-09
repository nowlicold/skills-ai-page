import { cn } from "@/lib/utils"

interface ListItem {
  title?: string
  url?: string
  description?: string
}

interface ListOutputProps {
  items: ListItem[]
  className?: string
}

export function ListOutput({ items, className }: ListOutputProps) {
  if (items.length === 0) {
    return (
      <p className={cn("text-muted-foreground text-sm", className)}>暂无条目</p>
    )
  }
  return (
    <ul className={cn("space-y-2", className)}>
      {items.map((item, i) => (
        <li key={i} className="flex flex-col gap-0.5">
          {item.url ? (
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline underline-offset-2 hover:opacity-80"
            >
              {item.title || item.url || "链接"}
            </a>
          ) : (
            <span>{item.title || "（无标题）"}</span>
          )}
          {item.description && (
            <span className="text-muted-foreground text-xs">
              {item.description}
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}
