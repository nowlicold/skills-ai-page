import { create } from "zustand"
import type { SkillMetadata } from "@/types/api"
import * as api from "@/lib/api"

interface SkillsState {
  skills: SkillMetadata[]
  loading: boolean
  error: string | null
  fetchSkills: () => Promise<void>
  uploadSkill: (file: File, options?: { sourceHint?: string; originUrl?: string }) => Promise<SkillMetadata | null>
  importFromUrl: (url: string, options?: { sourceHint?: string }) => Promise<SkillMetadata | null>
  clearError: () => void
}

export const useSkillsStore = create<SkillsState>((set) => ({
  skills: [],
  loading: false,
  error: null,

  fetchSkills: async () => {
    set({ loading: true, error: null })
    try {
      const skills = await api.listSkills()
      set({ skills, loading: false })
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "加载失败",
        loading: false,
      })
    }
  },

  uploadSkill: async (file: File, options?: { sourceHint?: string; originUrl?: string }) => {
    set({ error: null })
    try {
      const skill = await api.uploadSkill(file, options)
      set((s) => ({ skills: [skill, ...s.skills] }))
      return skill
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "上传失败",
      })
      return null
    }
  },

  importFromUrl: async (url: string, options?: { sourceHint?: string }) => {
    set({ error: null })
    try {
      const skill = await api.importSkillFromUrl(url, options)
      set((s) => ({ skills: [skill, ...s.skills] }))
      return skill
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "从链接导入失败",
      })
      return null
    }
  },

  clearError: () => set({ error: null }),
}))
