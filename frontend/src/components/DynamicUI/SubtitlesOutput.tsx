import { cn } from "@/lib/utils"

interface SubtitleSegment {
  start?: number
  end?: number
  text?: string
}

interface SubtitlesOutputProps {
  title?: string
  subtitles: SubtitleSegment[]
  className?: string
}

export function SubtitlesOutput({
  title,
  subtitles,
  className,
}: SubtitlesOutputProps) {
  return (
    <div className={cn("space-y-3", className)}>
      {title && (
        <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
      )}
      <div className="max-h-64 space-y-1 overflow-y-auto rounded-md border bg-muted/30 p-3 text-sm">
        {subtitles.length === 0 ? (
          <p className="text-muted-foreground">暂无字幕</p>
        ) : (
          subtitles.map((seg, i) => (
            <div key={i} className="flex gap-2">
              {(seg.start != null || seg.end != null) && (
                <span className="shrink-0 text-xs text-muted-foreground">
                  {seg.start != null && seg.end != null
                    ? `${formatTime(seg.start)} - ${formatTime(seg.end)}`
                    : seg.start != null
                      ? formatTime(seg.start)
                      : ""}
                </span>
              )}
              <span className="min-w-0 flex-1">{seg.text ?? ""}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, "0")}`
}
