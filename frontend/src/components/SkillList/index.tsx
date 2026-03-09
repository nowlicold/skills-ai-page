import { useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  CardAction,
} from "@/components/ui/card"
import { useSkillsStore } from "@/store/useSkillsStore"
import { useChatStore } from "@/store/useChatStore"
import type { SkillMetadata } from "@/types/api"

function SkillCard({
  skill,
  onUse,
}: {
  skill: SkillMetadata
  onUse: () => void
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{skill.name}</CardTitle>
        <CardDescription>{skill.description}</CardDescription>
        <CardAction>
          <Button size="sm" onClick={onUse}>
            使用这个 skill
          </Button>
        </CardAction>
      </CardHeader>
    </Card>
  )
}

export function SkillList() {
  const navigate = useNavigate()
  const { skills, loading, error, fetchSkills, clearError } = useSkillsStore()
  const { setSkill } = useChatStore()

  useEffect(() => {
    fetchSkills()
  }, [fetchSkills])

  const handleUse = (skill: SkillMetadata) => {
    setSkill(skill.name, skill.description)
    navigate(`/chat/${encodeURIComponent(skill.name)}`)
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
        <span>{error}</span>
        <div className="mt-2 flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchSkills}>
            重试
          </Button>
          <Button variant="ghost" size="sm" onClick={clearError}>
            关闭
          </Button>
        </div>
      </div>
    )
  }

  if (loading && skills.length === 0) {
    return <p className="text-muted-foreground">加载中…</p>
  }

  if (skills.length === 0) {
    return (
      <div className="rounded-lg border border-dashed bg-muted/30 px-4 py-8 text-center text-muted-foreground">
        <p className="font-medium">暂无 skill</p>
        <p className="mt-1 text-sm">请先上传 SKILL.md 或从链接导入</p>
      </div>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {skills.map((skill) => (
        <SkillCard key={skill.name} skill={skill} onUse={() => handleUse(skill)} />
      ))}
    </div>
  )
}
