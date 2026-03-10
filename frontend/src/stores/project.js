import { defineStore } from 'pinia'
import { ref } from 'vue'
import { projectApi } from '../api/client'

export const useProjectStore = defineStore('project', () => {
  const currentProjectId = ref(null) // null 表示全部项目
  const projectList = ref([])

  async function loadProjects() {
    try {
      const { data } = await projectApi.list()
      projectList.value = data
    } catch (e) {
      console.error('加载项目列表失败:', e)
    }
  }

  function setCurrentProject(id) {
    currentProjectId.value = id
  }

  return {
    currentProjectId,
    projectList,
    loadProjects,
    setCurrentProject,
  }
})
