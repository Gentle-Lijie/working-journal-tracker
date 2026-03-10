<template>
  <el-container class="app-container">
    <el-header>
      <div class="header-content">
        <h1 class="logo">工作日志追踪</h1>
        <el-menu
          :default-active="activeMenu"
          mode="horizontal"
          :ellipsis="false"
          router
          class="nav-menu"
        >
          <el-menu-item index="/">仪表盘</el-menu-item>
          <el-menu-item index="/journals">工作日志</el-menu-item>
          <el-menu-item index="/projects">项目</el-menu-item>
          <el-menu-item index="/config">配置</el-menu-item>
          <el-menu-item index="/stats">统计</el-menu-item>
          <el-menu-item index="/logs">系统日志</el-menu-item>
        </el-menu>
        <div class="project-selector">
          <el-select
            v-model="currentProjectId"
            placeholder="全部项目"
            clearable
            size="default"
            @change="onProjectChange"
            style="width: 180px"
          >
            <el-option
              v-for="p in projectStore.projectList"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>
        </div>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore } from './stores/project'

const route = useRoute()
const activeMenu = computed(() => route.path)
const projectStore = useProjectStore()

const currentProjectId = computed({
  get: () => projectStore.currentProjectId,
  set: (val) => projectStore.setCurrentProject(val),
})

function onProjectChange(val) {
  projectStore.setCurrentProject(val ?? null)
}

onMounted(() => {
  projectStore.loadProjects()
})
</script>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background-color: #f5f7fa;
}

.app-container {
  min-height: 100vh;
}

.el-header {
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
}

.header-content {
  display: flex;
  align-items: center;
  height: 60px;
}

.logo {
  font-size: 18px;
  margin: 0;
  margin-right: 40px;
  color: #303133;
  white-space: nowrap;
}

.nav-menu {
  border-bottom: none !important;
  flex: 1;
}

.project-selector {
  margin-left: auto;
  flex-shrink: 0;
}

.el-main {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}
</style>
