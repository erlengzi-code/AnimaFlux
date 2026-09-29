// Development 页面（§32 / §24）：从真实历史派生的 Development Context（非 Source-of-Truth）。

import { api, ApiError } from "../api.js";
import { el, clear, empty, loading, pageHead, formatAge, formatTime, fmt } from "../ui.js";
import { t, stageLabel } from "../i18n.js";

function stat(label, value) {
  const card = el("div", "stat-card");
  card.appendChild(el("div", "stat-label", label));
  card.appendChild(el("div", "stat-value", value));
  return card;
}

function domainTable(domains) {
  if (!domains || !domains.length) {
    return el("div", "empty", t("dev.noDomain"));
  }
  const table = el("div", "dev-table");
  const head = el("div", "dev-row dev-head");
  for (const h of ["domain", "exposure", "practice", "diversity", "recency"]) {
    head.appendChild(el("div", "dev-cell", h));
  }
  table.appendChild(head);
  for (const d of domains) {
    const row = el("div", "dev-row");
    row.appendChild(el("div", "dev-cell", d.domain));
    row.appendChild(el("div", "dev-cell", String(d.exposure ?? 0)));
    row.appendChild(el("div", "dev-cell", String(d.practice ?? 0)));
    row.appendChild(el("div", "dev-cell", String(d.diversity ?? 0)));
    row.appendChild(el("div", "dev-cell", d.recency ? formatTime(d.recency) : "—"));
    table.appendChild(row);
  }
  return table;
}

export async function renderDevelopment(app, { lifeId }) {
  loading(app);
  let dev;
  try {
    dev = await api.development(lifeId);
  } catch (e) {
    clear(app).appendChild(empty(e instanceof ApiError ? e.message : String(e)));
    return;
  }

  clear(app);
  app.appendChild(pageHead("Development", t("dev.subtitle")));

  const grid = el("div", "stat-grid");
  grid.appendChild(stat(t("dev.age"), formatAge(dev.chronological_age)));
  grid.appendChild(stat(t("dev.stage"), stageLabel(dev.life_stage)));
  grid.appendChild(stat(t("dev.maturity"), fmt(dev.biological_maturity)));
  grid.appendChild(stat(t("dev.roles"), (dev.role_refs || []).join(", ") || "—"));
  grid.appendChild(stat(t("dev.transitions"), (dev.transition_refs || []).join(", ") || "—"));
  app.appendChild(grid);

  const exp = el("section", "card", "");
  exp.style.padding = "18px 22px";
  exp.appendChild(el("div", "card-title", t("dev.domain")));
  exp.appendChild(el("div", "page-sub", t("dev.domainSub")));
  exp.appendChild(domainTable(dev.domain_experience?.domains));
  app.appendChild(exp);

  const note = el("section", "card", "");
  note.style.padding = "18px 22px";
  note.appendChild(el("div", "dev-note", t("dev.note")));
  note.appendChild(el("div", "dev-note-sub", t("dev.noteSub")));
  app.appendChild(note);
}
