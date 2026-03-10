<template>
  <div class="projects">
    <h2>项目管理</h2>

    <!-- 操作栏 -->
    <el-card class="action-bar">
      <el-form :inline="true">
        <el-form-item>
          <el-button type="primary" @click="showAddDialog = true">添加项目</el-button>
        </el-form-item>
        <el-form-item>
          <el-switch v-model="showInactive" active-text="显示已停用" @change="loadProjects" />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 项目列表 -->
    <el-card v-loading="loading">
      <el-empty v-if="projects.length === 0" description="暂无项目，点击上方按钮添加" />
      <el-table v-else :data="projects" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="项目名称" width="160">
          <template #default="{ row }">
            <span style="font-weight: 600">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路径" min-width="240" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.description || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '活跃' : '已停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="追踪状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="trackerStatus[row.id]" type="success" size="small" effect="dark">运行中</el-tag>
            <el-tag v-else type="info" size="small">未运行</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button
              v-if="row.is_active"
              type="warning" text size="small"
              @click="toggleActive(row, false)"
            >停用</el-button>
            <el-button
              v-else
              type="success" text size="small"
              @click="toggleActive(row, true)"
            >启用</el-button>
            <el-button type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加项目对话框 -->
    <el-dialog v-model="showAddDialog" title="添加项目" width="500px">
      <el-form :model="addForm" label-width="80px" :rules="formRules" ref="addFormRef">
        <el-form-item label="名称" prop="name">
          <el-input v-model="addForm.name" placeholder="项目名称（唯一）" />
        </el-form-item>
        <el-form-item label="路径" prop="path">
          <el-input v-model="addForm.path" placeholder="项目绝对路径" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="addForm.description" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleAdd">确定</el-button>
      </template>
    </el-dialog>

    <!-- 编辑项目对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑项目" width="500px">
      <el-form :model="editForm" label-width="80px" :rules="formRules" ref="editFormRef">
        <el-form-item label="名称" prop="name">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="路径" prop="path">
          <el-input v-model="editForm.path" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 项目统计概览 -->
    <el-card v-if="projects.length > 0" class="stats-card">
      <template #header>项目概览</template>
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="overview-item">
            <div class="overview-value">{{ projects.length }}</div>
            <div class="overview-label">总项目数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="overview-item">
            <div class="overview-value">{{ projects.filter(p => p.is_active).length }}</div>
            <div class="overview-label">活跃项目</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="overview-item">
            <div class="overview-value">{{ Object.keys(trackerStatus).length }}</div>
            <div class="overview-label">运行中追踪器</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="overview-item">
            <div class="overview-value">{{ projects.filter(p => !p.is_active).length }}</div>
            <div class="overview-label">已停用</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { projectApi } from '../api/client'
import { useProjectStore } from '../stores/project'

const projectStore = useProjectStore()
const loading = ref(false)
const submitting = ref(false)
const projects = ref([])
const trackerStatus = ref({})
const showInactive = ref(true)
const showAddDialog = ref(false)
const showEditDialog = ref(false)
const addFormRef = ref(null)
const editFormRef = ref(null)

const addForm = reactive({ name: '', path: '', description: '' })
const editForm = reactive({ id: null, name: '', path: '', description: '' })

const formRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  path: [{ required: true, message: '请输入项目路径', trigger: 'blur' }],
}

const formatTime = (isoStr) => {
  if (!isoStr) return '-'
  return new Date(isoStr).toLocaleString('zh-CN')
}

const loadProjects = async () => {
  loading.value = true
  try {
    const params = {}
    if (!showInactive.value) params.is_active = true
    const { data } = await projectApi.list(params)
    projects.value = data
    // 同步更新 store
    projectStore.projectList = data.filter(p => p.is_active)
  } catch (e) {
    console.error('加载项目失败:', e)
  } finally {
    loading.value = false
  }
}

const loadTrackerStatus = async () => {
  try {
    const { data } = await projectApi.trackerStatus()
    trackerStatus.value = data
  } catch {
    // 接口可能不存在，忽略
  }
}

const handleAdd = async () => {
  if (!addFormRef.value) return
  await addFormRef.value.validate()
  submitting.value = true
  try {
    await projectApi.create({
      name: addForm.name,
      path: addForm.path,
      description: addForm.description || undefined,
    })
    ElMessage.success('项目已添加')
    showAddDialog.value = false
    addForm.name = ''
    addForm.path = ''
    addForm.description = ''
    loadProjects()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  } finally {
    submitting.value = false
  }
}

const openEditDialog = (row) => {
  editForm.id = row.id
  editForm.name = row.name
  editForm.path = row.path
  editForm.description = row.description || ''
  showEditDialog.value = true
}

const handleEdit = async () => {
  if (!editFormRef.value) return
  await editFormRef.value.validate()
  submitting.value = true
  try {
    await projectApi.update(editForm.id, {
      name: editForm.name,
      path: editForm.path,
      description: editForm.description || undefined,
    })
    ElMessage.success('项目已更新')
    showEditDialog.value = false
    loadProjects()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '更新失败')
  } finally {
    submitting.value = false
  }
}

const toggleActive = async (row, active) => {
  try {
    await projectApi.update(row.id, { is_active: active })
    ElMessage.success(active ? '项目已启用' : '项目已停用')
    loadProjects()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定删除项目「${row.name}」？此操作将停用该项目。`,
      '确认删除',
      { type: 'warning' }
    )
    await projectApi.delete(row.id)
    ElMessage.success('项目已删除')
    loadProjects()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

onMounted(() => {
  loadProjects()
  loadTrackerStatus()
})
</script>

<style scoped>
.projects h2 { margin-top: 0; }
.action-bar { margin-bottom: 20px; }
.stats-card { margin-top: 20px; }
.overview-item { text-align: center; padding: 12px 0; }
.overview-value { font-size: 28px; font-weight: bold; color: #409eff; }
.overview-label { color: #909399; font-size: 13px; margin-top: 4px; }
</style>
