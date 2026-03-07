import { SkillList } from "@/components/SkillList"
import { SkillUpload } from "@/components/SkillUpload"

export function Home() {
  return (
    <div className="container mx-auto max-w-4xl space-y-8 px-4 py-8">
      <header>
        <h1 className="text-2xl font-semibold">Skills 使用平台</h1>
        <p className="text-muted-foreground">
          上传 SKILL.md 或从列表中选择一个 skill，通过对话使用
        </p>
      </header>
      <section>
        <h2 className="mb-4 text-lg font-medium">上传新 Skill</h2>
        <SkillUpload />
      </section>
      <section>
        <h2 className="mb-4 text-lg font-medium">已有 Skills</h2>
        <SkillList />
      </section>
    </div>
  )
}
