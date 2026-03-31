<template>
  <div class="debug-page">
    <el-card class="page-header">
      <template #header>
        <div class="header-content">
          <h2>组件调试</h2>
          <el-alert
            type="info"
            :closable="false"
            show-icon
            style="margin-top: 10px"
          >
            此页面用于按需启动/停止追踪器的各个组件，便于定位内存泄漏问题。每个组件作为独立进程运行。
          </el-alert>
        </div>
      </template>

      <!-- 项目选择 -->
      <div class="project-select">
        <span class="label">选择项目：</span>
        <el-select
          v-model="selectedProjectId"
          placeholder="请选择项目"
          style="width: 300px"
          @change="onProjectChange"
        >
          <el-option
            v-for="p in projectStore.projectList"
            :key="p.id"
            :label="p.name"
            :value="p.id"
          />
        </el-select>

        <el-button
          type="primary"
          :disabled="!selectedProjectId"
          @click="loadComponentStatus"
          style="margin-left: 10px"
        >
          刷新状态
        </el-button>

        <el-button-group style="margin-left: 20px">
          <el-button
            type="success"
            :disabled="!selectedProjectId"
            :loading="batchLoading"
            @click="startAllComponents"
          >
            启动全部
          </el-button>
          <el-button
            type="danger"
            :disabled="!selectedProjectId"
            :loading="batchLoading"
            @click="stopAllComponents"
          >
            停止全部
          </el-button>
        </el-button-group>
      </div>
    </el-card>

    <!-- 组件状态卡片 -->
    <div class="components-grid" v-if="selectedProjectId">
      <el-card
        v-for="comp in components"
        :key="comp.key"
        class="component-card"
        :class="{ running: componentStatus[comp.key]?.running }"
      >
        <template #header>
          <div class="card-header">
            <span class="title">{{ comp.name }}</span>
            <el-tag
              :type="componentStatus[comp.key]?.running ? 'success' : 'info'"
              size="small"
            >
              {{ componentStatus[comp.key]?.running ? '运行中' : '已停止' }}
            </el-tag>
          </div>
        </template>

        <div class="component-info">
          <p class="description">{{ comp.description }}</p>
          <p class="pid" v-if="componentStatus[comp.key]?.pid">
            PID: <code>{{ componentStatus[comp.key].pid }}</code>
          </p>
          <p class="pid" v-else>
            <el-text type="info">进程未运行</el-text>
          </p>
        </div>

        <div class="actions">
          <el-button
            type="success"
            size="small"
            :disabled="componentStatus[comp.key]?.running"
            :loading="loadingMap[comp.key]"
            @click="startComponent(comp.key)"
          >
            启动
          </el-button>
          <el-button
            type="danger"
            size="small"
            :disabled="!componentStatus[comp.key]?.running"
            :loading="loadingMap[comp.key]"
            @click="stopComponent(comp.key)"
          >
            停止
          </el-button>
          <el-button
            type="warning"
            size="small"
            :disabled="!componentStatus[comp.key]?.running"
            :loading="loadingMap[comp.key]"
            @click="restartComponent(comp.key)"
          >
            重启
          </el-button>
        </div>

        <div class="debug-tips">
          <el-text size="small" type="info">
            {{ comp.debugTip }}
          </el-text>
        </div>
      </el-card>
    </div>

    <!-- 未选择项目提示 -->
    <el-empty v-else description="请先选择一个项目" />

    <!-- 调试说明 -->
    <el-card class="debug-help" v-if="selectedProjectId">
      <template #header>
        <h3>调试说明</h3>
      </template>
      <ol class="help-list">
        <li>选择要调试的项目</li>
        <li>单独启动某个组件（如 Git 监控）</li>
        <li>检查 PID 文件：
          <code>cat ~/.work-journal/tracker-{{ selectedProjectId }}-[component].pid</code>
        </li>
        <li>观察进程内存：
          <code>top -pid $(cat ~/.work-journal/tracker-{{ selectedProjectId }}-[component].pid)</code>
        </li>
        <li>查看组件日志：
          <code>tail -f ~/.work-journal/component-{{ selectedProjectId }}-[component].log</code>
        </li>
        <li>依次测试各组件，定位内存泄漏来源</li>
      </ol>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useProjectStore } from '../stores/project'
import { componentApi } from '../api/client'

const projectStore = useProjectStore()

const selectedProjectId = ref(null)
const componentStatus = reactive({
  git: { running: false, pid: null },
  file: { running: false, pid: null },
  journal: { running: false, pid: null },
})
const loadingMap = reactive({
  git: false,
  file: false,
  journal: false,
})
const batchLoading = ref(false)

const components = [
  {
    key: 'git',
    name: 'Git 监控',
    description: '监控 Git 仓库的提交活动，记录每次提交的信息和变更文件。',
    debugTip: 'GitPython 可能存在内存泄漏，可通过定期重建 Repo 对象缓解',
  },
  {
    key: 'file',
    name: '文件监控',
    description: '监控项目目录的文件变更（创建、修改、删除），批量记录到数据库。',
    debugTip: 'watchfiles 库自动合并事件，内存占用较低',
  },
  {
    key: 'journal',
    name: '日志生成器',
    description: '整点自动生成工作日志，汇总过去一小时的活动记录。',
    debugTip: '调用 AI 接口生成日志，主要关注 AI 服务调用的内存情况',
  },
]

function onProjectChange(projectId) {
  if (projectId) {
    loadComponentStatus()
  }
}

async function loadComponentStatus() {
  if (!selectedProjectId.value) return

  try {
    const { data } = await componentApi.getStatus(selectedProjectId.value)
    Object.keys(data).forEach(key => {
      componentStatus[key] = data[key]
    })
  } catch (error) {
    ElMessage.error('获取组件状态失败: ' + (error.response?.data?.detail || error.message))
  }
}

async function startComponent(component) {
  loadingMap[component] = true
  try {
    await componentApi.start(selectedProjectId.value, component)
    ElMessage.success(`${component} 组件已启动`)
    await loadComponentStatus()
  } catch (error) {
    ElMessage.error('启动失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loadingMap[component] = false
  }
}

async function stopComponent(component) {
  loadingMap[component] = true
  try {
    await componentApi.stop(selectedProjectId.value, component)
    ElMessage.success(`${component} 组件已停止`)
    await loadComponentStatus()
  } catch (error) {
    ElMessage.error('停止失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loadingMap[component] = false
  }
}

async function restartComponent(component) {
  loadingMap[component] = true
  try {
    await componentApi.stop(selectedProjectId.value, component)
    await new Promise(resolve => setTimeout(resolve, 500))
    await componentApi.start(selectedProjectId.value, component)
    ElMessage.success(`${component} 组件已重启`)
    await loadComponentStatus()
  } catch (error) {
    ElMessage.error('重启失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loadingMap[component] = false
  }
}

async function startAllComponents() {
  batchLoading.value = true
  try {
    const { data } = await componentApi.startAll(selectedProjectId.value)
    const failed = Object.entries(data.results)
      .filter(([, r]) => !r.success)
      .map(([k, r]) => `${k}: ${r.error}`)

    if (failed.length === 0) {
      ElMessage.success('所有组件已启动')
    } else {
      ElMessage.warning('部分组件启动失败: ' + failed.join('; '))
    }
    await loadComponentStatus()
  } catch (error) {
    ElMessage.error('批量启动失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    batchLoading.value = false
  }
}

async function stopAllComponents() {
  batchLoading.value = true
  try {
    const { data } = await componentApi.stopAll(selectedProjectId.value)
    const failed = Object.entries(data.results)
      .filter(([, r]) => !r.success)
      .map(([k, r]) => `${k}: ${r.error}`)

    if (failed.length === 0) {
      ElMessage.success('所有组件已停止')
    } else {
      ElMessage.warning('部分组件停止失败: ' + failed.join('; '))
    }
    await loadComponentStatus()
  } catch (error) {
    ElMessage.error('批量停止失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    batchLoading.value = false
  }
}

onMounted(() => {
  projectStore.loadProjects()
})
</script>

<style scoped>
.debug-page {
  max-width: 1200px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header .header-content h2 {
  margin: 0;
}

.project-select {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px 0;
}

.project-select .label {
  font-weight: 500;
  margin-right: 10px;
}

.components-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.component-card {
  transition: all 0.3s;
}

.component-card.running {
  border-color: #67c23a;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header .title {
  font-weight: 600;
  font-size: 16px;
}

.component-info {
  margin-bottom: 15px;
}

.component-info .description {
  color: #606266;
  font-size: 14px;
  margin: 0 0 10px 0;
}

.component-info .pid {
  margin: 0;
  color: #909399;
  font-size: 13px;
}

.component-info .pid code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.actions {
  margin-bottom: 15px;
}

.debug-tips {
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}

.debug-help h3 {
  margin: 0;
  font-size: 16px;
}

.help-list {
  margin: 10px 0 0 0;
  padding-left: 20px;
  color: #606266;
}

.help-list li {
  margin-bottom: 8px;
}

.help-list code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
}
</style>
