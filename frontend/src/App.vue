<script setup lang="ts">
import { ref } from "vue";
import FileDropzone from "@/components/FileDropzone.vue";
import HistoryView from "@/views/HistoryView.vue";
import type { ViewKey } from "@/types";

const activeView = ref<ViewKey>("format");
</script>

<template>
  <div class="min-vh-100 bg-light">
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg bg-white border-bottom">
      <div class="container-fluid px-4">
        <!-- Logo -->
        <a class="navbar-brand fw-bold fs-4 text-primary mb-0" href="#" @click.prevent="activeView = 'format'">
          PrettyDocs
        </a>

        <!-- Botón hamburguesa (móvil) -->
        <button
          class="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#mainNav"
          aria-controls="mainNav"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span class="navbar-toggler-icon"></span>
        </button>

        <!-- Links -->
        <div class="collapse navbar-collapse" id="mainNav">
          <ul class="navbar-nav ms-auto mb-2 mb-lg-0 gap-lg-2">
            <li class="nav-item">
              <a
                class="nav-link fw-medium"
                :class="{ active: activeView === 'format' }"
                :aria-current="activeView === 'format' ? 'page' : undefined"
                href="#"
                @click.prevent="activeView = 'format'"
              >
                Formatear
              </a>
            </li>
            <li class="nav-item">
              <a
                class="nav-link fw-medium"
                :class="{ active: activeView === 'history' }"
                :aria-current="activeView === 'history' ? 'page' : undefined"
                href="#"
                @click.prevent="activeView = 'history'"
              >
                Historial
              </a>
            </li>
            <li class="nav-item">
              <a
                class="nav-link fw-medium"
                :class="{ active: activeView === 'settings' }"
                href="#"
                @click.prevent="activeView = 'settings'"
              >
                Configuración
              </a>
            </li>
          </ul>
        </div>
      </div>
    </nav>

    <!-- Contenido -->
    <div class="container py-4">
      <template v-if="activeView === 'format'">
        <!-- Subtítulo -->
        <p class="text-secondary text-center mb-4" style="font-size: 0.9em">
          Formateo profesional de documentos a sólo un par de clicks...
        </p>

        <!-- Dropzone -->
        <FileDropzone />
      </template>

      <template v-else-if="activeView === 'history'">
        <HistoryView />
      </template>
    </div>
  </div>
</template>