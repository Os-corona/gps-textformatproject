/* ==========================================================================
   PrettyDocs — Generador de Gráficas SVG Nativas (100 % Offline, sin CDNs)
   Renderiza dinámicamente los gráficos de las Diapositivas 07 y 09 desde data.js
   ========================================================================== */

(function () {
  const ns = (window.PrettyDocsPresentation = window.PrettyDocsPresentation || {});
  const SVG_NS = 'http://www.w3.org/2000/svg';

  function isPlaceholderValue(val) {
    if (val === null || val === undefined) return true;
    if (typeof val === 'string') {
      return val.includes('{{') || val.includes('}}') || val.trim() === '';
    }
    return false;
  }

  function escapeXml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ------------------------------------------------------------------------
     Slide 07 — Gráfica 1: Curva / Área acumulada del Sprint 3 (3 hitos)
     ------------------------------------------------------------------------ */
  function renderCumulativeChart(container, sprint3) {
    if (!container || !sprint3) return;
    const milestones = sprint3.milestones || [];
    const maxVal = Math.max(sprint3.plannedTasks || 25, ...milestones.map((m) => m.cumulative), 25);

    const W = 540;
    const H = 265;
    const padL = 50;
    const padR = 34;
    const padT = 26;
    const padB = 56;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    const points = [
      { date: 'Inicio', label: 'Arranque S3', cumulative: 0, planned: 0 },
      ...milestones
    ];

    const xAt = (i) => padL + (i / (points.length - 1)) * plotW;
    const yAt = (val) => padT + plotH - (val / maxVal) * plotH;

    // Líneas de grilla Y (0, 5, 10, 15, 20, 25)
    const ticks = [0, 5, 10, 15, 20, 25];
    const gridSvg = ticks
      .map((t) => {
        const y = yAt(t);
        return `
          <line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}"
                stroke="var(--border-subtle)" stroke-width="1" stroke-dasharray="${t === 0 ? '' : '4 4'}"/>
          <text x="${padL - 10}" y="${y + 5}" text-anchor="end"
                fill="var(--text-secondary)" font-size="14" font-family="var(--font-mono)">${t}</text>
        `;
      })
      .join('');

    const lineCoords = points.map((p, i) => `${xAt(i).toFixed(1)},${yAt(p.cumulative).toFixed(1)}`);
    const linePath = `M ${lineCoords.join(' L ')}`;
    const areaPath = `${linePath} L ${xAt(points.length - 1).toFixed(1)},${yAt(0).toFixed(1)} L ${xAt(0).toFixed(1)},${yAt(0).toFixed(1)} Z`;

    const plannedPath = `M ${xAt(0).toFixed(1)},${yAt(0).toFixed(1)} L ${xAt(points.length - 1).toFixed(1)},${yAt(maxVal).toFixed(1)}`;

    const dotsAndLabels = points
      .map((p, i) => {
        const cx = xAt(i);
        const cy = yAt(p.cumulative);
        const isFirst = i === 0;
        return `
          <g>
            <circle cx="${cx}" cy="${cy}" r="${isFirst ? 5 : 7}"
                    fill="var(--surface-card)" stroke="var(--pd-emerald)" stroke-width="3.5"/>
            ${
              !isFirst
                ? `<rect x="${cx - 20}" y="${cy - 32}" width="40" height="22" rx="6" fill="var(--pd-emerald)"/>
                   <text x="${cx}" y="${cy - 16}" text-anchor="middle" fill="#ffffff"
                         font-size="14" font-weight="800" font-family="var(--font-mono)">${p.cumulative}</text>`
                : ''
            }
            <text x="${cx}" y="${H - 28}" text-anchor="middle"
                  fill="var(--text-primary)" font-size="15" font-weight="700">${escapeXml(p.date)}</text>
            <text x="${cx}" y="${H - 10}" text-anchor="middle"
                  fill="var(--text-secondary)" font-size="13">${escapeXml(p.label)}</text>
          </g>
        `;
      })
      .join('');

    container.innerHTML = `
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Avance acumulado del Sprint 3">
        <defs>
          <linearGradient id="pd-area-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#00bd7e" stop-opacity="0.28"/>
            <stop offset="100%" stop-color="#00bd7e" stop-opacity="0.02"/>
          </linearGradient>
        </defs>
        ${gridSvg}
        <!-- Referencia lineal planeada -->
        <path d="${plannedPath}" fill="none" stroke="var(--text-secondary)" stroke-width="2"
              stroke-dasharray="6 5" opacity="0.55"/>
        <!-- Área completada -->
        <path d="${areaPath}" fill="url(#pd-area-grad)"/>
        <!-- Línea acumulada real animada -->
        <path d="${linePath}" fill="none" stroke="var(--pd-emerald)" stroke-width="4"
              stroke-linecap="round" stroke-linejoin="round"
              class="svg-draw" style="--path-len: 700; --draw-delay: 0.2s;"/>
        ${dotsAndLabels}
      </svg>
    `;
  }

  /* ------------------------------------------------------------------------
     Slide 07 — Gráfica 2: Barras horizontales por integrante (25 tareas)
     ------------------------------------------------------------------------ */
  function renderMemberChart(container, sprint3) {
    if (!container || !sprint3) return;
    const members = sprint3.byMember || [];
    const maxTasks = Math.max(...members.map((m) => m.tasks), 6);

    const W = 540;
    const H = 265;
    const rowH = H / members.length;
    const barStartX = 196;
    const maxBarW = 285;

    const rowsSvg = members
      .map((m, idx) => {
        const yCenter = idx * rowH + rowH / 2;
        const barW = Math.max(18, (m.tasks / maxTasks) * maxBarW);
        const barY = yCenter - 13;
        return `
          <g>
            <!-- Avatar con iniciales -->
            <circle cx="22" cy="${yCenter}" r="17" fill="var(--pd-emerald-soft)"
                    stroke="var(--pd-emerald)" stroke-width="1.5"/>
            <text x="22" y="${yCenter + 5}" text-anchor="middle"
                  fill="var(--pd-emerald-deep)" font-size="13" font-weight="800"
                  font-family="var(--font-mono)">${escapeXml(m.initials)}</text>
            <!-- Nombre y especialidad -->
            <text x="48" y="${yCenter - 2}" fill="var(--text-primary)"
                  font-size="16" font-weight="700">${escapeXml(m.name)}</text>
            <text x="48" y="${yCenter + 15}" fill="var(--text-secondary)"
                  font-size="13">${escapeXml(m.role)}</text>
            <!-- Pista de fondo -->
            <rect x="${barStartX}" y="${barY}" width="${maxBarW}" height="26" rx="8"
                  fill="var(--surface-mute)"/>
            <!-- Barra animada -->
            <rect x="${barStartX}" y="${barY}" width="${barW.toFixed(1)}" height="26" rx="8"
                  fill="var(--pd-emerald)" class="svg-bar-h" style="--bar-index: ${idx};"/>
            <!-- Valor numérico -->
            <text x="${barStartX + barW + 12}" y="${yCenter + 6}"
                  fill="var(--text-primary)" font-size="17" font-weight="800"
                  font-family="var(--font-mono)">${m.tasks}</text>
          </g>
        `;
      })
      .join('');

    container.innerHTML = `
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Distribución de tareas por integrante">
        ${rowsSvg}
      </svg>
    `;
  }

  /* ------------------------------------------------------------------------
     Slide 09 — KPI Cards de Calidad y Placeholders
     ------------------------------------------------------------------------ */
  function renderQualityKpis(metrics) {
    const map = [
      {
        id: 'kpi-backend-tests',
        value: metrics.backendTestsPassed,
        sub: `Base S2: ${metrics.sprint2BaselineTests} en verde`
      },
      {
        id: 'kpi-frontend-tests',
        value: metrics.frontendTestsPassed,
        sub: 'Vitest · Review / Result / Mocks'
      },
      {
        id: 'kpi-coverage',
        value: metrics.codeCoveragePct,
        sub: metrics.coverageDetail || 'ai_engine + docx_engine'
      },
      {
        id: 'kpi-integrity',
        value: metrics.integrityScorePct,
        sub: '8/8 casos del corpus S3T23'
      }
    ];

    map.forEach((item) => {
      const card = document.getElementById(item.id);
      if (!card) return;
      const valEl = card.querySelector('.kpi-value');
      const subEl = card.querySelector('.kpi-sub');
      const pending = isPlaceholderValue(item.value);

      if (valEl) valEl.textContent = pending ? String(item.value ?? '{{XX}}') : String(item.value);
      if (subEl) subEl.textContent = item.sub;

      card.classList.toggle('is-placeholder', pending);
      card.classList.toggle('kpi-card--accent', !pending);
    });

    const modelBadge = document.getElementById('eval-model-badge');
    if (modelBadge) {
      const modelVal = metrics.aiModelUsed;
      const pendingModel = isPlaceholderValue(modelVal);
      modelBadge.textContent = pendingModel ? `Modelo: ${modelVal}` : modelVal;
      modelBadge.className = pendingModel ? 'badge badge--amber' : 'badge badge--emerald';
    }

    const banner = document.getElementById('eval-placeholder-banner');
    if (banner) {
      const anyNull = (metrics.evaluationComparison || []).some(
        (row) => row.heuristic === null || row.aiModel === null
      );
      banner.hidden = !(metrics.isPlaceholder || anyNull);
    }
  }

  /* ------------------------------------------------------------------------
     Slide 09 — Gráfica agrupada SVG (Meta Plan vs. Heurístico vs. Modelo IA)
     ------------------------------------------------------------------------ */
  function renderEvaluationChart(container, metrics) {
    if (!container || !metrics) return;
    const rows = metrics.evaluationComparison || [];

    const W = 680;
    const H = 318;
    const padL = 48;
    const padR = 18;
    const padT = 36;
    const padB = 56;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    const yAt = (pct) => padT + plotH - (Math.max(0, Math.min(100, pct)) / 100) * plotH;

    // Grilla horizontal (0% - 100%)
    const gridTicks = [0, 25, 50, 75, 100];
    const gridSvg = gridTicks
      .map((t) => {
        const y = yAt(t);
        return `
          <line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}"
                stroke="var(--border-subtle)" stroke-width="1" stroke-dasharray="${t === 0 ? '' : '4 4'}"/>
          <text x="${padL - 8}" y="${y + 5}" text-anchor="end"
                fill="var(--text-secondary)" font-size="13" font-family="var(--font-mono)">${t}%</text>
        `;
      })
      .join('');

    const groupW = plotW / rows.length;
    const barW = 26;
    const gap = 8;

    const groupsSvg = rows
      .map((row, idx) => {
        const centerX = padL + idx * groupW + groupW / 2;
        const startX = centerX - (barW * 3 + gap * 2) / 2;

        // 1. Barra Meta del Plan (siempre real)
        const targetY = yAt(row.target);
        const targetH = Math.max(4, yAt(0) - targetY);

        // 2. Barra Heurístico (real o fantasma placeholder)
        const hasHeur = typeof row.heuristic === 'number' && !metrics.isPlaceholder;
        const heurVal = hasHeur ? row.heuristic : Math.max(18, Math.min(82, row.target * 0.72));
        const heurY = yAt(heurVal);
        const heurH = Math.max(6, yAt(0) - heurY);

        // 3. Barra Modelo IA (real o fantasma placeholder)
        const hasAi = typeof row.aiModel === 'number' && !metrics.isPlaceholder;
        const aiVal = hasAi ? row.aiModel : Math.max(20, Math.min(94, row.target * 0.9));
        const aiY = yAt(aiVal);
        const aiH = Math.max(6, yAt(0) - aiY);

        const x1 = startX;
        const x2 = startX + barW + gap;
        const x3 = startX + (barW + gap) * 2;

        return `
          <g>
            <!-- Línea punteada de meta por grupo -->
            <line x1="${x1 - 4}" y1="${targetY}" x2="${x3 + barW + 4}" y2="${targetY}"
                  stroke="var(--text-primary)" stroke-width="1.5" stroke-dasharray="3 3" opacity="0.45"/>

            <!-- Serie 1: Meta del Plan -->
            <rect x="${x1}" y="${targetY}" width="${barW}" height="${targetH}" rx="5"
                  fill="#2c3e50" class="svg-bar-v" style="--bar-index: ${idx * 3};"/>
            <text x="${x1 + barW / 2}" y="${targetY - 7}" text-anchor="middle"
                  fill="var(--text-primary)" font-size="13" font-weight="800"
                  font-family="var(--font-mono)">${row.target}%</text>

            <!-- Serie 2: Heurístico -->
            ${
              hasHeur
                ? `<rect x="${x2}" y="${heurY}" width="${barW}" height="${heurH}" rx="5"
                         fill="#64748b" class="svg-bar-v" style="--bar-index: ${idx * 3 + 1};"/>
                   <text x="${x2 + barW / 2}" y="${heurY - 7}" text-anchor="middle"
                         fill="var(--text-secondary)" font-size="13" font-weight="700"
                         font-family="var(--font-mono)">${row.heuristic}%</text>`
                : `<rect x="${x2}" y="${heurY}" width="${barW}" height="${heurH}" rx="5"
                         fill="rgba(217, 119, 6, 0.14)" stroke="#d97706" stroke-width="1.6"
                         stroke-dasharray="4 3" class="svg-bar-v" style="--bar-index: ${idx * 3 + 1};"/>
                   <text x="${x2 + barW / 2}" y="${heurY - 7}" text-anchor="middle"
                         fill="#d97706" font-size="11" font-weight="700"
                         font-family="var(--font-mono)">${escapeXml(row.placeholderLabel || '{{%}}')}</text>`
            }

            <!-- Serie 3: Modelo IA -->
            ${
              hasAi
                ? `<rect x="${x3}" y="${aiY}" width="${barW}" height="${aiH}" rx="5"
                         fill="#00bd7e" class="svg-bar-v" style="--bar-index: ${idx * 3 + 2};"/>
                   <text x="${x3 + barW / 2}" y="${aiY - 7}" text-anchor="middle"
                         fill="var(--pd-emerald-deep)" font-size="13" font-weight="800"
                         font-family="var(--font-mono)">${row.aiModel}%</text>`
                : `<rect x="${x3}" y="${aiY}" width="${barW}" height="${aiH}" rx="5"
                         fill="rgba(0, 189, 126, 0.12)" stroke="#d97706" stroke-width="1.6"
                         stroke-dasharray="4 3" class="svg-bar-v" style="--bar-index: ${idx * 3 + 2};"/>
                   <text x="${x3 + barW / 2}" y="${aiY - 7}" text-anchor="middle"
                         fill="#d97706" font-size="11" font-weight="700"
                         font-family="var(--font-mono)">${escapeXml(row.placeholderLabel || '{{%}}')}</text>`
            }

            <!-- Etiqueta del eje X -->
            <text x="${centerX}" y="${H - 22}" text-anchor="middle"
                  fill="var(--text-primary)" font-size="15" font-weight="700">${escapeXml(row.metric)}</text>
          </g>
        `;
      })
      .join('');

    const legendY = 14;
    const isPh = metrics.isPlaceholder || rows.some((r) => r.aiModel === null);

    container.innerHTML = `
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Comparativa de métricas Meta vs Heurístico vs Modelo IA">
        <!-- Leyenda superior -->
        <g font-size="14" font-weight="700">
          <rect x="${padL}" y="${legendY - 10}" width="14" height="14" rx="3" fill="#2c3e50"/>
          <text x="${padL + 20}" y="${legendY + 2}" fill="var(--text-primary)">Meta Plan S3</text>

          <rect x="${padL + 148}" y="${legendY - 10}" width="14" height="14" rx="3"
                fill="${isPh ? 'rgba(217,119,6,0.16)' : '#64748b'}"
                stroke="${isPh ? '#d97706' : 'none'}" stroke-dasharray="${isPh ? '3 2' : ''}"/>
          <text x="${padL + 168}" y="${legendY + 2}" fill="var(--text-secondary)">Heurístico${isPh ? ' (pend.)' : ''}</text>

          <rect x="${padL + 332}" y="${legendY - 10}" width="14" height="14" rx="3"
                fill="${isPh ? 'rgba(0,189,126,0.14)' : '#00bd7e'}"
                stroke="${isPh ? '#d97706' : 'none'}" stroke-dasharray="${isPh ? '3 2' : ''}"/>
          <text x="${padL + 352}" y="${legendY + 2}" fill="var(--text-primary)">Modelo IA${isPh ? ' (pend.)' : ''}</text>
        </g>

        ${gridSvg}
        ${groupsSvg}
      </svg>
    `;
  }

  /* ------------------------------------------------------------------------
     Slide 10 — Eficiencia de Costo y Tokens: PrettyDocs vs. Chat de IA
     ------------------------------------------------------------------------ */
  function renderCostTelemetry(cost) {
    if (!cost) return;
    const setText = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    setText('kpi-cost-spend', cost.totalSpendUsd);
    setText('kpi-cost-spend-sub', `${cost.totalDocuments} docs · ${cost.totalRequests} req · ${cost.tokenVolumeLabel} tok`);
    setText('kpi-cost-per-req', cost.costPerDocUsd);
    setText('kpi-cost-cache', cost.cacheHitRatePct);
    setText('kpi-cost-blended', `${cost.blendedPricePer1M}`);

    const container = document.getElementById('chart-cost-comparison');
    if (!container || !cost.comparison) return;

    const c = cost.comparison;
    const tokenReduction = Math.round((1 - c.prettyDocsTokens / c.chatTokens) * 100);
    const costFactor = Math.round(c.chat100DocsCostUsd / c.prettyDocs100DocsCostUsd);
    const W = 580;
    const H = 292;
    const barX = 18;
    const maxW = 438;

    const chatTokW = maxW;
    const pdTokW = Math.max(40, (c.prettyDocsTokens / c.chatTokens) * maxW);

    const chatCostW = maxW;
    const pdCostW = Math.max(26, (c.prettyDocs100DocsCostUsd / c.chat100DocsCostUsd) * maxW);

    container.innerHTML = `
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Comparativa de tokens y costo PrettyDocs vs Chat IA">
        <!-- Sección 1: Tokens por documento -->
        <text x="${barX}" y="20" fill="var(--text-primary)" font-size="15.5" font-weight="800">
          Tokens consumidos por documento (~5 págs.)
        </text>
        <rect x="444" y="3" width="124" height="24" rx="12" fill="var(--pd-emerald-soft)"/>
        <text x="506" y="19" text-anchor="middle" fill="var(--pd-emerald-deep)" font-size="13.5" font-weight="800">-${tokenReduction}% tokens</text>

        <!-- Barra Chat Tokens -->
        <text x="${barX}" y="47" fill="var(--text-secondary)" font-size="14" font-weight="700">Chat IA (4–5 turnos reenviando historial + reescritura)</text>
        <rect x="${barX}" y="54" width="${maxW}" height="24" rx="7" fill="var(--surface-mute)"/>
        <rect x="${barX}" y="54" width="${chatTokW.toFixed(1)}" height="24" rx="7"
              fill="#dc2626" fill-opacity="0.82" class="svg-bar-h" style="--bar-index: 0;"/>
        <text x="${barX + chatTokW + 10}" y="72" fill="#dc2626" font-size="15" font-weight="800" font-family="var(--font-mono)">~48k</text>

        <!-- Barra PrettyDocs Tokens -->
        <text x="${barX}" y="102" fill="var(--text-primary)" font-size="14" font-weight="700">PrettyDocs (bloques JSON sin XML ni imágenes keep)</text>
        <rect x="${barX}" y="109" width="${maxW}" height="24" rx="7" fill="var(--surface-mute)"/>
        <rect x="${barX}" y="109" width="${pdTokW.toFixed(1)}" height="24" rx="7"
              fill="#00bd7e" class="svg-bar-h" style="--bar-index: 1;"/>
        <text x="${barX + pdTokW + 10}" y="127" fill="var(--pd-emerald-deep)" font-size="15" font-weight="800" font-family="var(--font-mono)">~8.8k</text>

        <line x1="${barX}" y1="150" x2="${W - 12}" y2="150" stroke="var(--border-subtle)" stroke-dasharray="4 4"/>

        <!-- Sección 2: Costo estimado por 100 documentos -->
        <text x="${barX}" y="176" fill="var(--text-primary)" font-size="15.5" font-weight="800">
          Costo estimado (100 documentos / uso mensual)
        </text>
        <rect x="444" y="159" width="124" height="24" rx="12" fill="var(--pd-emerald-soft)"/>
        <text x="506" y="175" text-anchor="middle" fill="var(--pd-emerald-deep)" font-size="13.5" font-weight="800">~${costFactor}× menor</text>

        <!-- Barra Chat Costo -->
        <text x="${barX}" y="203" fill="var(--text-secondary)" font-size="14" font-weight="700">Plan Chat Pro (Gemini / Claude / ChatGPT)</text>
        <rect x="${barX}" y="210" width="${maxW}" height="22" rx="7" fill="var(--surface-mute)"/>
        <rect x="${barX}" y="210" width="${chatCostW.toFixed(1)}" height="22" rx="7"
              fill="#2c3e50" class="svg-bar-h" style="--bar-index: 2;"/>
        <text x="${barX + chatCostW + 10}" y="227" fill="var(--text-primary)" font-size="15" font-weight="800" font-family="var(--font-mono)">$20/mes</text>

        <!-- Barra PrettyDocs Costo -->
        <text x="${barX}" y="256" fill="var(--text-primary)" font-size="14" font-weight="700">PrettyDocs API (OpenRouter · ~$0.008/doc con caché)</text>
        <rect x="${barX}" y="263" width="${maxW}" height="20" rx="7" fill="var(--surface-mute)"/>
        <rect x="${barX}" y="263" width="${pdCostW.toFixed(1)}" height="20" rx="7"
              fill="#00bd7e" class="svg-bar-h" style="--bar-index: 3;"/>
        <text x="${barX + pdCostW + 10}" y="279" fill="var(--pd-emerald-deep)" font-size="15" font-weight="800" font-family="var(--font-mono)">~$${c.prettyDocs100DocsCostUsd.toFixed(2)} USD</text>
      </svg>
    `;
  }

  /* ------------------------------------------------------------------------
     API pública de charts.js
     ------------------------------------------------------------------------ */
  function renderAll(data) {
    if (!data) return;
    // Slide 07 KPIs
    const s3 = data.sprint3;
    const tasksEl = document.getElementById('kpi-s3-tasks');
    const pctEl = document.getElementById('kpi-s3-pct');
    const milestonesEl = document.getElementById('kpi-s3-milestones');
    const membersEl = document.getElementById('kpi-s3-members');

    const pct = s3.plannedTasks ? Math.round((s3.completedTasks / s3.plannedTasks) * 100) : 0;
    if (tasksEl) {
      tasksEl.dataset.countTarget = String(s3.completedTasks);
      tasksEl.dataset.countSuffix = ` / ${s3.plannedTasks}`;
      tasksEl.textContent = `${s3.completedTasks} / ${s3.plannedTasks}`;
    }
    if (pctEl) {
      pctEl.dataset.countTarget = String(pct);
      pctEl.dataset.countSuffix = '%';
      pctEl.textContent = `${pct}%`;
    }
    if (milestonesEl) milestonesEl.textContent = String(s3.milestones.length);
    if (membersEl) membersEl.textContent = String(s3.byMember.length);

    renderCumulativeChart(document.getElementById('chart-s3-cumulative'), s3);
    renderMemberChart(document.getElementById('chart-s3-members'), s3);

    // Slide 09 KPIs y gráfica comparativa
    renderQualityKpis(data.metricsPlaceholder);
    renderEvaluationChart(document.getElementById('chart-ai-evaluation'), data.metricsPlaceholder);

    // Slide 10 Costo y eficiencia de tokens
    renderCostTelemetry(data.costTelemetry);
  }

  ns.Charts = { renderAll, SVG_NS };
})();
