<script setup lang="ts">
import type { ViewKey } from "@/types";

defineProps<{
  active: ViewKey;
  expanded: boolean;
}>();

const emit = defineEmits<{
  (e: "update:active", value: ViewKey): void;
  (e: "toggle"): void;
}>();

const items: { key: ViewKey; label: string; icon: string }[] = [
  { key: "format", label: "Formatear", icon: "📝" },
  { key: "history", label: "Historial", icon: "🕘" },
  { key: "settings", label: "Configuración", icon: "⚙️" },
];
</script>

<template>
  <aside
    class="sidebar d-flex flex-column bg-white border-end"
    :class="{ expanded }"
  >
    <div class="d-flex align-items-center justify-content-between p-3 border-bottom">
      <span v-if="expanded" class="fw-bold fs-5 text-primary">PrettyDocs</span>
      <button
        class="btn btn-sm btn-light"
        @click="emit('toggle')"
        :title="expanded ? 'Colapsar' : 'Expandir'"
      >
        {{ expanded ? "«" : "»" }}
      </button>
    </div>

    <nav class="nav flex-column p-2 gap-1 flex-grow-1">
      <button
        v-for="item in items"
        :key="item.key"
        class="btn text-start d-flex align-items-center gap-3 nav-item-btn"
        :class="
          active === item.key
            ? 'btn-primary'
            : 'btn-light text-dark'
        "
        @click="emit('update:active', item.key)"
      >
        <span class="fs-5">{{ item.icon }}</span>
        <span v-if="expanded" class="fw-medium">{{ item.label }}</span>
      </button>
    </nav>

    <div v-if="expanded" class="p-3 border-top small text-secondary">
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
</style>
