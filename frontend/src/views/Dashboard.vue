<template>
  <div class="dashboard">
    <h2>仪表盘</h2>

    <!-- 今日概览卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>今日工作时长</template>
          <div class="stat-value">{{ formatDuration(stats.work_duration || 0) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>工作会话</template>
          <div class="stat-value">{{ stats.sessions || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>Git提交</template>
          <div class="stat-value">{{ stats.activities?.git_commits || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>文件变更</template>
          <div class="stat-value">{{ stats.activities?.file_changes || 0 }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近活动：左右布局 -->
    <el-row :gutter="20" class="activity-section">
      <!-- 左侧：Git提交（实时读取） -->
      <el-col :span="12">
        <el-card class="section-card">
          <template #header>
            <div class="card-header">
              <span>Git 提交记录</span>
              <el-button type="primary" text @click="loadGitLog">刷新</el-button>
            </div>
          </template>
          <div class="activity-list">
            <el-empty v-if="gitCommits.length === 0" description="暂无Git提交" />
            <div v-else v-for="commit in gitCommits" :key="commit.hash" class="git-item">
              <div class="git-header">
                <el-tag type="success" size="small">{{ commit.hash }}</el-tag>
                <span class="activity-time">{{ formatTime(commit.timestamp) }}</span>
              </div>
              <div class="git-message">{{ commit.message }}</div>
              <div class="git-meta">
                <span>{{ commit.author }}</span>
                <span>
                  <span class="git-stat-add">+{{ commit.stats.insertions }}</span>
                  <span class="git-stat-del">-{{ commit.stats.deletions }}</span>
                  <span>{{ commit.stats.files }}个文件</span>
                </span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：文件变更（watch记录） -->
      <el-col :span="12">
        <el-card class="section-card">
          <template #header>
            <div class="card-header">
              <span>文件变更监控</span>
              <el-button type="primary" text @click="loadFileActivities">刷新</el-button>
            </div>
          </template>
          <div class="activity-list">
            <el-empty v-if="fileActivities.length === 0" description="暂无文件变更" />
            <el-timeline v-else>
              <el-timeline-item
                v-for="activity in fileActivities"
                :key="activity.id"
                :timestamp="formatTime(activity.timestamp)"
                placement="top"
              >
                <el-tag :type="fileTypeColor(activity.activity_type)" size="small">
                  {{ fileTypeLabel(activity.activity_type) }}
                </el-tag>
                <span class="activity-desc">{{ activity.description }}</span>
              </el-timeline-item>
            </el-timeline>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近日志 -->
    <el-card class="section-card">
      <template #header>最近日志</template>
      <el-empty v-if="journals.length === 0" description="暂无日志条目" />
      <div v-else>
        <el-card
          v-for="journal in journals"
          :key="journal.id"
          shadow="never"
          class="journal-item"
        >
          <div class="journal-header">
            <div>
              <el-tag :type="workTypeColor(journal.work_type)" size="large">
                {{ journal.work_type }}
              </el-tag>
              <span class="journal-id">#{{ journal.id }}</span>
            </div>
            <span class="journal-time">
              {{ journal.start_time }} ~ {{ journal.end_time }}
            </span>
          </div>
          <div class="journal-content">
            <div class="journal-summary" v-html="renderMarkdown(journal.summary)"></div>
            <div class="journal-meta">
              <span v-if="journal.ai_model">模型: {{ journal.ai_model }}</span>
              <span v-if="journal.tokens_used">Tokens: {{ journal.tokens_used }}</span>
            </div>
          </div>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import { statsApi, activityApi, journalApi, gitApi } from '../api/client'
import { useProjectStore } from '../stores/project'

const md = new MarkdownIt()
const renderMarkdown = (text) => text ? md.render(text) : ''
const projectStore = useProjectStore()

const stats = ref({})
const gitCommits = ref([])
const fileActivities = ref([])
const journals = ref([])

const formatDuration = (seconds) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) return `${hours}小时${minutes}分钟`
  return `${minutes}分钟`
}

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const workTypeColor = (type) => {
  const colors = { '开发': 'primary', '会议': 'warning', '调研': 'info', '测试': 'success', '文档': '', '其他': 'danger' }
  return colors[type] || ''
}

const fileTypeLabel = (type) => {
  const labels = { file_create: '创建文件', file_modify: '修改文件', file_delete: '删除文件' }
  return labels[type] || type
}

const fileTypeColor = (type) => {
  const colors = { file_create: 'primary', file_modify: 'warning', file_delete: 'danger' }
  return colors[type] || ''
}

const loadStats = async () => {
  try {
    const { data } = await statsApi.daily(undefined, projectStore.currentProjectId)
    stats.value = data
  } catch (e) {
    console.error('加载统计失败:', e)
  }
}

const loadGitLog = async () => {
  try {
    const params = { limit: 15 }
    if (projectStore.currentProjectId != null) params.project_id = projectStore.currentProjectId
    const { data } = await gitApi.log(params)
    gitCommits.value = data
  } catch (e) {
    console.error('加载Git日志失败:', e)
    gitCommits.value = []
  }
}

const loadFileActivities = async () => {
  try {
    const params = { limit: 20 }
    if (projectStore.currentProjectId != null) params.project_id = projectStore.currentProjectId
    const { data } = await activityApi.list(params)
    fileActivities.value = data.filter(a =>
      ['file_create', 'file_modify', 'file_delete'].includes(a.activity_type)
    )
  } catch (e) {
    console.error('加载文件活动失败:', e)
    fileActivities.value = []
  }
}

const loadJournals = async () => {
  try {
    const params = { limit: 5 }
    if (projectStore.currentProjectId != null) params.project_id = projectStore.currentProjectId
    const { data } = await journalApi.list(params)
    journals.value = data
  } catch (e) {
    console.error('加载日志失败:', e)
  }
}

const loadAll = () => {
  loadStats()
  loadGitLog()
  loadFileActivities()
  loadJournals()
}

watch(() => projectStore.currentProjectId, loadAll)

onMounted(loadAll)
</script>

<style scoped>
.dashboard h2 { margin-top: 0; }
.stat-cards { margin-bottom: 20px; }
.stat-value { font-size: 28px; font-weight: bold; color: #409eff; text-align: center; padding: 10px 0; }
.section-card { margin-bottom: 20px; }
.activity-section { margin-bottom: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }

/* 活动列表 */
.activity-list { max-height: 450px; overflow-y: auto; }
.activity-desc { margin-left: 8px; color: #606266; }
.activity-time { color: #909399; font-size: 12px; }

/* Git 提交项 */
.git-item { padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
.git-item:last-child { border-bottom: none; }
.git-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.git-message { color: #303133; margin-bottom: 4px; line-height: 1.5; }
.git-meta { display: flex; justify-content: space-between; color: #909399; font-size: 12px; }
.git-stat-add { color: #67c23a; margin-right: 6px; }
.git-stat-del { color: #f56c6c; margin-right: 6px; }

/* 日志样式（与Journals页面统一） */
.journal-item { margin-bottom: 16px; }
.journal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.journal-id { margin-left: 8px; color: #909399; font-size: 13px; }
.journal-time { color: #909399; font-size: 13px; }
.journal-summary { margin: 0 0 12px 0; line-height: 1.8; }
.journal-summary :deep(h1),
.journal-summary :deep(h2),
.journal-summary :deep(h3) { margin: 8px 0 4px; font-size: 1em; }
.journal-summary :deep(p) { margin: 4px 0; }
.journal-summary :deep(ul),
.journal-summary :deep(ol) { margin: 4px 0; padding-left: 20px; }
.journal-summary :deep(code) { background: #f5f5f5; padding: 2px 4px; border-radius: 3px; font-size: 0.9em; }
.journal-summary :deep(pre) { background: #f5f5f5; padding: 12px; border-radius: 4px; overflow-x: auto; }
.journal-summary :deep(pre code) { background: none; padding: 0; }
.journal-meta { display: flex; gap: 16px; color: #909399; font-size: 12px; }
</style>
