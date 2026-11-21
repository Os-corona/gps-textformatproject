<script setup lang="ts">
import { ref } from "vue";
import Sidebar from "@/components/Sidebar.vue";

// Start collapsed on phones so the document/review content is readable.
const sidebarExpanded = ref(window.innerWidth >= 768);
</script>

<template>
  <div class="d-flex vh-100 bg-light">
    <Sidebar
      :expanded="sidebarExpanded"
      @toggle="sidebarExpanded = !sidebarExpanded"
    />

    <main class="flex-grow-1 overflow-auto">
      <!-- Header -->
      <div class="mt-3 mb-3 mx-4 app-header">
        <p class="fs-1 fw-semibold mb-1 app-title">PrettyDocs</p>
        <p style="font-size: 0.9em">
          Formateo profesional de documentos a sólo un par de clicks...
        </p>
      </div>

      <!-- Router Content -->
      <div class="mx-4 pb-5">
        <router-view />
      </div>
    </main>
  </div>
</template>

<style>
body {
  margin: 0;
}

@media (max-width: 767.98px) {
  main > .mx-4 {
    margin-left: 0.75rem !important;
    margin-right: 0.75rem !important;
  }

  .app-title {
    font-size: 2rem !important;
  }
}
</style>