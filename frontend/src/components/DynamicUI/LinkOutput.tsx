import { cn } from "@/lib/utils"

interface LinkOutputProps {
  url: string
  label?: string
  className?: string
}

export function LinkOutput({ url, label, className }: LinkOutputProps) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "inline-flex items-center gap-2 text-primary underline underline-offset-4 hover:opacity-80",
        className
      )}
    >
      {label ?? url}
    </a>
  )
}
