<template>
  <div class="config">
    <h2>配置管理</h2>

    <!-- API配置列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>API配置</span>
          <el-button type="primary" @click="showAddDialog = true">添加配置</el-button>
        </div>
      </template>

      <el-table :data="apiConfigs" v-loading="loading">
        <el-table-column prop="name" label="名称" width="150" />
        <el-table-column prop="base_url" label="Base URL" min-width="200" />
        <el-table-column prop="model" label="模型" width="150" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_active" type="success">活跃</el-tag>
            <el-tag v-else type="info">未激活</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="测试状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.test_status === 'success'" type="success">成功</el-tag>
            <el-tag v-else-if="row.test_status === 'failed'" type="danger">失败</el-tag>
            <el-tag v-else type="info">未测试</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250">
          <template #default="{ row }">
            <el-button size="small" @click="testConfig(row)">测试</el-button>
            <el-button size="small" type="primary" :disabled="row.is_active" @click="activateConfig(row)">
              激活
            </el-button>
            <el-button size="small" type="danger" @click="deleteConfig(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加配置对话框 -->
    <el-dialog v-model="showAddDialog" title="添加API配置" width="600px">
      <el-form :model="newConfig" label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="newConfig.name" placeholder="例如: default" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="newConfig.api_key" type="password" show-password />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="newConfig.base_url" placeholder="https://api.openai.com" />
        </el-form-item>
        <el-form-item label="模型">
          <el-input v-model="newConfig.model" placeholder="gpt-4" />
        </el-form-item>
        <el-form-item label="Endpoint">
          <el-input v-model="newConfig.endpoint" placeholder="/v1/chat/completions" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addConfig">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { configApi } from '../api/client'

const apiConfigs = ref([])
const loading = ref(false)
const showAddDialog = ref(false)
const newConfig = ref({
  name: '',
  api_key: '',
  base_url: '',
  model: '',
  endpoint: '/v1/chat/completions',
})

const loadConfigs = async () => {
  loading.value = true
  try {
    const { data } = await configApi.listApiConfigs()
    apiConfigs.value = data
  } catch (e) {
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

const addConfig = async () => {
  try {
    await configApi.createApiConfig(newConfig.value)
    ElMessage.success('配置已添加')
    showAddDialog.value = false
    newConfig.value = { name: '', api_key: '', base_url: '', model: '', endpoint: '/v1/chat/completions' }
    loadConfigs()
  } catch (e) {
    ElMessage.error('添加配置失败')
  }
}

const testConfig = async (config) => {
  loading.value = true
  try {
    const { data } = await configApi.testApiConfig(config.id)
    if (data.success) {
      ElMessage.success(`测试成功 (${data.response_time}ms)`)
    } else {
      ElMessage.error(`测试失败: ${data.message}`)
    }
    loadConfigs()
  } catch (e) {
    ElMessage.error('测试失败')
  } finally {
    loading.value = false
  }
}

const activateConfig = async (config) => {
  try {
    await configApi.updateApiConfig(config.id, { is_active: true })
    ElMessage.success('配置已激活')
    loadConfigs()
  } catch (e) {
    ElMessage.error('激活失败')
  }
}

const deleteConfig = async (config) => {
  try {
    await ElMessageBox.confirm('确定删除此配置？', '警告', { type: 'warning' })
    await configApi.deleteApiConfig(config.id)
    ElMessage.success('配置已删除')
    loadConfigs()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

onMounted(() => {
  loadConfigs()
})
</script>

<style scoped>
.config h2 { margin-top: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
