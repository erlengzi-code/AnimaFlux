// Mind 页面（§12.4 / §39.14）：13 Core State 的只读视图，按 3 组排列（STABLE SELF / ACTIVE MIND / LIFE CONTEXT）。

import { api, ApiError } from "../api.js";
import { el, clear, empty, loading, pageHead, openDrawer } from "../ui.js";
import { renderGeneric, stateSummary } from "../renderers.js";
import { t } from "../i18n.js";

// 13 个冻结 Core State 的展示分组 + 图标（图标仅作视觉区分，不承载语义）。
const GROUPS = [
  { labelKey: "group.stable", items: ["identity", "personality", "value", "self_model", "narrative"] },
  { labelKey: "group.active", items: ["emotion", "drive", "belief", "goal"] },
  { labelKey: "group.context", items: ["body", "memory", "relationship", "world_model"] },
];

const ICONS = {
  identity: "◉", personality: "✦", value: "♡", self_model: "◇", narrative: "⌁",
  emotion: "☺", drive: "⚡", belief: "◐", goal: "◎",
  body: "✚", memory: "◈", relationship: "♙", world_model: "⌂",
};

// 前端按 namespace 给出展示名（覆盖后端「身份 Identity」混合文案，随语言切换）。
function stateName(ns) {
  return t(`state.${ns}`) || ns;
}

function stateItem(namespace, displayName, summary, seeded, onOpen) {
  const item = el("div", "state-item");
  const ico = el("div", "state-ico", ICONS[namespace] || "·");
  item.appendChild(ico);
  const body = el("div", "");
  body.appendChild(el("b", "", displayName));
  body.appendChild(el("small", "", seeded ? (summary || t("mind.initialized")) : t("mind.uninitialized")));
  item.appendChild(body);
  item.appendChild(el("div", "chev", "›"));
  item.addEventListener("click", onOpen);
  return item;
}

export async function renderMind(app, { lifeId }) {
  loading(app);

  let states;
  try {
    states = await api.listStates(lifeId);
  } catch (e) {
    clear(app).appendChild(empty(e instanceof ApiError ? e.message : String(e)));
    return;
  }
  const byNs = Object.fromEntries(states.map((s) => [s.namespace, s]));

  clear(app);
  app.appendChild(pageHead(t("mind.title"), t("mind.subtitle")));

  const grid = el("div", "mind-groups");
  for (const group of GROUPS) {
    const card = el("section", "card group-card");
    card.appendChild(el("div", "group-label", t(group.labelKey)));
    const list = el("div", "state-list");
    for (const ns of group.items) {
      const s = byNs[ns];
      if (!s) continue;
      const item = stateItem(ns, stateName(ns), "", s.seeded, async () => {
        let data = null;
        if (s.seeded) {
          const full = await api.getState(lifeId, ns);
          data = full.data;
        }
        const summary = stateSummary(ns, data);
        const body = el("div", "why");
        body.appendChild(el("div", "why-sec", stateName(ns)));
        if (summary) body.appendChild(el("div", "kv-value", summary));
        body.appendChild(renderGeneric(data ?? { seeded: false }));
        openDrawer(stateName(ns), body);
      });
      // 异步补一句话摘要
      if (s.seeded) {
        api.getState(lifeId, ns).then((full) => {
          const summary = stateSummary(ns, full.data);
          const small = item.querySelector("small");
          small.textContent = summary || t("mind.initialized");
        }).catch(() => {});
      }
      list.appendChild(item);
    }
    card.appendChild(list);
    grid.appendChild(card);
  }
  app.appendChild(grid);
}
