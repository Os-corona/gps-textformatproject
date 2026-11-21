<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";

defineProps<{
  expanded: boolean;
}>();

const emit = defineEmits<{
  (e: "toggle"): void;
}>();

const route = useRoute();
const router = useRouter();

const items = [
  { path: "/", label: "Formatear", icon: "📝" },
  { path: "/history", label: "Historial", icon: "🕘" },
  { path: "/settings", label: "Configuración", icon: "⚙️" },
];

function navigate(path: string) {
  router.push(path);
}

function isItemActive(path: string) {
  if (path === "/") {
    return ["/", "/config", "/result"].includes(route.path) || route.path.startsWith("/processing") || route.path.startsWith("/review");
  }
  return route.path === path;
}
</script>

<template>
  <aside
    class="sidebar d-flex flex-column bg-white border-end"
    :class="{ expanded }"
  >
    <div class="d-flex align-items-center justify-content-between p-3 border-bottom">
      <span v-if="expanded" class="fw-bold fs-5 text-primary sidebar-brand">PrettyDocs</span>
      <button
        class="btn btn-sm btn-light sidebar-toggle"
        @click="emit('toggle')"
        :title="expanded ? 'Colapsar' : 'Expandir'"
      >
        {{ expanded ? "«" : "»" }}
      </button>
    </div>

    <nav class="nav flex-column p-2 gap-1 flex-grow-1">
      <button
        v-for="item in items"
        :key="item.path"
        class="btn text-start d-flex align-items-center gap-3 nav-item-btn"
        :class="
          isItemActive(item.path)
            ? 'btn-primary'
            : 'btn-light text-dark'
        "
        @click="navigate(item.path)"
      >
        <span class="fs-5">{{ item.icon }}</span>
        <span v-if="expanded" class="fw-medium nav-label">{{ item.label }}</span>
      </button>
    </nav>

    <div v-if="expanded" class="p-3 border-top small text-secondary sidebar-footer">
      v0.1.0 · Front-end only
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 72px;
  flex-shrink: 0;
  transition: width 0.2s ease;
}
.sidebar.expanded {
  width: 240px;
  flex-shrink: 0;
}

.nav-item-btn {
  white-space: nowrap;
  overflow: hidden;
}

/* Keep the navigation compact on phones so the review content keeps a
   readable width. The sidebar never grows past the icon rail on small screens. */
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
