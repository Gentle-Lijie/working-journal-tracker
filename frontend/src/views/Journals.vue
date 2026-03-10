<template>
  <div class="journals">
    <h2>工作日志</h2>

    <!-- 筛选器 -->
    <el-card class="filter-card">
      <el-form :inline="true">
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="工作类型">
          <el-select v-model="workType" placeholder="全部" clearable>
            <el-option label="开发" value="开发" />
            <el-option label="会议" value="会议" />
            <el-option label="调研" value="调研" />
            <el-option label="测试" value="测试" />
            <el-option label="文档" value="文档" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadJournals">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 日志列表 -->
    <el-card v-loading="loading">
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
            <p class="journal-summary">{{ journal.summary }}</p>
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
import { ref, onMounted } from 'vue'
import { journalApi } from '../api/client'

const dateRange = ref([])
const workType = ref('')
const journals = ref([])
const loading = ref(false)

const workTypeColor = (type) => {
  const colors = { '开发': 'primary', '会议': 'warning', '调研': 'info', '测试': 'success', '文档': '', '其他': 'danger' }
  return colors[type] || ''
}

const loadJournals = async () => {
  loading.value = true
  try {
    const params = {}
    if (dateRange.value && dateRange.value.length === 2) {
      params.from = dateRange.value[0]
      params.to = dateRange.value[1]
    }
    if (workType.value) {
      params.work_type = workType.value
    }
    const { data } = await journalApi.list(params)
    journals.value = data
  } catch (e) {
    console.error('加载日志失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadJournals()
})
</script>

<style scoped>
.journals h2 { margin-top: 0; }
.filter-card { margin-bottom: 20px; }
.journal-item { margin-bottom: 16px; }
.journal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.journal-id { margin-left: 8px; color: #909399; font-size: 13px; }
.journal-time { color: #909399; font-size: 13px; }
.journal-summary { margin: 0 0 12px 0; line-height: 1.8; white-space: pre-wrap; }
.journal-meta { display: flex; gap: 16px; color: #909399; font-size: 12px; }
</style>
