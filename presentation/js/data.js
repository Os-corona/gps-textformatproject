/* ==========================================================================
   PrettyDocs — Fuente Única de Verdad de Datos Finales (100 % Offline)
   Todos los números han sido verificados contra el repositorio y OpenRouter.
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

  // === MÉTRICAS REALES DE CALIDAD Y EVALUACIÓN (VERIFICADAS 22/11/2026) ===
  metricsPlaceholder: {
    isPlaceholder: false,
    sprint2BaselineTests: 61,                 // Base Sprint 2
    backendTestsPassed: 430,                  // pytest --ds=core.test_settings (430 passed, 1 live deselected)
    frontendTestsPassed: 12,                  // vitest specs (ReviewView, ResultView, api.mocks)
    codeCoveragePct: '91.1%',                 // ai_engine: 90.2% · docx_engine: 92.4% (medido con sys.monitoring)
    coverageDetail: 'ai_engine 90.2% · docx_engine 92.4%',
    integrityScorePct: '100%',                // 8/8 documentos del corpus S3T23 con integridad verificada
    aiModelUsed: 'openai/gpt-6-luna · OpenRouter',
    evaluationComparison: [
      // Resultados reales sobre el corpus curado S3T23 (8 documentos)
      { metric: 'Integridad', target: 100, heuristic: 100, aiModel: 100 },
      { metric: 'Títulos', target: 85, heuristic: 100, aiModel: 100 },
      { metric: 'Listas', target: 85, heuristic: 100, aiModel: 100 },
      { metric: 'Tablas', target: 70, heuristic: 67, aiModel: 67 },
      { metric: 'Respaldo ≤10%', target: 10, heuristic: 0, aiModel: 12.5, lowerIsBetter: true }
    ]
  },

  // === TELEMETRÍA REAL DE COSTO Y TOKENS (DASHBOARD OPENROUTER) ===
  costTelemetry: {
    totalSpendUsd: '$0.19',
    totalDocuments: 25,
    totalRequests: 77,
    tokenVolumeLabel: '1.28M',
    cacheHitRatePct: '41.8%',
    blendedPricePer1M: '$0.15',
    costPerDocUsd: '~$0.008',
    // Comparativa por documento típico (~5 páginas, ~3 chunks/requests)
    comparison: {
      chatTokens: 48000,            // Chat multi-turno (4-5 iteraciones reenviando historial + texto reescrito)
      prettyDocsTokens: 8845,       // Promedio del corpus (1 pasada JSON sin XML/imágenes)
      chat100DocsCostUsd: 20.0,     // Suscripción mensual típica de chat IA ($20 USD/mes)
      prettyDocs100DocsCostUsd: 0.76 // 100 docs × ($0.19 / 25 docs reales = $0.0076 USD/doc)
    }
  }
};

window.PrettyDocsPresentation.DATA = PRESENTATION_DATA;
