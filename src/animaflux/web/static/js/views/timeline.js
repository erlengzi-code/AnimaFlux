// Timeline 页面（§12.6 / §21.3 / §39.11）：只读历史回放（Exact Replay）+ Agency + 逐步查看。

import { api, ApiError } from "../api.js";
import { el, clear, empty, loading, pageHead, formatTime, openDrawer } from "../ui.js";
import { renderGeneric } from "../renderers.js";
import { t } from "../i18n.js";

// 相邻 Tick 相比，version_id 变化的 Namespace（第 0 个 Tick 视为全部为新增）。
function changedNamespaces(ticks, i) {
  const cur = ticks[i].version_map || {};
  if (i === 0) return Object.keys(cur).sort();
  const prev = ticks[i - 1].version_map || {};
  return Object.keys(cur).filter((ns) => cur[ns] !== prev[ns]).sort();
}

// 时间线筛选：按「哪部分心智发生了变化」过滤（真实 namespace，非虚构分类）。
const FILTERS = [
  ["timeline.filterAll", null],
  ["timeline.filterEmotion", "emotion"],
  ["timeline.filterGoal", "goal"],
  ["timeline.filterRelationship", "relationship"],
  ["timeline.filterMemory", "memory"],
  ["timeline.filterNarrative", "narrative"],
];
const COLORS = ["green", "purple", "orange", ""];

function agencyCard(rec) {
  const card = el("div", "agency");
  const head = el("div", "agency-head");
  const action = rec.selected_action_type || "NO_ACTION";
  head.appendChild(el("span", "agency-action", action));
  head.appendChild(el("span", "agency-time", rec.world_time ? formatTime(rec.world_time) : ""));
  card.appendChild(head);
  const why = el("div", "agency-why");
  const parts = [];
  if (rec.trigger_type) parts.push(t("timeline.trigger", { type: rec.trigger_type }));
  if (rec.expected_outcome) parts.push(String(rec.expected_outcome));
  if (rec.no_action_reason) parts.push(t("timeline.reason", { reason: rec.no_action_reason }));
  if (rec.confidence !== undefined && rec.confidence !== null) parts.push(t("timeline.confidence", { n: Number(rec.confidence).toFixed(2) }));
  why.textContent = parts.join(t("sep3"));
  card.appendChild(why);
  return card;
}

function tickEvent(tick, changed, colorClass) {
  const ev = el("div", `life-event ${colorClass}`);
  const card = el("div", "event-card");
  card.appendChild(el("div", "event-date", tick.runtime_time_after ? formatTime(tick.runtime_time_after) : ""));
  const mid = el("div", "");
  mid.appendChild(el("b", "", tick.tick_id));
  mid.appendChild(el("p", "", changed.length ? t("timeline.changed", { list: changed.join(", ") }) : t("timeline.noChange")));
  card.appendChild(mid);
  const whyBtn = el("button", "btn small", t("ui.view"));
  whyBtn.addEventListener("click", () => openDrawer(`Tick ${tick.tick_id}`, renderGeneric(tick.payloads || {})));
  card.appendChild(whyBtn);
  ev.appendChild(card);
  return ev;
}

export async function renderTimeline(app, { lifeId }) {
  loading(app);
  let ticks;
  let agency;
  try {
    [ticks, agency] = await Promise.all([api.timeline(lifeId), api.agency(lifeId)]);
  } catch (e) {
    clear(app).appendChild(empty(e instanceof ApiError ? e.message : String(e)));
    return;
  }

  clear(app);
  app.appendChild(pageHead("Timeline", t("timeline.subtitle", { n: ticks.length })));

  // Agency / 为什么这样做（§12E A8）
  const agencyPanel = el("section", "card", "");
  agencyPanel.style.padding = "18px 22px";
  agencyPanel.appendChild(el("div", "card-title", t("timeline.agencyTitle")));
  agencyPanel.appendChild(el("div", "page-sub", t("timeline.agencySub")));
  if (!agency.length) {
    agencyPanel.appendChild(el("div", "empty", t("timeline.noAgency")));
  } else {
    const agencyList = el("div", "agency-list");
    agency.forEach((r) => agencyList.appendChild(agencyCard(r)));
    agencyPanel.appendChild(agencyList);
  }
  app.appendChild(agencyPanel);

  // 时间线（筛选 + 竖线事件流）
  const timelineCard = el("section", "card timeline-card");
  const filters = el("div", "filters");
  let activeFilter = null;
  const line = el("div", "life-line");

  function drawLine() {
    clear(line);
    let rendered = 0;
    ticks.forEach((t, i) => {
      const changed = changedNamespaces(ticks, i);
      if (activeFilter && !changed.includes(activeFilter)) return;
      line.appendChild(tickEvent(t, changed, COLORS[rendered % COLORS.length]));
      rendered += 1;
    });
    if (!rendered) line.appendChild(el("div", "empty", t("timeline.filterNone")));
  }

  for (const [labelKey, ns] of FILTERS) {
    const f = el("button", "filter", t(labelKey));
    if (ns === null) f.classList.add("active");
    f.addEventListener("click", () => {
      activeFilter = ns;
      for (const b of filters.querySelectorAll(".filter")) b.classList.remove("active");
      f.classList.add("active");
      drawLine();
    });
    filters.appendChild(f);
  }
  timelineCard.appendChild(filters);
  timelineCard.appendChild(line);
  app.appendChild(timelineCard);

  if (!ticks.length) {
    drawLine();
  } else {
    drawLine();

    // 逐步查看（§39.11 step through history）
    const stepper = el("section", "card", "");
    stepper.style.padding = "18px 22px";
    stepper.appendChild(el("div", "card-title", t("timeline.stepTitle")));
    stepper.appendChild(el("div", "page-sub", t("timeline.stepSub")));
    const controls = el("div", "stepper");
    const prevBtn = el("button", "btn", t("timeline.prev"));
    const nextBtn = el("button", "btn", t("timeline.next"));
    const idxLabel = el("span", "stepper-idx", "");
    controls.appendChild(prevBtn);
    controls.appendChild(idxLabel);
    controls.appendChild(nextBtn);
    stepper.appendChild(controls);
    const detail = el("div", "stepper-detail");
    stepper.appendChild(detail);
    app.appendChild(stepper);

    let idx = 0;
    function show() {
      idxLabel.textContent = `${idx + 1} / ${ticks.length}`;
      prevBtn.disabled = idx === 0;
      nextBtn.disabled = idx === ticks.length - 1;
      clear(detail);
      detail.appendChild(renderGeneric(ticks[idx].payloads || {}));
    }
    prevBtn.addEventListener("click", () => { idx = Math.max(0, idx - 1); show(); });
    nextBtn.addEventListener("click", () => { idx = Math.min(ticks.length - 1, idx + 1); show(); });
    show();
  }
}
