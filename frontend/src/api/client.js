import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 活动记录API
export const activityApi = {
  list(params = {}) {
    return client.get('/activities', { params })
  },
  create(data) {
    return client.post('/activities', data)
  },
}

// 日志API
export const journalApi = {
  list(params = {}) {
    return client.get('/journals', { params })
  },
  generate(data) {
    return client.post('/journals/generate', data)
  },
}

// 配置API
export const configApi = {
  listApiConfigs() {
    return client.get('/config/api')
  },
  createApiConfig(data) {
    return client.post('/config/api', data)
  },
  updateApiConfig(id, data) {
    return client.put(`/config/api/${id}`, data)
  },
  deleteApiConfig(id) {
    return client.delete(`/config/api/${id}`)
  },
  testApiConfig(id) {
    return client.post(`/config/api/${id}/test`)
  },
  getAppConfig() {
    return client.get('/config/app')
  },
  updateAppConfigSection(section, data) {
    return client.put(`/config/app/${section}`, data)
  },
}

// AI API
export const aiApi = {
  test(data) {
    return client.post('/ai/test', data)
  },
  summarize(data) {
    return client.post('/ai/summarize', data)
  },
  classify(data) {
    return client.post('/ai/classify', data)
  },
}

// 统计API
export const statsApi = {
  daily(date) {
    return client.get('/stats/daily', { params: { date } })
  },
  tokens(days = 7) {
    return client.get('/stats/tokens', { params: { days } })
  },
  workTypes(days = 30) {
    return client.get('/stats/work-types', { params: { days } })
  },
}

export default client
