const statusEls = {
  serviceStatus: document.getElementById("service-status"),
  lastError: document.getElementById("last-error"),
  lastSuccess: document.getElementById("last-success"),
  nextRun: document.getElementById("next-run"),
  recommendationTotal: document.getElementById("recommendation-total"),
  runCount: document.getElementById("run-count"),
  lastDuration: document.getElementById("last-duration"),
  generatedAt: document.getElementById("generated-at"),
  reportGeneratedAt: document.getElementById("report-generated-at"),
  reportSource: document.getElementById("report-source"),
  reportTotal: document.getElementById("report-total"),
  tierSummary: document.getElementById("tier-summary"),
  recommendationList: document.getElementById("recommendation-list"),
  recommendationCaption: document.getElementById("recommendation-caption"),
  runNowBtn: document.getElementById("run-now-btn"),
  pageSizeSelect: document.getElementById("page-size-select"),
  prevPageBtn: document.getElementById("prev-page-btn"),
  nextPageBtn: document.getElementById("next-page-btn"),
  pageIndicator: document.getElementById("page-indicator"),
  searchInput: document.getElementById("search-input"),
  tierFilterSelect: document.getElementById("tier-filter-select"),
  sortSelect: document.getElementById("sort-select"),
  jumpPageInput: document.getElementById("jump-page-input"),
  jumpPageBtn: document.getElementById("jump-page-btn"),
  viewSwitcher: document.getElementById("view-switcher"),
  strategySwitcher: document.getElementById("strategy-switcher"),
};

const uiState = {
  viewResults: {},
  strategyResults: {},
  currentView: "bullish",
  currentStrategy: "long_term",
  hasUserSelectedStrategy: false,
  filteredItems: [],
  currentPage: 1,
  pageSize: Number(statusEls.pageSizeSelect.value || 6),
  keyword: "",
  tier: "ALL",
  sortKey: "score_desc",
};

function formatTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function formatNumber(value, digits = 2) {
  return Number(value || 0).toFixed(digits);
}

function formatLiveCrossState(state) {
  switch (state) {
    case "weak_hold":
      return "弱保持";
    case "normal_hold":
      return "普通保持";
    case "strong_hold":
      return "强保持";
    case "confirmed_close":
      return "收盘确认";
    default:
      return "-";
  }
}

function getCurrentStrategyResult() {
  const currentView = uiState.viewResults[uiState.currentView];
  if (currentView && currentView.strategy_results) {
    return (
      currentView.strategy_results[uiState.currentStrategy] || {
        strategy_label: "\u957f\u7ebf",
        interval: "1d",
        recommendations: [],
        total: 0,
      }
    );
  }
  return (
    uiState.strategyResults[uiState.currentStrategy] || {
      strategy_label: "\u957f\u7ebf",
      interval: "1d",
      recommendations: [],
      total: 0,
    }
  );
}

function getStrategySource(viewKey = uiState.currentView) {
  const currentView = uiState.viewResults[viewKey];
  if (currentView && currentView.strategy_results) {
    return currentView.strategy_results;
  }
  return uiState.strategyResults || {};
}

function pickPreferredStrategy(viewKey = uiState.currentView, fallback = "long_term") {
  const source = getStrategySource(viewKey);
  const entries = Object.entries(source);
  if (!entries.length) {
    return fallback;
  }

  const preferred = entries.find(([, value]) => Number(value.total || 0) > 0);
  return preferred ? preferred[0] : entries[0][0] || fallback;
}

function renderViewSwitcher() {
  const entries = Object.entries(uiState.viewResults || {});
  if (!entries.length) {
    statusEls.viewSwitcher.innerHTML = "";
    return;
  }

  statusEls.viewSwitcher.innerHTML = entries
    .map(([key, value]) => {
      const active = key === uiState.currentView ? " active" : "";
      const label = value.view_label || (key === "bearish" ? "看跌" : "看涨");
      let total = 0;
      Object.values(value.strategy_results || {}).forEach((item) => {
        total += Number(item.total || 0);
      });
      return `
        <button class="strategy-chip${active}" type="button" data-view="${key}">
          <span>${label}</span>
          <small>方向</small>
          <strong>${total}</strong>
        </button>
      `;
    })
    .join("");

  statusEls.viewSwitcher.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => {
      uiState.currentView = button.dataset.view;
      uiState.currentStrategy = pickPreferredStrategy(uiState.currentView, uiState.currentStrategy);
      uiState.currentPage = 1;
      applyFiltersAndSort();
      renderViewSwitcher();
      renderStrategySwitcher();
      updateStrategyOverview();
    });
  });
}

function renderTierSummary(tierSummary) {
  const entries = Object.entries(tierSummary || {});
  if (!entries.length) {
    statusEls.tierSummary.innerHTML = '<div class="empty">\u6682\u65e0\u7edf\u8ba1\u6570\u636e</div>';
    return;
  }

  statusEls.tierSummary.innerHTML = entries
    .map(
      ([tier, count]) => `
        <div class="tier-chip">
          <span>${tier}</span>
          <strong>${count}</strong>
        </div>
      `
    )
    .join("");
}

function buildCurrentTierSummary() {
  const current = getCurrentStrategyResult();
  const summary = {};
  (current.recommendations || []).forEach((item) => {
    summary[item.tier] = (summary[item.tier] || 0) + 1;
  });
  return summary;
}

function updateStrategyOverview() {
  const current = getCurrentStrategyResult();
  statusEls.recommendationTotal.textContent = current.total || 0;
  statusEls.reportTotal.textContent = current.total || 0;
  renderTierSummary(buildCurrentTierSummary());
}

function renderStrategySwitcher() {
  const source =
    (uiState.viewResults[uiState.currentView] || {}).strategy_results || uiState.strategyResults;
  const entries = Object.entries(source);
  if (!entries.length) {
    statusEls.strategySwitcher.innerHTML = "";
    return;
  }

  statusEls.strategySwitcher.innerHTML = entries
    .map(([key, value]) => {
      const active = key === uiState.currentStrategy ? " active" : "";
      return `
        <button class="strategy-chip${active}" type="button" data-strategy="${key}">
          <span>${value.strategy_label}</span>
          <small>${value.interval}</small>
          <strong>${value.total || 0}</strong>
        </button>
      `;
    })
    .join("");

  statusEls.strategySwitcher.querySelectorAll("[data-strategy]").forEach((button) => {
    button.addEventListener("click", () => {
      uiState.currentStrategy = button.dataset.strategy;
      uiState.hasUserSelectedStrategy = true;
      uiState.currentPage = 1;
      applyFiltersAndSort();
      renderStrategySwitcher();
      updateStrategyOverview();
    });
  });
}

function getSortValue(item, sortKey) {
  const signal = item.signal || {};
  switch (sortKey) {
    case "score_asc":
    case "score_desc":
      return Number(item.score || 0);
    case "change_desc":
      return Number(signal.market_change_24h || 0);
    case "trend_desc":
      return Number(signal.trend_strength || 0);
    case "confidence_desc":
      return Number(signal.confidence || 0);
    default:
      return Number(item.score || 0);
  }
}

function applyFiltersAndSort() {
  const keyword = uiState.keyword.trim().toUpperCase();
  const tier = uiState.tier;
  const sortKey = uiState.sortKey;
  const strategyResult = getCurrentStrategyResult();

  let items = [...(strategyResult.recommendations || [])];

  if (keyword) {
    items = items.filter((item) => String(item.symbol || "").toUpperCase().includes(keyword));
  }

  if (tier !== "ALL") {
    items = items.filter((item) => item.tier === tier);
  }

  items.sort((a, b) => {
    const aValue = getSortValue(a, sortKey);
    const bValue = getSortValue(b, sortKey);
    return sortKey.endsWith("_asc") ? aValue - bValue : bValue - aValue;
  });

  uiState.filteredItems = items;
  uiState.currentPage = 1;
  renderRecommendations();
}

function buildRecommendationCard(item, index) {
  const signal = item.signal || {};
  const liveState = formatLiveCrossState(signal.live_cross_state);
  const liveGapRatio = Number(signal.live_gap_ratio || 0) * 100;
  const reasons = (item.reasons || []).slice(0, 3).join("；");
  const consistency = item.consistency_summary || signal.consistency_summary || "";
  const consistencyHtml = consistency ? `<p class="consistency">${consistency}</p>` : "";

  return `
    <article class="recommendation-card">
      <div class="recommendation-head">
        <div class="coin-head">
          <span class="rank">#${index + 1}</span>
          <h3>${item.symbol}</h3>
          <p class="summary">${item.summary || ""}</p>
        </div>
        <div class="score-wrap">
          <span class="tier">${item.tier}</span>
          <strong>${formatNumber(item.score)}</strong>
        </div>
      </div>
      <div class="recommendation-grid">
        <div class="metrics">
          <span>方向: ${signal.view_label || (signal.market_view === "bearish" ? "看跌" : "看涨")}</span>
          <span>\u5468\u671f: ${signal.strategy_label || "-"} / ${signal.timeframe || "-"}</span>
          <span>\u73b0\u4ef7: ${formatNumber(signal.current_price, 4)}</span>
          <span>24h涨跌: ${formatNumber(signal.market_change_24h)}%</span>
          <span>\u8d8b\u52bf: ${formatNumber(signal.trend_strength, 1)}</span>
          <span>\u7f6e\u4fe1\u5ea6: ${formatNumber(signal.confidence, 1)}%</span>
          <span>\u4ea4\u53c9: ${signal.cross_label || "-"}</span>
          <span>\u4ea4\u53c9\u65f6\u95f4: ${signal.cross_time || "-"}</span>
          <span>\u5b9e\u65f6\u72b6\u6001: ${liveState}</span>
          <span>\u7ad9\u4e0a\u5e45\u5ea6: ${formatNumber(liveGapRatio, 2)}%</span>
          <span>\u57fa\u7840\u5206: ${formatNumber(item.base_score ?? signal.base_recommendation_score)}</span>
          <span>\u52a0\u5206: +${formatNumber(item.consistency_bonus ?? signal.consistency_bonus)}</span>
        </div>
        <div class="detail-stack">
          ${consistencyHtml}
          <p class="reasons"><strong>\u63a8\u8350\u7406\u7531:</strong> ${reasons || "\u65e0"}</p>
          <p class="risk"><strong>\u98ce\u9669\u6458\u8981:</strong> ${item.risk_summary || "\u65e0"}</p>
        </div>
      </div>
    </article>
  `;
}

function renderPagination() {
  const totalItems = uiState.filteredItems.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / uiState.pageSize));
  uiState.currentPage = Math.min(uiState.currentPage, totalPages);

  statusEls.pageIndicator.textContent = `\u7b2c ${uiState.currentPage} / ${totalPages} \u9875`;
  statusEls.prevPageBtn.disabled = uiState.currentPage <= 1;
  statusEls.nextPageBtn.disabled = uiState.currentPage >= totalPages;
  statusEls.jumpPageInput.max = String(totalPages);
}

function renderRecommendations() {
  const strategyResult = getCurrentStrategyResult();
  const list = uiState.filteredItems;
  const total = list.length;

  statusEls.recommendationCaption.textContent = `${
    strategyResult.strategy_label || "\u5f53\u524d"
  }\u5217\u8868\uff0c\u7b5b\u9009\u540e ${total} \u6761`;

  if (!total) {
    statusEls.pageIndicator.textContent = "\u7b2c 0 / 0 \u9875";
    statusEls.prevPageBtn.disabled = true;
    statusEls.nextPageBtn.disabled = true;
    statusEls.recommendationList.innerHTML =
      '<div class="empty">\u5f53\u524d\u7b5b\u9009\u6761\u4ef6\u4e0b\u65e0\u7ed3\u679c</div>';
    return;
  }

  const start = (uiState.currentPage - 1) * uiState.pageSize;
  const end = start + uiState.pageSize;
  const currentItems = list.slice(start, end);

  statusEls.recommendationList.innerHTML = currentItems
    .map((item, idx) => buildRecommendationCard(item, start + idx))
    .join("");

  renderPagination();
}

function updateRecommendationItems(payload) {
  uiState.viewResults = payload.view_results || {};
  uiState.strategyResults = payload.strategy_results || {};
  const defaultView = payload.default_view || "bullish";
  if (!uiState.viewResults[uiState.currentView] && uiState.viewResults[defaultView]) {
    uiState.currentView = defaultView;
  }
  const defaultStrategy = payload.default_strategy || "long_term";
  const currentSource = getStrategySource(uiState.currentView);
  const currentExists = Boolean(currentSource[uiState.currentStrategy]);

  if (!uiState.hasUserSelectedStrategy) {
    uiState.currentStrategy = pickPreferredStrategy(uiState.currentView, defaultStrategy);
  } else if (!currentExists) {
    uiState.currentStrategy = pickPreferredStrategy(uiState.currentView, defaultStrategy);
  }
  renderViewSwitcher();
  renderStrategySwitcher();
  applyFiltersAndSort();
  updateStrategyOverview();
}

async function loadStatus() {
  const response = await fetch("/api/status", { cache: "no-store" });
  const payload = await response.json();
  const service = payload.service || {};
  const summary = payload.summary || {};

  statusEls.serviceStatus.textContent = service.running ? "\u8fd0\u884c\u4e2d" : "\u7a7a\u95f2";
  statusEls.lastError.textContent = `\u6700\u8fd1\u9519\u8bef\uff1a${service.last_error || "\u65e0"}`;
  statusEls.lastSuccess.textContent = formatTime(service.last_success_at);
  statusEls.nextRun.textContent = `\u4e0b\u6b21\u6267\u884c\uff1a${formatTime(service.next_run_at)}`;
  statusEls.recommendationTotal.textContent = summary.recommendation_total || 0;
  statusEls.runCount.textContent = `\u8fd0\u884c\u6b21\u6570\uff1a${service.run_count || 0}`;
  statusEls.lastDuration.textContent = `${service.last_duration_seconds || 0}\u79d2`;
  statusEls.generatedAt.textContent = `\u6570\u636e\u65f6\u95f4\uff1a${formatTime(summary.generated_at)}`;
  statusEls.reportGeneratedAt.textContent = formatTime(summary.generated_at);
  statusEls.reportSource.textContent = `\u6765\u6e90\u6587\u4ef6\uff1a${summary.latest_file || "-"}`;
  statusEls.reportTotal.textContent = summary.recommendation_total || 0;
}

async function loadRecommendations() {
  const response = await fetch("/api/recommendations", { cache: "no-store" });
  const payload = await response.json();
  updateRecommendationItems(payload);
}

async function refreshAll() {
  await Promise.all([loadStatus(), loadRecommendations()]);
}

statusEls.runNowBtn.addEventListener("click", async () => {
  statusEls.runNowBtn.disabled = true;
  statusEls.runNowBtn.textContent = "\u6267\u884c\u4e2d...";
  try {
    const response = await fetch("/api/run", { method: "POST" });
    const payload = await response.json();
    alert(payload.message);
  } catch (error) {
    alert(`\u89e6\u53d1\u5931\u8d25\uff1a${error}`);
  } finally {
    statusEls.runNowBtn.disabled = false;
    statusEls.runNowBtn.textContent = "\u7acb\u5373\u6267\u884c\u4e00\u6b21";
    setTimeout(refreshAll, 1200);
  }
});

statusEls.pageSizeSelect.addEventListener("change", () => {
  uiState.pageSize = Number(statusEls.pageSizeSelect.value);
  uiState.currentPage = 1;
  renderRecommendations();
});

statusEls.prevPageBtn.addEventListener("click", () => {
  if (uiState.currentPage > 1) {
    uiState.currentPage -= 1;
    renderRecommendations();
  }
});

statusEls.nextPageBtn.addEventListener("click", () => {
  const totalPages = Math.max(1, Math.ceil(uiState.filteredItems.length / uiState.pageSize));
  if (uiState.currentPage < totalPages) {
    uiState.currentPage += 1;
    renderRecommendations();
  }
});

statusEls.jumpPageBtn.addEventListener("click", () => {
  const totalPages = Math.max(1, Math.ceil(uiState.filteredItems.length / uiState.pageSize));
  const page = Number(statusEls.jumpPageInput.value);
  if (!Number.isInteger(page) || page < 1 || page > totalPages) {
    alert(`\u8bf7\u8f93\u5165 1 \u5230 ${totalPages} \u4e4b\u95f4\u7684\u9875\u7801`);
    return;
  }
  uiState.currentPage = page;
  renderRecommendations();
});

statusEls.searchInput.addEventListener("input", () => {
  uiState.keyword = statusEls.searchInput.value;
  applyFiltersAndSort();
});

statusEls.tierFilterSelect.addEventListener("change", () => {
  uiState.tier = statusEls.tierFilterSelect.value;
  applyFiltersAndSort();
});

statusEls.sortSelect.addEventListener("change", () => {
  uiState.sortKey = statusEls.sortSelect.value;
  applyFiltersAndSort();
});

refreshAll();
setInterval(refreshAll, 30000);
