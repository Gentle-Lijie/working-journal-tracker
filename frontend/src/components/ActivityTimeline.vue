<template>
  <div class="activity-timeline">
    <el-timeline v-if="activities.length > 0">
      <el-timeline-item
        v-for="activity in activities"
        :key="activity.id"
        :timestamp="formatTime(activity.timestamp)"
        placement="top"
      >
        <el-tag :type="activityTypeColor(activity.activity_type)" size="small">
          {{ activityTypeLabel(activity.activity_type) }}
        </el-tag>
        <span class="activity-desc">{{ activity.description }}</span>
      </el-timeline-item>
    </el-timeline>
    <el-empty v-else description="暂无活动记录" />
  </div>
</template>

<script setup>
import { defineProps } from 'vue'

defineProps({
  activities: {
    type: Array,
    default: () => [],
  },
})

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const activityTypeLabel = (type) => {
  const labels = {
    git_commit: 'Git提交',
    file_create: '创建文件',
    file_modify: '修改文件',
    file_delete: '删除文件',
  }
  return labels[type] || type
}

const activityTypeColor = (type) => {
  const colors = {
    git_commit: 'success',
    file_create: 'primary',
    file_modify: 'warning',
    file_delete: 'danger',
  }
  return colors[type] || ''
}
</script>

<style scoped>
.activity-timeline {
  max-height: 400px;
  overflow-y: auto;
}
.activity-desc {
  margin-left: 8px;
  color: #606266;
}
</style>
