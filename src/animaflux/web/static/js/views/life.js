// Life Overview 页面（§27）—— 明亮动漫风：英雄卡 + 焦点卡 + 基础状态 + 最近动态 + 情绪。

import { api, ApiError } from "../api.js";
import { navigate } from "../router.js";
import {
  el, clear, toast, empty, spinner, pageHead, formatAge, formatTime, fmt,
  pill, progressBar,
} from "../ui.js";
import { t, stageLabel, vitalLabel } from "../i18n.js";

// 时间推进步长（label 存 i18n key，渲染时取当前语言）。
const DELTAS = [
  ["life.deltaMin", 60],
  ["life.deltaHour", 3600],
  ["life.deltaDay", 86400],
  ["life.deltaMonth", 2592000],
  ["life.deltaYear", 31536000],
];

// 效价/唤醒 → 情绪词 + 表情（best-effort 映射，不猜语义）。
function moodDescriptor(valence, arousal) {
  const v = Number(valence) || 0;
  const a = Number(arousal) || 0;
  if (v >= 0.3 && a >= 0.3) return { word: t("mood.excited"), emoji: "😄" };
  if (v >= 0.3) return { word: t("mood.pleasant"), emoji: "☺" };
  if (v <= -0.3 && a >= 0.3) return { word: t("mood.anxious"), emoji: "😣" };
  if (v <= -0.3) return { word: t("mood.low"), emoji: "☹" };
  if (a <= -0.3) return { word: t("mood.calm"), emoji: "😌" };
  return { word: t("mood.stable"), emoji: "🙂" };
}

function joinOrDash(list) {
  return list && list.length ? list.join(t("sep")) : "—";
}

// 相邻 Tick 相比 version_id 变化的 Namespace（第 0 个视为全部）。
function changedNamespaces(ticks, i) {
  const cur = ticks[i].version_map || {};
  if (i === 0) return Object.keys(cur).sort();
  const prev = ticks[i - 1].version_map || {};
  return Object.keys(cur).filter((ns) => cur[ns] !== prev[ns]).sort();
}

function heroCard(life) {
  const hero = el("section", "card hero");
  const content = el("div", "hero-content");

  const av = el("div", "hero-avatar", Array.from(life.primary_name || "●")[0]);
  content.appendChild(av);

  const info = el("div", "hero-info");
  const statusRow = el("div", "status-row");
  const vs = String(life.vital_status || "").toLowerCase();
  const vsLabel = vitalLabel(life.vital_status) || "—";
  statusRow.appendChild(pill(vsLabel, vs === "alive" ? "green" : "orange"));
  statusRow.appendChild(pill(formatAge(life.chronological_age), "blue"));
  info.appendChild(statusRow);
  info.appendChild(el("h2", "", life.primary_name || life.life_id));
  const metaBits = [life.life_stage ? stageLabel(life.life_stage) : "", joinOrDash(life.active_roles)].filter(Boolean);
  info.appendChild(el("div", "meta", metaBits.join(t("sep3"))));

  const md = moodDescriptor(life.mood?.valence, life.mood?.arousal);
  const stateBox = el("div", "hero-state");
  stateBox.appendChild(el("small", "", t("life.currentState")));
  stateBox.appendChild(el("strong", "", t("life.overall", { word: md.word })));
  const goal0 = (life.active_goals || [])[0];
  const drive0 = (life.top_drives || [])[0];
  const desc = goal0
    ? t("life.currentGoal", { goal: goal0 })
    : drive0 ? t("life.currentDrive", { drive: drive0 }) : t("life.noGoalDrive");
  stateBox.appendChild(el("p", "", desc));
  info.appendChild(stateBox);

  content.appendChild(info);
  hero.appendChild(content);
  return hero;
}

function focusCards(life, memories) {
  const wrap = el("div", "focus-cards");

  const goal = el("section", "card focus-card");
  const goalIcon = el("div", "focus-icon", "◎");
  goalIcon.style.background = "var(--orange-soft)";
  goal.appendChild(goalIcon);
  goal.appendChild(el("h3", "", t("life.focusGoal")));
  goal.appendChild(el("p", "", joinOrDash(life.active_goals)));
  wrap.appendChild(goal);

  const rel = el("section", "card focus-card");
  const relIcon = el("div", "focus-icon", "♙");
  relIcon.style.background = "var(--blue-soft)";
  rel.appendChild(relIcon);
  rel.appendChild(el("h3", "", t("life.focusPeople")));
  rel.appendChild(el("p", "", joinOrDash(life.relationship_targets)));
  wrap.appendChild(rel);

  const mem = el("section", "card focus-card");
  const memIcon = el("div", "focus-icon", "◈");
  memIcon.style.background = "var(--purple-soft)";
  mem.appendChild(memIcon);
  mem.appendChild(el("h3", "", t("life.focusMemory")));
  const firstMem = memories && memories[0];
  mem.appendChild(el("p", "", firstMem ? (firstMem.summary_text || t("life.structuredMemory")) : t("life.noMemory")));
  wrap.appendChild(mem);

  return wrap;
}

function basicItem(label, small, pct, color) {
  const item = el("div", "basic-item");
  item.appendChild(el("b", "", label));
  item.appendChild(el("small", "", small));
  item.appendChild(progressBar(pct, color));
  return item;
}

function basicCard(life) {
  const card = el("section", "card basic-card");
  const head = el("div", "section-head");
  head.appendChild(el("div", "card-title", t("life.basicTitle")));
  head.appendChild(el("div", "card-link", t("life.basicSub")));
  card.appendChild(head);

  const list = el("div", "basic-list");
  const hb = life.homeostasis || {};
  const energy = Math.round((Number(hb.energy) || 0) * 100);
  list.appendChild(basicItem(t("life.body"), t("life.energy", { pct: energy }), energy, "var(--green)"));
  const valence = (Number(life.mood?.valence) + 1) / 2 * 100;
  list.appendChild(basicItem(t("life.mood"), moodDescriptor(life.mood?.valence, life.mood?.arousal).word, valence, "var(--pink)"));
  const drives = life.top_drives || [];
  list.appendChild(basicItem(t("life.drive"), joinOrDash(drives), Math.min(100, drives.length * 34), "var(--orange)"));
  const domains = life.domain_experience || [];
  list.appendChild(basicItem(t("life.experience"), joinOrDash(domains), Math.min(100, domains.length * 34), "var(--blue)"));

  card.appendChild(list);
  return card;
}

function timelineMini(lifeId, ticks) {
  const card = el("section", "card timeline-mini");
  const head = el("div", "section-head");
  head.appendChild(el("div", "card-title", t("life.recentTitle")));
  const allBtn = el("button", "btn small", t("life.viewAll"));
  allBtn.addEventListener("click", () => navigate(`/life/${lifeId}/timeline`));
  head.appendChild(allBtn);
  card.appendChild(head);

  if (!ticks.length) {
    card.appendChild(el("div", "empty", t("life.noHistory")));
    return card;
  }
  const n = ticks.length;
  const start = Math.max(0, n - 4);
  for (let i = n - 1; i >= start; i--) {
    const tick = ticks[i];
    const row = el("div", "timeline-row");
    row.appendChild(el("div", "timeline-time", tick.runtime_time_after ? formatTime(tick.runtime_time_after) : ""));
    row.appendChild(el("b", "", t("life.commit", { tick: tick.tick_id })));
    const changed = changedNamespaces(ticks, i);
    row.appendChild(el("p", "", changed.length ? t("life.changed", { list: changed.join(", ") }) : t("life.noChange")));
    card.appendChild(row);
  }
  return card;
}

function moodCard(life) {
  const card = el("section", "card mood-card");
  const head = el("div", "section-head");
  head.appendChild(el("div", "card-title", t("life.moodTitle")));
  card.appendChild(head);

  const md = moodDescriptor(life.mood?.valence, life.mood?.arousal);
  const line = el("div", "mood-line");
  const face = el("div", "mood-face", md.emoji);
  line.appendChild(face);
  const txt = el("div", "");
  txt.appendChild(el("b", "", t("life.moodOverall", { word: md.word })));
  txt.appendChild(el("p", "", t("life.moodLine", { v: fmt(life.mood?.valence), a: fmt(life.mood?.arousal) })));
  line.appendChild(txt);
  card.appendChild(line);
  return card;
}

function worldBlock(title, children) {
  const box = el("div", "world-block");
  box.appendChild(el("div", "world-block-title", title));
  for (const c of children) box.appendChild(c);
  return box;
}

function worldCard(world) {
  const card = el("section", "card world-card");
  const head = el("div", "section-head");
  head.appendChild(el("div", "card-title", t("life.worldTitle")));
  head.appendChild(el("div", "card-link", t("life.worldSub")));
  card.appendChild(head);

  const stype = world && world.scenario_type;
  if (!stype) {
    card.appendChild(el("div", "empty", t("world.noWorld")));
    return card;
  }

  card.appendChild(el("div", "world-type", `${t("world.scenarioType")} · ${t(`scenario.${stype}`)}`));

  const facts = world.facts || {};
  const fbox = worldBlock(t("world.facts"), []);
  const keys = Object.keys(facts);
  if (!keys.length) fbox.appendChild(el("div", "empty", "—"));
  for (const k of keys) {
    const row = el("div", "world-fact");
    row.appendChild(el("span", "world-key", k));
    row.appendChild(el("span", "world-val", String(facts[k])));
    fbox.appendChild(row);
  }
  card.appendChild(fbox);

  const death = world.death_info;
  if (death) {
    const dbox = worldBlock(t("world.deathInfo"), []);
    let line = death.alive ? t("world.alive") : t("world.dead");
    if (death.death_cause) line += ` · ${t("world.deathCause")}: ${death.death_cause}`;
    if (death.age_at_death != null) line += ` · ${t("world.ageAtDeath")}: ${death.age_at_death}`;
    dbox.appendChild(el("div", "world-death-line", line));
    card.appendChild(dbox);
  }

  const chronicle = world.chronicle;
  if (chronicle && chronicle.length) {
    const cbox = worldBlock(t("world.chronicle"), []);
    for (const line of chronicle.slice(-6)) cbox.appendChild(el("div", "world-chronicle-line", line));
    card.appendChild(cbox);
  }

  return card;
}

function actionsPanel(lifeId, refresh) {
  const panel = el("section", "card", "");
  panel.style.padding = "18px 22px";
  panel.appendChild(el("div", "card-title", t("life.actionsTitle")));
  panel.appendChild(el("div", "page-sub", t("life.actionsSub")));

  const advRow = el("div", "action-row");
  advRow.appendChild(el("span", "action-label", t("life.advance")));
  for (const [labelKey, sec] of DELTAS) {
    const b = el("button", "btn", t(labelKey));
    b.addEventListener("click", async () => {
      b.disabled = true;
      try {
        await api.advance(lifeId, sec);
        await refresh();
      } catch (e) {
        toast(e.message);
      } finally {
        b.disabled = false;
      }
    });
    advRow.appendChild(b);
  }
  panel.appendChild(advRow);

  const obsForm = el("form", "action-row");
  const obsInput = el("input", "obs-input");
  obsInput.type = "text";
  obsInput.placeholder = t("life.observePh");
  const obsBtn = el("button", "btn", t("life.observe"));
  obsBtn.type = "submit";
  obsForm.appendChild(obsInput);
  obsForm.appendChild(obsBtn);
  obsForm.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!obsInput.value.trim()) return;
    obsBtn.disabled = true;
    try {
      await api.observe(lifeId, obsInput.value.trim());
      obsInput.value = "";
      await refresh();
    } catch (e) {
      toast(e.message);
    } finally {
      obsBtn.disabled = false;
    }
  });
  panel.appendChild(obsForm);

  const ctlRow = el("div", "action-row");
  const actBtn = el("button", "btn", t("life.act"));
  actBtn.addEventListener("click", async () => {
    actBtn.disabled = true;
    try {
      const r = await api.act(lifeId);
      if (r.acted) toast(t("act.acted", { action: r.action_type || r.status || "?" }), "ok");
      else toast(t("act.noAction", { reason: r.no_action_reason || "—" }));
      await refresh();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : String(e));
    } finally {
      actBtn.disabled = false;
    }
  });
  const cpBtn = el("button", "btn", t("life.checkpoint"));
  cpBtn.addEventListener("click", async () => {
    cpBtn.disabled = true;
    try {
      await api.createCheckpoint(lifeId);
      toast(t("life.checkpointed"), "ok");
    } catch (e) {
      toast(e.message);
    } finally {
      cpBtn.disabled = false;
    }
  });
  const talkBtn = el("button", "btn primary", t("life.goTalk"));
  talkBtn.addEventListener("click", () => navigate(`/life/${lifeId}/talk`));
  ctlRow.appendChild(actBtn);
  ctlRow.appendChild(cpBtn);
  ctlRow.appendChild(talkBtn);
  panel.appendChild(ctlRow);

  return panel;
}

export async function renderLife(app, { lifeId }) {
  clear(app);

  async function refresh() {
    try {
      await draw();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function draw() {
    clear(app);
    app.appendChild(spinner());
    let life;
    let memories;
    let ticks;
    let world;
    try {
      [life, memories, ticks, world] = await Promise.all([
        api.getLife(lifeId),
        api.memories(lifeId).catch(() => []),
        api.timeline(lifeId).catch(() => []),
        api.world(lifeId).catch(() => ({ scenario_type: null, facts: {} })),
      ]);
    } catch (e) {
      clear(app).appendChild(empty(e instanceof ApiError ? e.message : String(e)));
      return;
    }
    clear(app);

    app.appendChild(pageHead(life.primary_name || life.life_id, t("life.subtitle")));

    const grid = el("div", "life-grid");
    const left = el("div", "life-left");
    left.appendChild(heroCard(life));
    left.appendChild(focusCards(life, memories));
    left.appendChild(basicCard(life));
    grid.appendChild(left);

    const right = el("div", "life-right");
    right.appendChild(timelineMini(lifeId, ticks));
    right.appendChild(moodCard(life));
    right.appendChild(worldCard(world));
    grid.appendChild(right);

    app.appendChild(grid);
    app.appendChild(actionsPanel(lifeId, refresh));
  }

  await draw();
}
