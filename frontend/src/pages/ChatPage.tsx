import { useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Chat } from "@/components/Chat"
import { ArrowLeft } from "lucide-react"
import { useSkillsStore } from "@/store/useSkillsStore"
import { useChatStore } from "@/store/useChatStore"

export function ChatPage() {
  const { skillName: paramName } = useParams<{ skillName: string }>()
  const navigate = useNavigate()
  const { skills, fetchSkills } = useSkillsStore()
  const { setSkill, skillName } = useChatStore()
  const name = paramName ? decodeURIComponent(paramName) : null

  useEffect(() => {
    if (!name) return
    if (skillName === name) return
    const sync = () => {
      const found = useSkillsStore.getState().skills.find((s) => s.name === name)
      setSkill(name, found?.description ?? "")
    }
    if (skills.length === 0) {
      fetchSkills().then(sync)
    } else {
      sync()
    }
  }, [name, skillName, setSkill, fetchSkills, skills.length])

  return (
    <div className="flex h-screen flex-col">
      <header className="flex shrink-0 items-center gap-2 border-b px-4 py-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate("/")}
          aria-label="返回"
        >
          <ArrowLeft className="size-4" />
        </Button>
        <h1 className="truncate text-lg font-medium">
          {skillName ? decodeURIComponent(skillName) : "对话"}
        </h1>
      </header>
      <main className="min-h-0 flex-1">
        <Chat />
      </main>
    </div>
  )
}
