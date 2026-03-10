import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求日志拦截器
client.interceptors.request.use(
  (config) => {
    const params = config.params ? `?${new URLSearchParams(config.params)}` : ''
    console.log(`[API] ${config.method.toUpperCase()} ${config.baseURL}${config.url}${params}`)
    return config
  },
  (error) => {
    console.error('[API] 请求错误:', error.message)
    return Promise.reject(error)
  }
)

// 响应日志拦截器
client.interceptors.response.use(
  (response) => {
    const { config, status, data } = response
    const count = Array.isArray(data) ? `(${data.length}条)` : ''
    console.log(`[API] ${config.method.toUpperCase()} ${config.url} => ${status} ${count}`)
    return response
  },
  (error) => {
    const { config, response } = error
    const status = response?.status || 'NETWORK_ERROR'
    const detail = response?.data?.detail || error.message
    console.error(`[API] ${config?.method?.toUpperCase()} ${config?.url} => ${status}: ${detail}`)
    return Promise.reject(error)
  }
)

// 项目API
export const projectApi = {
  list(params = {}) {
    return client.get('/projects', { params })
  },
  create(data) {
    return client.post('/projects', data)
  },
  get(id) {
    return client.get(`/projects/${id}`)
  },
  update(id, data) {
    return client.put(`/projects/${id}`, data)
  },
  delete(id) {
    return client.delete(`/projects/${id}`)
  },
  setPath(id, path) {
    return client.put(`/projects/${id}/path`, { path })
  },
  trackerStatus() {
    return client.get('/projects/tracker-status/all')
  },
  start(id) {
    return client.post(`/projects/${id}/start`)
  },
  stop(id) {
    return client.post(`/projects/${id}/stop`)
  },
}

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

// Git API
export const gitApi = {
  log(params = {}) {
    return client.get('/git/log', { params })
  },
}

// 系统日志API
export const logApi = {
  list(params = {}) {
    return client.get('/logs', { params })
  },
  tail(lines = 50) {
    return client.get('/logs/tail', { params: { lines } })
  },
}

// 文件系统API
export const filesystemApi = {
  browse(path) {
    return client.get('/filesystem/browse', { params: { path } })
  },
}

// 统计API
export const statsApi = {
  daily(date, projectId) {
    const params = {}
    if (date) params.date = date
    if (projectId != null) params.project_id = projectId
    return client.get('/stats/daily', { params })
  },
  tokens(days = 7, projectId) {
    const params = { days }
    if (projectId != null) params.project_id = projectId
    return client.get('/stats/tokens', { params })
  },
  workTypes(days = 30, projectId) {
    const params = { days }
    if (projectId != null) params.project_id = projectId
    return client.get('/stats/work-types', { params })
  },
}

export default client
