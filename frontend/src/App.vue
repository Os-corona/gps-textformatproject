<script setup lang="ts">
import { ref } from 'vue'
import Sidebar from '@/components/Sidebar.vue'

// Start collapsed on phones so the document/review content is readable.
const sidebarExpanded = ref(window.innerWidth >= 768)
</script>

<template>
  <div class="d-flex vh-100 pd-shell">
    <Sidebar
      :expanded="sidebarExpanded"
      @toggle="sidebarExpanded = !sidebarExpanded"
    />

    <main class="flex-grow-1 overflow-auto">
      <!-- Top App Bar -->
      <header class="app-topbar px-4 py-3 mb-3">
        <div class="d-flex flex-wrap align-items-center justify-content-between gap-2">
          <div>
            <div class="d-flex align-items-center gap-2">
              <h1 class="app-title mb-0">PrettyDocs</h1>
              <span class="badge rounded-pill app-badge">IA Estructural + OOXML</span>
            </div>
            <p class="app-subtitle mb-0">
              Transforma documentos Word planos en reportes ejecutivos y académicos sin alterar tu contenido.
            </p>
          </div>

          <div class="d-none d-md-flex align-items-center gap-2">
            <span class="status-pill">
              <span class="status-dot"></span>
              Integridad verificada 100%
            </span>
          </div>
        </div>
      </header>

      <!-- Router Content -->
      <div class="px-4 pb-5 app-content">
        <router-view />
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-topbar {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--pd-border);
  position: sticky;
  top: 0;
  z-index: 20;
}

.app-title {
  font-size: 1.45rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #1f497d 0%, #3b6fb6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.app-badge {
  background: var(--pd-brand-soft);
  color: var(--pd-brand);
  border: 1px solid rgba(31, 73, 125, 0.16);
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.3rem 0.65rem;
}

.app-subtitle {
  font-size: 0.85rem;
  color: var(--pd-muted);
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  color: #166534;
  background: #dcfce7;
  border: 1px solid #bbf7d0;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #16a34a;
}

@media (max-width: 767.98px) {
  .app-topbar,
  .app-content {
    padding-left: 0.85rem !important;
    padding-right: 0.85rem !important;
  }
}
</style>
