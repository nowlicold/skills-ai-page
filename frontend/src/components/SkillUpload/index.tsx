import { useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useSkillsStore } from "@/store/useSkillsStore"
import { Upload } from "lucide-react"

export function SkillUpload() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const { uploadSkill, error } = useSkillsStore()

  const handleFile = async (file: File | null) => {
    if (!file) return
    if (!file.name.endsWith(".md") && !file.name.endsWith("SKILL.md")) {
      return
    }
    await uploadSkill(file)
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
      <CardContent className="space-y-2">
        <input
          ref={inputRef}
          type="file"
          accept=".md"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
        />
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
