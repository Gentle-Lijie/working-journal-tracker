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

    <!-- 最近活动 -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>最近活动</span>
          <el-button type="primary" text @click="loadActivities">刷新</el-button>
        </div>
      </template>
      <ActivityTimeline :activities="activities" />
    </el-card>

    <!-- 最近日志 -->
    <el-card class="section-card">
      <template #header>最近日志</template>
      <el-empty v-if="journals.length === 0" description="暂无日志条目" />
      <div v-else>
        <el-card
          v-for="journal in journals"
          :key="journal.id"
          shadow="never"
          class="journal-card"
        >
          <div class="journal-header">
            <el-tag :type="workTypeColor(journal.work_type)">{{ journal.work_type }}</el-tag>
            <span class="journal-time">
              {{ journal.start_time }} ~ {{ journal.end_time }}
            </span>
          </div>
          <p class="journal-summary">{{ journal.summary }}</p>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { statsApi, activityApi, journalApi } from '../api/client'
import ActivityTimeline from '../components/ActivityTimeline.vue'

const stats = ref({})
const activities = ref([])
const journals = ref([])

const formatDuration = (seconds) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) return `${hours}小时${minutes}分钟`
  return `${minutes}分钟`
}

const workTypeColor = (type) => {
  const colors = { '开发': 'primary', '会议': 'warning', '调研': 'info', '测试': 'success', '文档': '', '其他': 'danger' }
  return colors[type] || ''
}

const loadStats = async () => {
  try {
    const { data } = await statsApi.daily()
    stats.value = data
  } catch (e) {
    console.error('加载统计失败:', e)
  }
}

const loadActivities = async () => {
  try {
    const { data } = await activityApi.list({ limit: 20 })
    activities.value = data
  } catch (e) {
    console.error('加载活动失败:', e)
  }
}

const loadJournals = async () => {
  try {
    const { data } = await journalApi.list({ limit: 5 })
    journals.value = data
  } catch (e) {
    console.error('加载日志失败:', e)
  }
}

onMounted(() => {
  loadStats()
  loadActivities()
  loadJournals()
})
</script>

<style scoped>
.dashboard h2 { margin-top: 0; }
.stat-cards { margin-bottom: 20px; }
.stat-value { font-size: 28px; font-weight: bold; color: #409eff; text-align: center; padding: 10px 0; }
.section-card { margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.journal-card { margin-bottom: 12px; }
.journal-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.journal-time { color: #909399; font-size: 13px; }
.journal-summary { margin: 0; line-height: 1.6; color: #303133; white-space: pre-wrap; }
</style>
