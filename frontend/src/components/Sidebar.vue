<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

defineProps<{
  expanded: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle'): void
}>()

const route = useRoute()
const router = useRouter()

const items = [
  { path: '/', label: 'Formatear', icon: 'format' },
  { path: '/history', label: 'Historial', icon: 'history' },
  { path: '/settings', label: 'Preferencias', icon: 'settings' }
] as const

function navigate(path: string) {
  router.push(path)
}

function isItemActive(path: string) {
  if (path === '/') {
    return (
      ['/', '/config', '/result'].includes(route.path) ||
      route.path.startsWith('/processing') ||
      route.path.startsWith('/review')
    )
  }
  return route.path === path
}
</script>

<template>
  <aside
    class="sidebar d-flex flex-column bg-white border-end"
    :class="{ expanded }"
  >
    <div class="d-flex align-items-center justify-content-between p-3 border-bottom sidebar-head">
      <div v-if="expanded" class="d-flex align-items-center gap-2 sidebar-brand">
        <span class="brand-mark">P</span>
        <span class="fw-bold fs-6 text-dark">PrettyDocs</span>
      </div>
      <button
        type="button"
        class="btn btn-sm btn-light border sidebar-toggle"
        @click="emit('toggle')"
        :title="expanded ? 'Colapsar menú' : 'Expandir menú'"
      >
        <svg v-if="expanded" xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
          <path fill-rule="evenodd" d="M11.354 1.646a.5.5 0 0 1 0 .708L5.707 8l5.647 5.646a.5.5 0 0 1-.708.708l-6-6a.5.5 0 0 1 0-.708l6-6a.5.5 0 0 1 .708 0z"/>
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
          <path fill-rule="evenodd" d="M4.646 1.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0 1 0 .708l-6 6a.5.5 0 0 1-.708-.708L10.293 8 4.646 2.354a.5.5 0 0 1 0-.708z"/>
        </svg>
      </button>
    </div>

    <nav class="nav flex-column p-2 gap-1 flex-grow-1">
      <button
        v-for="item in items"
        :key="item.path"
        type="button"
        class="btn text-start d-flex align-items-center gap-3 nav-item-btn"
        :class="isItemActive(item.path) ? 'nav-item-btn--active' : 'nav-item-btn--idle'"
        @click="navigate(item.path)"
      >
        <span class="nav-icon d-inline-flex align-items-center justify-content-center">
          <svg v-if="item.icon === 'format'" xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16">
            <path d="M5.5 7a.5.5 0 0 0 0 1h5a.5.5 0 0 0 0-1h-5zM5 9.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5zm0 2a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 0 1h-2a.5.5 0 0 1-.5-.5z"/>
            <path d="M9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.5L9.5 0zm0 1v2A1.5 1.5 0 0 0 11 4.5h2V14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h5.5z"/>
          </svg>
          <svg v-else-if="item.icon === 'history'" xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16">
            <path d="M8.515 1.019A7 7 0 0 0 8 1V0a8 8 0 0 1 .589.022l-.074.997zm2.004.45a7.003 7.003 0 0 0-.985-.299l.219-.976c.383.086.76.2 1.126.342l-.36.933zm1.37.71a7.01 7.01 0 0 0-.439-.27l.493-.87a8.025 8.025 0 0 1 .979.654l-.615.789a6.996 6.996 0 0 0-.418-.302zm1.834 1.79a6.99 6.99 0 0 0-.653-.796l.724-.69c.27.285.52.59.747.91l-.818.576zm.744 1.352a7.08 7.08 0 0 0-.214-.468l.893-.45a7.976 7.976 0 0 1 .45 1.088l-.95.313a7.023 7.023 0 0 0-.179-.483zm.53 2.507a6.991 6.991 0 0 0-.1-1.025l.985-.17c.067.386.106.778.116 1.17l-1 .025zm-.131 1.538c.033-.17.06-.339.081-.51l.993.123a7.957 7.957 0 0 1-.23 1.155l-.964-.267c.046-.165.086-.332.12-.501zm-.952 2.379c.184-.29.346-.594.486-.908l.914.405c-.16.36-.345.706-.555 1.038l-.845-.535zm-.964 1.205c.122-.122.239-.248.35-.378l.758.653a8.073 8.073 0 0 1-.401.432l-.707-.707z"/>
            <path d="M8 1a7 7 0 1 0 4.95 11.95l.707.707A8.001 8.001 0 1 1 8 0v1z"/>
            <path d="M7.5 3a.5.5 0 0 1 .5.5v5.21l3.248 1.856a.5.5 0 0 1-.496.868l-3.5-2A.5.5 0 0 1 7 9V3.5a.5.5 0 0 1 .5-.5z"/>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16">
            <path d="M8 4.754a3.246 3.246 0 1 0 0 6.492 3.246 3.246 0 0 0 0-6.492zM5.754 8a2.246 2.246 0 1 1 4.492 0 2.246 2.246 0 0 1-4.492 0z"/>
            <path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 0 1-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 0 1-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 0 1 .52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 0 1 1.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 0 1 1.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 0 1 .52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 0 1-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 0 1-1.255-.52l-.094-.319zm-2.633.283c.246-.835 1.428-.835 1.674 0l.094.319a1.873 1.873 0 0 0 2.693 1.115l.291-.16c.764-.415 1.6.42 1.184 1.185l-.159.292a1.873 1.873 0 0 0 1.116 2.692l.318.094c.835.246.835 1.428 0 1.674l-.319.094a1.873 1.873 0 0 0-1.115 2.693l.16.291c.415.764-.42 1.6-1.185 1.184l-.291-.159a1.873 1.873 0 0 0-2.693 1.116l-.094.318c-.246.835-1.428.835-1.674 0l-.094-.319a1.873 1.873 0 0 0-2.692-1.115l-.292.16c-.764.415-1.6-.42-1.184-1.185l.159-.291A1.873 1.873 0 0 0 1.945 8.93l-.319-.094c-.835-.246-.835-1.428 0-1.674l.319-.094A1.873 1.873 0 0 0 3.06 4.377l-.16-.292c-.415-.764.42-1.6 1.185-1.184l.292.159a1.873 1.873 0 0 0 2.692-1.115l.094-.319z"/>
          </svg>
        </span>
        <span v-if="expanded" class="fw-medium nav-label">{{ item.label }}</span>
      </button>
    </nav>

    <div v-if="expanded" class="p-3 border-top sidebar-footer">
      <div class="d-flex align-items-center gap-2 small fw-semibold text-dark">
        <span class="engine-dot"></span>
        Motor IA + OOXML v1.1
      </div>
      <div class="text-secondary" style="font-size: 0.72rem">
        PrettyDocs · Sprint 3 Demo
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 72px;
  flex-shrink: 0;
  transition: width 0.2s ease;
  border-color: var(--pd-border) !important;
}
.sidebar.expanded {
  width: 232px;
  flex-shrink: 0;
}

.sidebar-head {
  min-height: 64px;
  border-color: var(--pd-border) !important;
}

.brand-mark {
  width: 30px;
  height: 30px;
  border-radius: 0.55rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f497d 0%, #3b6fb6 100%);
  color: #fff;
  font-weight: 800;
  font-size: 0.95rem;
}

.nav-item-btn {
  white-space: nowrap;
  overflow: hidden;
  border-radius: 0.65rem;
  padding: 0.65rem 0.85rem;
  border: 0;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.nav-item-btn--active {
  background: linear-gradient(135deg, #1f497d 0%, #2f5496 100%);
  color: #fff;
  box-shadow: 0 4px 12px rgba(31, 73, 125, 0.22);
}

.nav-item-btn--active:hover {
  color: #fff;
}

.nav-item-btn--idle {
  background: transparent;
  color: #334155;
}

.nav-item-btn--idle:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.nav-icon {
  width: 22px;
  flex-shrink: 0;
}

.engine-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #16a34a;
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.2);
}

@media (max-width: 767.98px) {
  .sidebar.expanded {
    width: 72px;
  }

  .sidebar.expanded .sidebar-brand,
  .sidebar.expanded .nav-label,
  .sidebar.expanded .sidebar-footer,
  .sidebar .sidebar-toggle {
    display: none;
  }
}
</style>
