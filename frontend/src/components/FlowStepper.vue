<script setup lang="ts">
const props = defineProps<{
  current: 1 | 2 | 3 | 4
}>()

const steps = [
  { id: 1, label: 'Subir Word' },
  { id: 2, label: 'Personalizar e IA' },
  { id: 3, label: 'Revisión IA' },
  { id: 4, label: 'Resultado' }
] as const
</script>

<template>
  <div class="pd-stepper" aria-label="Progreso del flujo">
    <template v-for="(step, idx) in steps" :key="step.id">
      <div
        class="pd-step"
        :class="{
          'pd-step--done': step.id < props.current,
          'pd-step--active': step.id === props.current
        }"
      >
        <span class="pd-step-dot">
          <template v-if="step.id < props.current">✓</template>
          <template v-else>{{ step.id }}</template>
        </span>
        <span>{{ step.label }}</span>
      </div>
      <div
        v-if="idx < steps.length - 1"
        class="pd-step-line"
        :class="{ 'pd-step-line--done': step.id < props.current }"
      ></div>
    </template>
  </div>
</template>
