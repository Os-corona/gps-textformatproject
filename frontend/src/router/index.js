import { createRouter, createWebHistory } from 'vue-router'
import { useFlowStore } from '@/stores/flowStore'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue')
  },
  {
    path: '/config',
    name: 'config',
    component: () => import('@/views/ConfigView.vue'),
    meta: { requiresDocument: true }
  },
  {
    path: '/result',
    name: 'result',
    component: () => import('@/views/ResultView.vue'),
    meta: { requiresConfig: true }
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('@/views/HistoryView.vue')
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const DEV_BYPASS = String(import.meta.env.VITE_USE_MOCKS).toLowerCase() === 'true'

router.beforeEach((to, from, next) => {
  // Skip guards in mock/dev mode so we can navigate directly to any route
  if (DEV_BYPASS) return next()

  const flowStore = useFlowStore()

  if (to.meta.requiresDocument && !flowStore.document) {
    return next({ path: '/' })
  }

  if (to.meta.requiresConfig && !flowStore.config) {
    return next({ path: '/' })
  }

  next()
})

export default router
