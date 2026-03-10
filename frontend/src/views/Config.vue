<template>
  <div class="config">
    <h2>配置管理</h2>

    <el-tabs v-model="activeTab" v-loading="loading">
      <!-- 数据库配置 -->
      <el-tab-pane label="数据库" name="database">
        <el-form :model="appConfig.database" label-width="120px" style="max-width: 500px">
          <el-form-item label="主机">
            <el-input v-model="appConfig.database.host" />
          </el-form-item>
          <el-form-item label="端口">
            <el-input-number v-model="appConfig.database.port" :min="1" :max="65535" />
          </el-form-item>
          <el-form-item label="用户">
            <el-input v-model="appConfig.database.user" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="appConfig.database.password" type="password" show-password />
          </el-form-item>
          <el-form-item label="数据库名">
            <el-input v-model="appConfig.database.database" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveSection('database')">保存</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- SSH 隧道配置 -->
      <el-tab-pane label="SSH 隧道" name="ssh">
        <el-form :model="appConfig.ssh" label-width="120px" style="max-width: 500px">
          <el-form-item label="启用">
            <el-switch v-model="appConfig.ssh.enabled" />
          </el-form-item>
          <template v-if="appConfig.ssh.enabled">
            <el-form-item label="SSH主机">
              <el-input v-model="appConfig.ssh.host" />
            </el-form-item>
            <el-form-item label="SSH端口">
              <el-input-number v-model="appConfig.ssh.port" :min="1" :max="65535" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="appConfig.ssh.username" />
            </el-form-item>
            <el-form-item label="认证方式">
              <el-radio-group v-model="appConfig.ssh.auth_type">
                <el-radio value="key">密钥</el-radio>
                <el-radio value="password">密码</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item v-if="appConfig.ssh.auth_type === 'key'" label="密钥路径">
              <el-input v-model="appConfig.ssh.key_path" />
            </el-form-item>
            <el-form-item v-if="appConfig.ssh.auth_type === 'password'" label="SSH密码">
              <el-input v-model="appConfig.ssh.password" type="password" show-password />
            </el-form-item>
            <el-form-item label="远程主机">
              <el-input v-model="appConfig.ssh.remote_host" />
            </el-form-item>
            <el-form-item label="远程端口">
              <el-input-number v-model="appConfig.ssh.remote_port" :min="1" :max="65535" />
            </el-form-item>
          </template>
          <el-form-item>
            <el-button type="primary" @click="saveSection('ssh')">保存</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 追踪器配置 -->
      <el-tab-pane label="追踪器" name="tracker">
        <el-form :model="appConfig.tracker" label-width="160px" style="max-width: 600px">
          <el-form-item label="Git检查间隔(秒)">
            <el-input-number v-model="appConfig.tracker.git_check_interval" :min="5" />
          </el-form-item>
          <el-form-item label="文件批量大小">
            <el-input-number v-model="appConfig.tracker.file_batch_size" :min="1" />
          </el-form-item>
          <el-form-item label="文件批量间隔(秒)">
            <el-input-number v-model="appConfig.tracker.file_batch_interval" :min="10" />
          </el-form-item>
          <el-form-item label="监控路径">
            <div style="width: 100%">
              <el-tag
                v-for="(path, index) in appConfig.tracker.watch_paths"
                :key="index"
                closable
                style="margin: 0 4px 4px 0"
                @close="appConfig.tracker.watch_paths.splice(index, 1)"
              >{{ path }}</el-tag>
              <el-input
                v-if="showWatchPathInput"
                ref="watchPathRef"
                v-model="newWatchPath"
                size="small"
                style="width: 200px"
                @keyup.enter="addWatchPath"
                @blur="addWatchPath"
              />
              <el-button v-else size="small" @click="showWatchPathInput = true">+ 添加</el-button>
            </div>
          </el-form-item>
          <el-form-item label="忽略模式">
            <div style="width: 100%">
              <el-tag
                v-for="(pat, index) in appConfig.tracker.ignored_patterns"
                :key="index"
                closable
                style="margin: 0 4px 4px 0"
                @close="appConfig.tracker.ignored_patterns.splice(index, 1)"
              >{{ pat }}</el-tag>
              <el-input
                v-if="showIgnoreInput"
                ref="ignoreRef"
                v-model="newIgnorePattern"
                size="small"
                style="width: 200px"
                @keyup.enter="addIgnorePattern"
                @blur="addIgnorePattern"
              />
              <el-button v-else size="small" @click="showIgnoreInput = true">+ 添加</el-button>
            </div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveSection('tracker')">保存</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- AI 服务配置 -->
      <el-tab-pane label="AI 服务" name="ai">
        <el-form :model="appConfig.ai" label-width="140px" style="max-width: 500px">
          <el-form-item label="默认配置名称">
            <el-input v-model="appConfig.ai.default_config" />
          </el-form-item>
          <el-form-item label="重试次数">
            <el-input-number v-model="appConfig.ai.retry_attempts" :min="0" :max="10" />
          </el-form-item>
          <el-form-item label="超时时间(秒)">
            <el-input-number v-model="appConfig.ai.timeout" :min="5" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveSection('ai')">保存</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- Web 服务配置 -->
      <el-tab-pane label="Web 服务" name="web">
        <el-form :model="appConfig.web" label-width="120px" style="max-width: 500px">
          <el-form-item label="监听地址">
            <el-input v-model="appConfig.web.host" />
          </el-form-item>
          <el-form-item label="端口">
            <el-input-number v-model="appConfig.web.port" :min="1" :max="65535" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveSection('web')">保存</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- API 配置（原有功能） -->
      <el-tab-pane label="API 配置" name="apiConfig">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>API配置</span>
              <el-button type="primary" @click="showAddDialog = true">添加配置</el-button>
            </div>
          </template>

          <el-table :data="apiConfigs" v-loading="apiLoading">
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
            <el-table-column label="操作" width="280">
              <template #default="{ row }">
                <el-button size="small" @click="testConfig(row)">测试</el-button>
                <el-button size="small" type="primary" plain @click="openEditDialog(row)">编辑</el-button>
                <el-button size="small" type="primary" :disabled="row.is_active" @click="activateConfig(row)">
                  激活
                </el-button>
                <el-button size="small" type="danger" @click="deleteConfig(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加API配置对话框 -->
    <el-dialog v-model="showAddDialog" :title="editingConfig ? '编辑API配置' : '添加API配置'" width="600px">
      <el-form :model="editingConfig || newConfig" label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="currentForm.name" placeholder="例如: default" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="currentForm.api_key" type="password" show-password placeholder="不修改请留空" />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="currentForm.base_url" placeholder="https://api.openai.com" />
        </el-form-item>
        <el-form-item label="模型">
          <el-input v-model="currentForm.model" placeholder="gpt-4" />
        </el-form-item>
        <el-form-item label="Endpoint">
          <el-input v-model="currentForm.endpoint" placeholder="/v1/chat/completions" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="saveConfig">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { configApi } from '../api/client'

const activeTab = ref('database')
const loading = ref(false)

// 应用配置
const appConfig = ref({
  database: { host: '', port: 3307, user: '', password: '', database: '' },
  ssh: { enabled: false, host: '', port: 22, username: '', auth_type: 'key', key_path: '', password: '', remote_host: '127.0.0.1', remote_port: 3306 },
  tracker: { git_check_interval: 30, file_batch_size: 10, file_batch_interval: 300, watch_paths: ['.'], ignored_patterns: [] },
  ai: { default_config: 'default', retry_attempts: 3, timeout: 30 },
  web: { host: '127.0.0.1', port: 8000 },
})

// 动态标签输入
const showWatchPathInput = ref(false)
const newWatchPath = ref('')
const watchPathRef = ref(null)
const showIgnoreInput = ref(false)
const newIgnorePattern = ref('')
const ignoreRef = ref(null)

const addWatchPath = () => {
  if (newWatchPath.value.trim()) {
    appConfig.value.tracker.watch_paths.push(newWatchPath.value.trim())
  }
  newWatchPath.value = ''
  showWatchPathInput.value = false
}

const addIgnorePattern = () => {
  if (newIgnorePattern.value.trim()) {
    appConfig.value.tracker.ignored_patterns.push(newIgnorePattern.value.trim())
  }
  newIgnorePattern.value = ''
  showIgnoreInput.value = false
}

const loadAppConfig = async () => {
  loading.value = true
  try {
    const { data } = await configApi.getAppConfig()
    appConfig.value = data
  } catch (e) {
    ElMessage.error('加载应用配置失败')
  } finally {
    loading.value = false
  }
}

const saveSection = async (section) => {
  try {
    await configApi.updateAppConfigSection(section, appConfig.value[section])
    ElMessage.success('配置已保存')
  } catch (e) {
    ElMessage.error('保存配置失败')
  }
}

// API 配置（原有功能）
const apiConfigs = ref([])
const apiLoading = ref(false)
const showAddDialog = ref(false)
const editingConfig = ref(null)
const newConfig = ref({
  name: '',
  api_key: '',
  base_url: '',
  model: '',
  endpoint: '/v1/chat/completions',
})

// 当前表单数据（用于添加或编辑）
const currentForm = ref({
  name: '',
  api_key: '',
  base_url: '',
  model: '',
  endpoint: '/v1/chat/completions',
})

const loadConfigs = async () => {
  apiLoading.value = true
  try {
    const { data } = await configApi.listApiConfigs()
    apiConfigs.value = data
  } catch (e) {
    ElMessage.error('加载API配置失败')
  } finally {
    apiLoading.value = false
  }
}

const addConfig = async () => {
  try {
    await configApi.createApiConfig(newConfig.value)
    ElMessage.success('配置已添加')
    closeDialog()
    loadConfigs()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加配置失败')
  }
}

const openEditDialog = (config) => {
  editingConfig.value = config
  currentForm.value = {
    name: config.name,
    api_key: '', // 编辑时不显示原密钥
    base_url: config.base_url,
    model: config.model,
    endpoint: config.endpoint || '/v1/chat/completions',
  }
  showAddDialog.value = true
}

const saveConfig = async () => {
  try {
    if (editingConfig.value) {
      // 编辑模式
      const updateData = {
        name: currentForm.value.name,
        base_url: currentForm.value.base_url,
        model: currentForm.value.model,
        endpoint: currentForm.value.endpoint,
      }
      // 只有填写了 API Key 才更新
      if (currentForm.value.api_key) {
        updateData.api_key = currentForm.value.api_key
      }
      await configApi.updateApiConfig(editingConfig.value.id, updateData)
      ElMessage.success('配置已更新')
    } else {
      // 添加模式
      await configApi.createApiConfig(currentForm.value)
      ElMessage.success('配置已添加')
    }
    closeDialog()
    loadConfigs()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存配置失败')
  }
}

const closeDialog = () => {
  showAddDialog.value = false
  editingConfig.value = null
  currentForm.value = { name: '', api_key: '', base_url: '', model: '', endpoint: '/v1/chat/completions' }
  newConfig.value = { name: '', api_key: '', base_url: '', model: '', endpoint: '/v1/chat/completions' }
}

const testConfig = async (config) => {
  apiLoading.value = true
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
    apiLoading.value = false
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
  loadAppConfig()
  loadConfigs()
})
</script>

<style scoped>
.config h2 { margin-top: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
