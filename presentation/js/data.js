/* ==========================================================================
   PrettyDocs — Fuente Única de Verdad de Datos y Placeholders (100 % Offline)
   --------------------------------------------------------------------------
   INSTRUCCIONES ANTES DE EXPONER:
   1. Actualiza los valores en `metricsPlaceholder` cuando tengas el reporte
      final de cobertura y evaluación con modelo real (S3T19).
   2. Cambia `isPlaceholder: false` para activar el renderizado definitivo
      (las barras y tarjetas se actualizarán y animarán automáticamente).
   ========================================================================== */

window.PrettyDocsPresentation = window.PrettyDocsPresentation || {};

const PRESENTATION_DATA = {
  // === DATOS REALES DEL SPRINT 3 (JIRA: 25/25 TAREAS) ===
  sprint3: {
    plannedTasks: 25,
    completedTasks: 25,
    milestones: [
      { date: '5 nov', label: 'Integración S2', added: 6, planned: 6, cumulative: 6 },
      { date: '10–12 nov', label: 'Motor + Vistas', added: 9, planned: 15, cumulative: 15 },
      { date: '22–23 nov', label: 'IA + Validador + QA', added: 10, planned: 25, cumulative: 25 }
    ],
    byMember: [
      { initials: 'AG', name: 'Alfonso Marón', role: 'Frontend Vue 3', tasks: 6 },
      { initials: 'RG', name: 'Roberto Cisneros', role: 'IA / Plantillas / API', tasks: 6 },
      { initials: 'LC', name: 'Luis Dorian', role: 'Motor DOCX / Orquestador', tasks: 6 },
      { initials: 'LS', name: 'Luis Arturo', role: 'QA / Evaluación IA', tasks: 4 },
      { initials: 'OC', name: 'Oscar Corona', role: 'Líder / Proveedor IA / QA', tasks: 3 }
    ]
  },

  // === MÉTRICAS DE PRUEBAS Y PLACEHOLDERS EDITABLES ===
  // Nota: `backendTestsPassed` (241) y `frontendTestsPassed` (12) reflejan el
  // conteo real verificado en el repositorio el 22/11/2026. Puedes actualizarlos
  // junto con cobertura y evaluación IA, y poner `isPlaceholder: false` al cerrar.
  metricsPlaceholder: {
    isPlaceholder: true,
    sprint2BaselineTests: 61,                 // Dato confirmado del Sprint 2
    backendTestsPassed: 241,                  // Verificado con pytest (241 passed, 1 live deselected)
    frontendTestsPassed: 12,                  // Verificado en frontend/src/**/__tests__/*.spec.js
    codeCoveragePct: '{{XX}}%',               // Ej: '86%'
    integrityScorePct: '{{100}}%',            // Meta obligatoria: 100% en corpus completo
    aiModelUsed: '{{MODELO_OPENROUTER}}',     // Ej: 'Gemini 2.0 Flash vía OpenRouter'
    evaluationComparison: [
      // Sustituir `null` por números (0–100) al concluir scripts/evaluate_ai.py (S3T19)
      { metric: 'Integridad', target: 100, heuristic: null, aiModel: null, placeholderLabel: '{{%}}' },
      { metric: 'Títulos', target: 85, heuristic: null, aiModel: null, placeholderLabel: '{{%}}' },
      { metric: 'Listas', target: 85, heuristic: null, aiModel: null, placeholderLabel: '{{%}}' },
      { metric: 'Tablas', target: 70, heuristic: null, aiModel: null, placeholderLabel: '{{%}}' },
      { metric: 'Respaldo ≤10%', target: 10, heuristic: null, aiModel: null, placeholderLabel: '{{%}}', lowerIsBetter: true }
    ]
  }
};

window.PrettyDocsPresentation.DATA = PRESENTATION_DATA;
