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
        {error}
        <Button variant="ghost" size="sm" className="ml-2" onClick={clearError}>
          关闭
        </Button>
      </div>
    )
  }

  if (loading && skills.length === 0) {
    return <p className="text-muted-foreground">加载中…</p>
  }

  if (skills.length === 0) {
    return (
      <p className="text-muted-foreground">暂无 skills，请先上传 SKILL.md</p>
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
