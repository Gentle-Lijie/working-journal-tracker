<template>
  <div class="api-tester">
    <el-form :model="form" label-width="100px">
      <el-form-item label="API Key">
        <el-input v-model="form.api_key" type="password" show-password />
      </el-form-item>
      <el-form-item label="Base URL">
        <el-input v-model="form.base_url" placeholder="https://api.openai.com" />
      </el-form-item>
      <el-form-item label="模型">
        <el-input v-model="form.model" placeholder="gpt-4" />
      </el-form-item>
      <el-form-item label="Endpoint">
        <el-input v-model="form.endpoint" placeholder="/v1/chat/completions" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="testing" @click="testApi">
          测试连接
        </el-button>
      </el-form-item>
    </el-form>

    <el-result
      v-if="result"
      :icon="result.success ? 'success' : 'error'"
      :title="result.success ? '连接成功' : '连接失败'"
      :sub-title="result.message"
    >
      <template v-if="result.success" #extra>
        <span>响应时间: {{ result.response_time }}ms</span>
      </template>
    </el-result>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { aiApi } from '../api/client'

const form = ref({
  api_key: '',
  base_url: '',
  model: '',
  endpoint: '/v1/chat/completions',
})

const testing = ref(false)
const result = ref(null)

const testApi = async () => {
  testing.value = true
  result.value = null
  try {
    const { data } = await aiApi.test(form.value)
    result.value = data
  } catch (e) {
    result.value = { success: false, message: '请求失败: ' + (e.message || '未知错误') }
  } finally {
    testing.value = false
  }
}
</script>
