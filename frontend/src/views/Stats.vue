<template>
  <div class="stats">
    <h2>统计信息</h2>

    <el-row :gutter="20">
      <!-- Token使用趋势 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>Token使用趋势</span>
              <el-select v-model="tokenDays" size="small" @change="loadTokenStats">
                <el-option :value="7" label="最近7天" />
                <el-option :value="30" label="最近30天" />
                <el-option :value="90" label="最近90天" />
              </el-select>
            </div>
          </template>
          <div ref="tokenChartRef" class="chart-container"></div>
          <div class="token-summary">
            <span>总计: {{ tokenStats.total_tokens?.toLocaleString() || 0 }} tokens</span>
            <span>调用: {{ tokenStats.total_calls || 0 }} 次</span>
          </div>
        </el-card>
      </el-col>

      <!-- 工作类型分布 -->
      <el-col :span="12">
        <el-card>
          <template #header>工作类型分布</template>
          <div ref="typeChartRef" class="chart-container"></div>
          <div class="type-summary">
            总计: {{ workTypeStats.total_journals || 0 }} 条日志
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 每日工作时长 -->
    <el-card class="daily-card">
      <template #header>今日详细统计</template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="日期">{{ dailyStats.date }}</el-descriptions-item>
        <el-descriptions-item label="工作时长">{{ formatDuration(dailyStats.work_duration || 0) }}</el-descriptions-item>
        <el-descriptions-item label="会话数">{{ dailyStats.sessions || 0 }}</el-descriptions-item>
        <el-descriptions-item label="活动总数">{{ dailyStats.activities?.total || 0 }}</el-descriptions-item>
        <el-descriptions-item label="Git提交">{{ dailyStats.activities?.git_commits || 0 }}</el-descriptions-item>
        <el-descriptions-item label="文件变更">{{ dailyStats.activities?.file_changes || 0 }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { statsApi } from '../api/client'

const tokenDays = ref(7)
const tokenStats = ref({})
const workTypeStats = ref({})
const dailyStats = ref({})
const tokenChartRef = ref(null)
const typeChartRef = ref(null)

let tokenChart = null
let typeChart = null

const formatDuration = (seconds) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) return `${hours}小时${minutes}分钟`
  return `${minutes}分钟`
}

const loadTokenStats = async () => {
  try {
    const { data } = await statsApi.tokens(tokenDays.value)
    tokenStats.value = data
    renderTokenChart(data)
  } catch (e) {
    console.error('加载Token统计失败:', e)
  }
}

const loadWorkTypeStats = async () => {
  try {
    const { data } = await statsApi.workTypes(30)
    workTypeStats.value = data
    renderTypeChart(data)
  } catch (e) {
    console.error('加载工作类型统计失败:', e)
  }
}

const loadDailyStats = async () => {
  try {
    const { data } = await statsApi.daily()
    dailyStats.value = data
  } catch (e) {
    console.error('加载每日统计失败:', e)
  }
}

const renderTokenChart = (data) => {
  if (!tokenChartRef.value) return
  if (!tokenChart) {
    tokenChart = echarts.init(tokenChartRef.value)
  }

  const dates = Object.keys(data.daily_usage || {}).sort()
  const tokens = dates.map(d => data.daily_usage[d].tokens)

  tokenChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', name: 'Tokens' },
    series: [{
      type: 'bar',
      data: tokens,
      itemStyle: { color: '#409eff' },
    }],
    grid: { left: 60, right: 20, top: 30, bottom: 30 },
  })
}

const renderTypeChart = (data) => {
  if (!typeChartRef.value) return
  if (!typeChart) {
    typeChart = echarts.init(typeChartRef.value)
  }

  const dist = data.distribution || {}
  const chartData = Object.entries(dist).map(([name, value]) => ({ name, value }))

  typeChart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: chartData,
      label: { formatter: '{b}: {c} ({d}%)' },
    }],
  })
}

onMounted(async () => {
  await nextTick()
  loadTokenStats()
  loadWorkTypeStats()
  loadDailyStats()
})
</script>

<style scoped>
.stats h2 { margin-top: 0; }
.chart-container { height: 300px; }
.token-summary, .type-summary { text-align: center; color: #909399; font-size: 13px; padding: 8px 0; display: flex; justify-content: center; gap: 20px; }
.daily-card { margin-top: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
