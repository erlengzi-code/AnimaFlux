// 只读渲染器（§30 / §39.15 / §39.16）。
// - renderGeneric：任意 JSON-safe 值的折叠只读树（未知 Namespace 也走这里，绝不因插件报错）。
// - renderStateCard：13 State 的卡片（定制 headline + 全量只读树）。
// 一律 textContent，禁止 innerHTML 注入模型输出（§39.18）。

import { el, fmt } from "./ui.js";
import { t, vitalLabel } from "./i18n.js";

function toggleNode(root, label) {
  const btn = el("button", "tree-toggle", "▸");
  btn.addEventListener("click", () => {
    const open = root.classList.toggle("open");
    btn.textContent = open ? "▾" : "▸";
  });
  root.appendChild(btn);
  if (label !== undefined) root.appendChild(el("span", "tree-node-label", label));
}

function buildNode(container, value) {
  if (value === null || value === undefined) {
    container.appendChild(el("span", "tree-null", "null"));
  } else if (typeof value === "boolean") {
    container.appendChild(el("span", "tree-bool", String(value)));
  } else if (typeof value === "number") {
    container.appendChild(el("span", "tree-num", String(value)));
  } else if (typeof value === "string") {
    container.appendChild(el("span", "tree-str", value));
  } else if (Array.isArray(value)) {
    if (value.length === 0) {
      container.appendChild(el("span", "tree-empty", "[]"));
      return;
    }
    const root = el("div", "tree-node");
    toggleNode(root, `[${value.length}]`);
    const body = el("div", "tree-body");
    value.forEach((item, i) => {
      const row = el("div", "tree-row");
      row.appendChild(el("span", "tree-key", String(i)));
      buildNode(row, item);
      body.appendChild(row);
    });
    root.appendChild(body);
    container.appendChild(root);
  } else if (typeof value === "object") {
    const keys = Object.keys(value);
    if (keys.length === 0) {
      container.appendChild(el("span", "tree-empty", "{}"));
      return;
    }
    const root = el("div", "tree-node");
    toggleNode(root, `{${keys.length}}`);
    const body = el("div", "tree-body");
    keys.forEach((k) => {
      const row = el("div", "tree-row");
      row.appendChild(el("span", "tree-key", `${k}:`));
      buildNode(row, value[k]);
      body.appendChild(row);
    });
    root.appendChild(body);
    container.appendChild(root);
  } else {
    container.appendChild(el("span", "tree-str", String(value)));
  }
}

export function renderGeneric(value) {
  const wrap = el("div", "tree");
  buildNode(wrap, value);
  return wrap;
}

// 各 Namespace 的 headline（best-effort；缺字段时省略，绝不猜）。
const HEADLINES = {
  identity: (d) => [[t("r.name"), d.primary_name], [t("r.born"), d.birth_time]],
  body: (d) => [[t("r.vital"), d.vital_status], [t("r.bioAge"), fmt(d.biological_age)]],
  emotion: (d) => (d.mood
    ? [[t("r.valence"), fmt(d.mood.valence)], [t("r.arousal"), fmt(d.mood.arousal)]]
    : []),
  personality: (d) => [[t("r.traits"), (d.traits || []).length]],
  value: (d) => [[t("r.values"), (d.commitments || []).length]],
  relationship: (d) => [[t("r.relationships"), (d.relationships || []).length]],
  self_model: (d) => [[t("r.selfEsteem"), fmt(d.self_esteem)]],
};

export function stateHeadline(namespace, data) {
  const fn = HEADLINES[namespace];
  if (!fn) return [];
  try {
    return fn(data);
  } catch (_e) {
    return [];
  }
}

// 13 个 Namespace 的一行人类可读摘要（best-effort：缺字段省略，绝不猜）。
// 供 Mind 的 state-item 与 Life 焦点卡使用。
const SUMMARIES = {
  identity: (d) => {
    const roles = (d.roles || []).filter((r) => r.status === "active").map((r) => r.label);
    if (roles.length) return roles.join(t("sep3"));
    return d.primary_name || "";
  },
  body: (d) => {
    const parts = [];
    if (d.vital_status) parts.push(vitalLabel(d.vital_status));
    if (d.biological_age !== undefined && d.biological_age !== null) parts.push(t("r.bioAgeLine", { n: fmt(d.biological_age) }));
    return parts.join(t("sep3"));
  },
  personality: (d) => (d.traits || []).map((t) => t.name).slice(0, 3).join(t("sep")),
  emotion: (d) => {
    const active = (d.episodes || []).filter((e) => e.status === "active").map((e) => e.emotion_type);
    if (active.length) return active.join(t("sep"));
    return d.mood ? `valence ${fmt(d.mood.valence)}` : "";
  },
  drive: (d) => (d.active_drives || []).map((x) => x.drive_type).slice(0, 3).join(t("sep")),
  memory: (_d) => t("r.memoryNote"),
  belief: (d) => {
    const n = (d.records || []).length;
    if (!n) return "";
    const top = (d.records || []).find((b) => b.status === "ACTIVE");
    return top ? top.proposition : t("r.beliefs", { n });
  },
  value: (d) => (d.commitments || []).map((c) => c.value_type).slice(0, 3).join(t("sep")),
  goal: (d) => (d.goals || []).filter((g) => ["PROPOSED", "ACTIVE", "PAUSED"].includes(g.status)).map((g) => g.description).slice(0, 2).join(t("sep2")),
  relationship: (d) => (d.relationships || []).map((r) => r.target_id).join(t("sep")),
  world_model: (d) => {
    const n = (d.entities || []).length + (d.schemas || []).length;
    return n ? t("r.worldModel", { n }) : "";
  },
  self_model: (d) => t("r.selfEsteemLine", { n: fmt(d.self_esteem) }),
  narrative: (d) => (d.themes || []).map((t) => t.name).slice(0, 2).join(t("sep")),
};

export function stateSummary(namespace, data) {
  const fn = SUMMARIES[namespace];
  if (!fn || data == null) return "";
  try {
    return fn(data);
  } catch (_e) {
    return "";
  }
}

export function renderStateCard(namespace, displayName, version, data) {
  const card = el("div", "state-card");
  const head = el("div", "state-card-head");
  head.appendChild(el("span", "state-card-name", displayName));
  head.appendChild(el("span", "state-card-meta", `v${version ?? "—"}`));
  card.appendChild(head);

  if (data == null) {
    card.appendChild(el("div", "state-card-empty", t("r.unseeded")));
    return card;
  }

  const lines = stateHeadline(namespace, data);
  if (lines.length) {
    const summary = el("div", "state-card-headline");
    for (const [label, value] of lines) {
      const row = el("div", "kv");
      row.appendChild(el("span", "kv-label", label));
      row.appendChild(el("span", "kv-value", value === undefined || value === null ? "—" : String(value)));
      summary.appendChild(row);
    }
    card.appendChild(summary);
  }
  card.appendChild(renderGeneric(data));
  return card;
}
