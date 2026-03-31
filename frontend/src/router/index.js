import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'

const routes = [
  { path: '/', name: 'Dashboard', component: Dashboard },
  { path: '/journals', name: 'Journals', component: () => import('../views/Journals.vue') },
  { path: '/projects', name: 'Projects', component: () => import('../views/Projects.vue') },
  { path: '/config', name: 'Config', component: () => import('../views/Config.vue') },
  { path: '/stats', name: 'Stats', component: () => import('../views/Stats.vue') },
  { path: '/logs', name: 'Logs', component: () => import('../views/Logs.vue') },
  { path: '/debug', name: 'Debug', component: () => import('../views/Debug.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
