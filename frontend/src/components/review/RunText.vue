<script setup lang="ts">
withDefaults(
  defineProps<{
    runs?: Array<{
      text?: string
      bold?: boolean | null
      italic?: boolean | null
      underline?: boolean | null
    }>
    fallback?: string
  }>(),
  {
    runs: () => [],
    fallback: ''
  }
)
</script>

<template>
  <template v-if="runs && runs.length">
    <template v-for="(run, index) in runs" :key="index">
      <!--
        Text always comes from Vue interpolation. `strong` is used for bold
        runs; italic/underline are rendered as safe utility classes.
      -->
      <component
        :is="run.bold ? 'strong' : 'span'"
        :class="{
          'fst-italic': run.italic,
          'text-decoration-underline': run.underline
        }"
      >{{ run.text }}</component>
    </template>
  </template>
  <template v-else>{{ fallback }}</template>
</template>
