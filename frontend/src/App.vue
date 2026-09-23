<script setup lang="ts">
import FileDropzone from "@/components/FileDropzone.vue";
</script>

<template>
  <div class="min-vh-100 bg-light">
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg bg-white border-bottom">
      <div class="container-fluid px-4">
        <!-- Logo -->
        <a class="navbar-brand fw-bold fs-4 text-primary mb-0" href="#">
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
              <a class="nav-link active fw-medium" aria-current="page" href="#">
                Formatear
              </a>
            </li>
            <li class="nav-item">
              <a class="nav-link fw-medium" href="#">Historial</a>
            </li>
            <li class="nav-item">
              <a class="nav-link fw-medium" href="#">Configuración</a>
            </li>
          </ul>
        </div>
      </div>
    </nav>

    <!-- Contenido -->
    <div class="container py-4">
      <!-- Subtítulo -->
      <p class="text-secondary text-center mb-4" style="font-size: 0.9em">
        Formateo profesional de documentos a sólo un par de clicks...
      </p>

      <!-- Dropzone -->
      <FileDropzone />
    </div>
  </div>
</template>