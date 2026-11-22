<script setup lang="ts">
import { reactive, ref } from 'vue'
import {
  DOCUMENT_THEMES,
  loadUserPrefs,
  saveUserPrefs
} from '@/constants/documentThemes'

const initial = loadUserPrefs()
const prefs = reactive({
  defaultTheme: initial.defaultTheme || 'azul_ejecutivo',
  defaultEmphasis: initial.defaultEmphasis || 'medio',
  showDividers: initial.showDividers ?? true
})

const savedNotice = ref(false)

function save() {
  saveUserPrefs({ ...prefs })
  savedNotice.value = true
  setTimeout(() => {
    savedNotice.value = false
  }, 2500)
}
</script>

<template>
  <div class="container-fluid settings-container px-0">
    <h2 class="fw-bold text-dark mb-1">Preferencias de diseño</h2>
    <p class="text-secondary mb-4">
      Define tus valores predeterminados al configurar nuevos documentos Word.
    </p>

    <div class="card pd-card p-4 mb-4">
      <h5 class="fw-bold text-dark mb-3">Valores por defecto en la configuración</h5>

      <div class="mb-4">
        <label class="form-label fw-semibold small d-block mb-2">Paleta cromática predeterminada para Word</label>
        <div class="row g-2">
          <div v-for="theme in DOCUMENT_THEMES" :key="theme.id" class="col-6 col-md-4">
            <button
              type="button"
              class="pref-theme-btn w-100 text-start p-3 rounded-3"
              :class="{ 'pref-theme-btn--active': prefs.defaultTheme === theme.id }"
              @click="prefs.defaultTheme = theme.id"
            >
              <div class="d-flex align-items-center gap-1 mb-2">
                <span class="swatch-lg" :style="{ backgroundColor: theme.primary }"></span>
                <span class="swatch-sm" :style="{ backgroundColor: theme.secondary }"></span>
                <span class="swatch-sm" :style="{ backgroundColor: theme.headerFill }"></span>
              </div>
              <div class="fw-bold text-dark small">{{ theme.name }}</div>
              <div class="text-secondary" style="font-size: 0.72rem">{{ theme.tagline }}</div>
            </button>
          </div>
        </div>
      </div>

      <div class="row g-3 mb-4">
        <div class="col-md-6">
          <label for="pref-emphasis" class="form-label fw-semibold small">Nivel de énfasis (negritas con IA)</label>
          <select id="pref-emphasis" v-model="prefs.defaultEmphasis" class="form-select">
            <option value="ninguno">Ninguno (sin negritas nuevas)</option>
            <option value="ligero">Ligero (solo etiquetas clave)</option>
            <option value="medio">Medio (etiquetas y conceptos principales)</option>
          </select>
        </div>
        <div class="col-md-6 d-flex align-items-end">
          <div class="form-check form-switch mb-2">
            <input id="pref-dividers" v-model="prefs.showDividers" class="form-check-input" type="checkbox" />
            <label class="form-check-label small fw-semibold" for="pref-dividers">
              Activar barras divisorias y acentos por defecto
            </label>
          </div>
        </div>
      </div>

      <div class="d-flex align-items-center gap-3">
        <button class="btn pd-btn-brand px-4" @click="save">Guardar preferencias</button>
        <span v-if="savedNotice" class="badge rounded-pill text-bg-success px-3 py-2">
          ✓ Preferencias guardadas
        </span>
      </div>
    </div>

    <div class="card pd-card p-4">
      <h5 class="fw-bold text-dark mb-2">Garantías activas del motor de integridad</h5>
      <p class="small text-secondary mb-3">
        Estas reglas se ejecutan automáticamente por código en el backend antes de generar cualquier archivo Word.
      </p>
      <div class="row g-3 small">
        <div class="col-md-4">
          <div class="p-3 rounded-3 bg-light border h-100">
            <div class="fw-bold text-dark mb-1">Cifras y monedas exactas</div>
            <div class="text-secondary">Verificación estricta de números, decimales, porcentajes y símbolos de moneda.</div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="p-3 rounded-3 bg-light border h-100">
            <div class="fw-bold text-dark mb-1">Bloques opacos intactos</div>
            <div class="text-secondary">Imágenes, tablas previas, ecuaciones y saltos de sección se copian desde el XML original.</div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="p-3 rounded-3 bg-light border h-100">
            <div class="fw-bold text-dark mb-1">Respaldo automático</div>
            <div class="text-secondary">Si el modelo falla la integridad tras 1 reintento, el estructurador heurístico garantiza la entrega.</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-container {
  max-width: 960px;
  margin: 0 auto;
}

.pref-theme-btn {
  border: 2px solid #e2e8f0;
  background: #fff;
  cursor: pointer;
  transition: all 0.15s ease;
}

.pref-theme-btn--active {
  border-color: #0f172a;
  background: #f8fafc;
}

.swatch-lg {
  width: 20px;
  height: 20px;
  border-radius: 999px;
  display: inline-block;
}

.swatch-sm {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  display: inline-block;
  border: 1px solid rgba(15, 23, 42, 0.12);
}
</style>
