<template>
  <div class="logs">
    <h2>系统日志</h2>

    <!-- 筛选栏 -->
    <el-card class="filter-card">
      <el-form :inline="true">
        <el-form-item label="级别">
          <el-select v-model="level" placeholder="全部" clearable style="width: 120px" @change="loadLogs">
            <el-option label="INFO" value="INFO" />
            <el-option label="WARNING" value="WARNING" />
            <el-option label="ERROR" value="ERROR" />
            <el-option label="DEBUG" value="DEBUG" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="keyword" placeholder="搜索日志内容" clearable style="width: 200px" @keyup.enter="loadLogs" />
        </el-form-item>
        <el-form-item label="行数">
          <el-input-number v-model="lines" :min="50" :max="2000" :step="50" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadLogs">查询</el-button>
          <el-button :type="autoRefresh ? 'danger' : 'success'" @click="toggleAutoRefresh">
            {{ autoRefresh ? '停止刷新' : '自动刷新' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 日志统计 -->
    <el-row :gutter="12" class="log-stats">
      <el-col :span="6">
        <el-tag type="info" size="large">总计: {{ logEntries.length }}</el-tag>
      </el-col>
      <el-col :span="6">
        <el-tag type="success" size="large">INFO: {{ countByLevel('INFO') }}</el-tag>
      </el-col>
      <el-col :span="6">
        <el-tag type="warning" size="large">WARNING: {{ countByLevel('WARNING') }}</el-tag>
      </el-col>
      <el-col :span="6">
        <el-tag type="danger" size="large">ERROR: {{ countByLevel('ERROR') }}</el-tag>
      </el-col>
    </el-row>

    <!-- 日志列表 -->
    <el-card v-loading="loading">
      <el-empty v-if="logEntries.length === 0" description="暂无日志" />
      <el-table
        v-else
        :data="logEntries"
        stripe
        style="width: 100%"
        max-height="600"
        :row-class-name="rowClassName"
        size="small"
      >
        <el-table-column prop="timestamp" label="时间" width="170" />
        <el-table-column prop="level" label="级别" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="levelColor(row.level)" size="small">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="200" show-overflow-tooltip />
        <el-table-column prop="location" label="位置" width="180" show-overflow-tooltip />
        <el-table-column prop="message" label="消息" min-width="300" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { logApi } from '../api/client'

const loading = ref(false)
const logEntries = ref([])
const level = ref('')
const keyword = ref('')
const lines = ref(200)
const autoRefresh = ref(false)
let refreshTimer = null

const levelColor = (lv) => {
  const map = { INFO: 'success', WARNING: 'warning', ERROR: 'danger', DEBUG: 'info' }
  return map[lv] || 'info'
}

const rowClassName = ({ row }) => {
  if (row.level === 'ERROR') return 'log-row-error'
  if (row.level === 'WARNING') return 'log-row-warning'
  return ''
}

const countByLevel = (lv) => logEntries.value.filter(e => e.level === lv).length

const loadLogs = async () => {
  loading.value = true
  try {
    const params = { lines: lines.value }
    if (level.value) params.level = level.value
    if (keyword.value) params.keyword = keyword.value
    const { data } = await logApi.list(params)
    logEntries.value = (data.logs || []).reverse()
  } catch (e) {
    console.error('加载日志失败:', e)
  } finally {
    loading.value = false
  }
}

const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    refreshTimer = setInterval(loadLogs, 5000)
  } else {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

onMounted(loadLogs)

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.logs h2 { margin-top: 0; }
.filter-card { margin-bottom: 16px; }
.log-stats { margin-bottom: 16px; }
</style>

<style>
.log-row-error { background-color: #fef0f0 !important; }
.log-row-warning { background-color: #fdf6ec !important; }
</style>
