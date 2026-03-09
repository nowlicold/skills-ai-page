import { useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Chat } from "@/components/Chat"
import { DynamicParamForm } from "@/components/DynamicParamForm"
import { ArrowLeft } from "lucide-react"
import { useSkillsStore } from "@/store/useSkillsStore"
import { useChatStore } from "@/store/useChatStore"

export function ChatPage() {
  const { skillName: paramName } = useParams<{ skillName: string }>()
  const navigate = useNavigate()
  const { skills, fetchSkills } = useSkillsStore()
  const { setSkill, skillName, executeWithParams, loading } = useChatStore()
  const name = paramName ? decodeURIComponent(paramName) : null
  const currentSkill = skills.find((s) => s.name === (skillName ?? name))

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

  const handleFormSubmit = (values: Record<string, unknown>) => {
    const prompt =
      (values.prompt as string)?.trim() ||
      (values.query as string)?.trim() ||
      Object.values(values)
        .filter((v) => v != null && String(v).trim() !== "")
        .join(" ")
    executeWithParams({ ...values, prompt: prompt || " " })
  }

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
      <main className="flex min-h-0 flex-1 flex-col">
        {currentSkill?.description && (
          <section className="shrink-0 border-b px-4 py-3">
            <p className="text-sm text-muted-foreground">{currentSkill.description}</p>
          </section>
        )}
        {currentSkill?.parameters && currentSkill.parameters.length > 0 && (
          <section className="shrink-0 border-b px-4 py-3">
            <h2 className="mb-2 text-xs font-medium text-muted-foreground">
              填写参数
            </h2>
            <DynamicParamForm
              parameters={currentSkill.parameters}
              onSubmit={handleFormSubmit}
              loading={loading}
            />
          </section>
        )}
        <section className="flex min-h-0 flex-1 flex-col">
          <Chat />
        </section>
      </main>
    </div>
  )
}
