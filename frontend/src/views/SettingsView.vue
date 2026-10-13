<script setup lang="ts">
import { reactive } from "vue";

const settings = reactive({
  model: "gpt-4o",
  temperature: 0.4,
  saveHistory: true,
  outputLang: "es",
});

const models = [
  { id: "gpt-4o", name: "GPT-4o (OpenAI)" },
  { id: "claude-3-5-sonnet", name: "Claude 3.5 Sonnet (Anthropic)" },
  { id: "gemini-1-5-pro", name: "Gemini 1.5 Pro (Google)" },
  { id: "llama-3-70b", name: "Llama 3 70B (local)" },
];

const languages = [
  { id: "es", name: "Español" },
  { id: "en", name: "English" },
  { id: "pt", name: "Português" },
];

function save() {
  console.log("Settings guardados:", settings);
  alert("Configuración guardada (mock).");
}
</script>

<template>
  <div>
    <h2 class="fw-semibold mb-1">Configuración</h2>
    <p class="text-secondary mb-4">
      Ajusta el modelo de IA y preferencias generales.
    </p>

    <div class="card border-0 shadow-sm mb-3">
      <div class="card-body d-flex flex-column gap-3">
        <div>
          <label class="form-label fw-semibold">Modelo de IA</label>
          <select v-model="settings.model" class="form-select">
            <option v-for="m in models" :key="m.id" :value="m.id">
              {{ m.name }}
            </option>
          </select>
        </div>

        <div>
          <label class="form-label fw-semibold d-flex justify-content-between">
            <span>Creatividad (temperature)</span>
            <span class="text-secondary">{{ settings.temperature.toFixed(2) }}</span>
          </label>
          <input
            v-model.number="settings.temperature"
            type="range"
            min="0"
            max="1"
            step="0.05"
            class="form-range"
          />
          <div class="form-text">
            Valores bajos = más determinista. Valores altos = más creativo.
          </div>
        </div>

        <div>
          <label class="form-label fw-semibold">Idioma de salida</label>
          <select v-model="settings.outputLang" class="form-select">
            <option v-for="l in languages" :key="l.id" :value="l.id">
              {{ l.name }}
            </option>
          </select>
        </div>

        <div class="form-check form-switch">
          <input
            id="saveHistory"
            v-model="settings.saveHistory"
            class="form-check-input"
            type="checkbox"
          />
          <label for="saveHistory" class="form-check-label">
            Guardar historial automáticamente
          </label>
        </div>
      </div>
    </div>

    <button class="btn btn-primary" @click="save">Guardar cambios</button>
  </div>
</template>
