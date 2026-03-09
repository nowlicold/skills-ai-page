import { useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useSkillsStore } from "@/store/useSkillsStore"
import { Link2, Upload } from "lucide-react"

const SOURCE_OPTIONS = [
  { value: "", label: "自动识别" },
  { value: "cursor", label: "Cursor" },
  { value: "github", label: "GitHub" },
]

export function SkillUpload() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [sourceHint, setSourceHint] = useState("")
  const [originUrl, setOriginUrl] = useState("")
  const [importing, setImporting] = useState(false)
  const { uploadSkill, importFromUrl, error } = useSkillsStore()

  const handleFile = async (file: File | null) => {
    if (!file) return
    if (!file.name.endsWith(".md") && !file.name.endsWith("SKILL.md")) {
      return
    }
    await uploadSkill(file, {
      sourceHint: sourceHint || undefined,
      originUrl: originUrl.trim() || undefined,
    })
    if (inputRef.current) inputRef.current.value = ""
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(true)
  }

  const onDragLeave = () => setDragging(false)

  const handleImportFromUrl = async () => {
    const url = originUrl.trim()
    if (!url) return
    setImporting(true)
    try {
      await importFromUrl(url, { sourceHint: sourceHint || undefined })
      setOriginUrl("")
    } finally {
      setImporting(false)
    }
  }

  return (
    <Card
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      className={dragging ? "border-primary bg-muted/50" : ""}
    >
      <CardHeader>
        <CardTitle>上传 Skill</CardTitle>
        <CardDescription>
          上传 Claude Code 标准的 SKILL.md 文件，平台将分析并加入列表
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <input
          ref={inputRef}
          type="file"
          accept=".md"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
        />
        <div className="grid gap-2">
          <label className="text-sm font-medium">来源（可选）</label>
          <select
            value={sourceHint}
            onChange={(e) => setSourceHint(e.target.value)}
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
          >
            {SOURCE_OPTIONS.map((o) => (
              <option key={o.value || "auto"} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-medium">来源 URL（可选）</label>
          <div className="flex gap-2">
            <Input
              placeholder="如 https://github.com/xxx/xxx/blob/main/SKILL.md"
              value={originUrl}
              onChange={(e) => setOriginUrl(e.target.value)}
            />
            <Button
              type="button"
              variant="secondary"
              onClick={handleImportFromUrl}
              disabled={!originUrl.trim() || importing}
            >
              {importing ? "导入中…" : "从链接导入"}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            粘贴 .md 链接后点「从链接导入」，无需选择本地文件
          </p>
        </div>
        <Button
          variant="outline"
          className="w-full"
          onClick={() => inputRef.current?.click()}
        >
          <Upload className="mr-2 size-4" />
          选择 SKILL.md
        </Button>
        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}
      </CardContent>
    </Card>
  )
}
