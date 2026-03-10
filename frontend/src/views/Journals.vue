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
          <el-button type="success" @click="showGenerateDialog = true">手动生成日志</el-button>
          <el-dropdown @command="handleExport" style="margin-left: 12px;">
            <el-button type="info">
              导出 ▼
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="excel">导出 Excel</el-dropdown-item>
                <el-dropdown-item command="markdown">导出 Markdown</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 手动生成日志对话框 -->
    <el-dialog v-model="showGenerateDialog" title="手动生成日志" width="480px">
      <el-form label-width="80px">
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="generateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DDTHH:mm:ss"
            :shortcuts="timeShortcuts"
          />
        </el-form-item>
        <el-form-item label="会话ID">
          <el-input-number v-model="generateSessionId" :min="0" placeholder="可选" controls-position="right" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGenerateDialog = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="handleGenerate">生成</el-button>
      </template>
    </el-dialog>

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
            <div class="journal-summary markdown-body" v-html="renderMarkdown(journal.summary)"></div>
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
import { ElMessage } from 'element-plus'
import MarkdownIt from 'markdown-it'
import * as XLSX from 'xlsx'
import { journalApi } from '../api/client'
import { useProjectStore } from '../stores/project'

const md = new MarkdownIt()
const renderMarkdown = (text) => text ? md.render(text) : ''
const projectStore = useProjectStore()

const dateRange = ref([])
const workType = ref('')
const journals = ref([])
const loading = ref(false)

// 手动生成相关
const showGenerateDialog = ref(false)
const generateRange = ref([])
const generateSessionId = ref(null)
const generating = ref(false)

const timeShortcuts = [
  {
    text: '最近1小时',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setHours(start.getHours() - 1)
      return [start, end]
    },
  },
  {
    text: '最近3小时',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setHours(start.getHours() - 3)
      return [start, end]
    },
  },
  {
    text: '今天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setHours(0, 0, 0, 0)
      return [start, end]
    },
  },
]

const handleGenerate = async () => {
  if (!generateRange.value || generateRange.value.length !== 2) {
    ElMessage.warning('请选择时间范围')
    return
  }
  generating.value = true
  try {
    const { data } = await journalApi.generate({
      start_time: generateRange.value[0],
      end_time: generateRange.value[1],
      session_id: generateSessionId.value || undefined,
      project_id: projectStore.currentProjectId || undefined,
    })
    if (data.success) {
      ElMessage.success('日志生成成功')
      showGenerateDialog.value = false
      loadJournals()
    } else {
      ElMessage.warning(data.message || '生成失败')
    }
  } catch (e) {
    ElMessage.error('生成日志失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    generating.value = false
  }
}

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
    if (projectStore.currentProjectId != null) {
      params.project_id = projectStore.currentProjectId
    }
    const { data } = await journalApi.list(params)
    journals.value = data
  } catch (e) {
    console.error('加载日志失败:', e)
  } finally {
    loading.value = false
  }
}

watch(() => projectStore.currentProjectId, loadJournals)

onMounted(() => {
  loadJournals()
})

const handleExport = (format) => {
  if (journals.value.length === 0) {
    ElMessage.warning('没有可导出的日志')
    return
  }
  if (format === 'excel') exportExcel()
  else if (format === 'markdown') exportMarkdown()
}

const exportExcel = () => {
  const rows = journals.value.map(j => ({
    'ID': j.id,
    '工作类型': j.work_type,
    '开始时间': j.start_time,
    '结束时间': j.end_time,
    '摘要': j.summary,
    'AI模型': j.ai_model || '',
    'Tokens': j.tokens_used || 0,
  }))
  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '工作日志')
  XLSX.writeFile(wb, `工作日志_${new Date().toISOString().slice(0, 10)}.xlsx`)
}

const exportMarkdown = () => {
  const lines = ['# 工作日志\n']
  for (const j of journals.value) {
    lines.push(`## #${j.id} ${j.work_type}`)
    lines.push(`**时间**: ${j.start_time} ~ ${j.end_time}\n`)
    lines.push(j.summary || '')
    if (j.ai_model) lines.push(`\n> 模型: ${j.ai_model} | Tokens: ${j.tokens_used || 0}`)
    lines.push('\n---\n')
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `工作日志_${new Date().toISOString().slice(0, 10)}.md`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.journals h2 { margin-top: 0; }
.filter-card { margin-bottom: 20px; }
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
