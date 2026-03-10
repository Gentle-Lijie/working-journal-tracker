<template>
  <el-dialog :model-value="visible" @update:model-value="$emit('update:visible', $event)" title="选择目录" width="600px">
    <!-- 当前路径 + 手动输入 -->
    <div style="display: flex; gap: 8px; margin-bottom: 12px;">
      <el-input
        v-model="manualPath"
        placeholder="输入路径后回车跳转"
        @keyup.enter="goToPath(manualPath)"
        style="flex: 1"
      />
      <el-button @click="goToPath(manualPath)">跳转</el-button>
    </div>

    <!-- 面包屑导航 -->
    <div style="margin-bottom: 8px; font-size: 13px; color: #606266;">
      <span v-for="(seg, i) in breadcrumbs" :key="i">
        <el-link type="primary" @click="goToPath(seg.path)" :underline="false">{{ seg.name }}</el-link>
        <span v-if="i < breadcrumbs.length - 1" style="margin: 0 2px;">/</span>
      </span>
      <el-tag v-if="isGit" size="small" type="success" style="margin-left: 8px;">Git 仓库</el-tag>
    </div>

    <!-- 目录列表 -->
    <div v-loading="loading" style="height: 360px; overflow-y: auto; border: 1px solid #ebeef5; border-radius: 4px;">
      <!-- 返回上级 -->
      <div
        v-if="parentPath"
        class="dir-item"
        @click="goToPath(parentPath)"
      >
        <el-icon><ArrowLeft /></el-icon>
        <span style="margin-left: 6px;">.. 返回上级</span>
      </div>
      <div v-if="dirs.length === 0 && !loading" style="padding: 40px; text-align: center; color: #909399;">
        无子目录
      </div>
      <div
        v-for="dir in dirs"
        :key="dir.path"
        class="dir-item"
        :class="{ selected: dir.path === selectedPath }"
        @click="selectedPath = dir.path"
        @dblclick="goToPath(dir.path)"
      >
        <el-icon><Folder /></el-icon>
        <span style="margin-left: 6px;">{{ dir.name }}</span>
      </div>
    </div>

    <div v-if="error" style="color: #f56c6c; margin-top: 8px; font-size: 13px;">{{ error }}</div>

    <!-- 已选路径 -->
    <div style="margin-top: 12px; font-size: 13px; color: #606266;">
      已选：<strong>{{ selectedPath || currentPath }}</strong>
    </div>

    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="confirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Folder, ArrowLeft } from '@element-plus/icons-vue'
import { filesystemApi } from '../api/client'

const props = defineProps({
  visible: Boolean,
  initialPath: { type: String, default: '' },
})
const emit = defineEmits(['update:visible', 'select'])

const loading = ref(false)
const currentPath = ref('')
const parentPath = ref(null)
const dirs = ref([])
const isGit = ref(false)
const error = ref('')
const selectedPath = ref('')
const manualPath = ref('')

const breadcrumbs = computed(() => {
  if (!currentPath.value) return []
  const parts = currentPath.value.split('/').filter(Boolean)
  return parts.map((name, i) => ({
    name: i === 0 ? '/' + name : name,
    path: '/' + parts.slice(0, i + 1).join('/'),
  }))
})

const browse = async (path) => {
  loading.value = true
  error.value = ''
  try {
    const { data } = await filesystemApi.browse(path || undefined)
    currentPath.value = data.path
    parentPath.value = data.parent
    dirs.value = data.dirs || []
    isGit.value = data.is_git || false
    manualPath.value = data.path
    selectedPath.value = ''
    if (data.error) error.value = data.error
  } catch (e) {
    error.value = '浏览目录失败'
  } finally {
    loading.value = false
  }
}

const goToPath = (path) => {
  if (path) browse(path)
}

const confirm = () => {
  emit('select', selectedPath.value || currentPath.value)
  emit('update:visible', false)
}

watch(() => props.visible, (val) => {
  if (val) {
    browse(props.initialPath || '')
  }
})
</script>

<style scoped>
.dir-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid #f5f5f5;
  font-size: 14px;
}
.dir-item:hover {
  background: #f5f7fa;
}
.dir-item.selected {
  background: #ecf5ff;
  color: #409eff;
}
</style>
