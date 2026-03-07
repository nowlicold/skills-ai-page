import { cn } from "@/lib/utils"

interface ProgressBarProps {
  progress?: number
  status?: "running" | "success" | "error"
  className?: string
}

export function ProgressBar({
  progress = 0,
  status = "running",
  className,
}: ProgressBarProps) {
  return (
    <div className={cn("space-y-2", className)}>
      <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className="h-full rounded-full bg-primary transition-all duration-300"
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>
      <p className="text-sm text-muted-foreground">
        {status === "running" && "进行中…"}
        {status === "success" && "完成"}
        {status === "error" && "失败"}
      </p>
    </div>
  )
}
