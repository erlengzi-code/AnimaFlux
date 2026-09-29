// Talk 页面（§28）：对话 + 当前生命语境 + Why 抽屉（明亮动漫风 chat 卡片）。

import { api, ApiError } from "../api.js";
import { el, clear, loading, openDrawer, fmt, formatAge } from "../ui.js";
import { renderGeneric } from "../renderers.js";
import { t, stageLabel, vitalLabel } from "../i18n.js";

function avatarSm(name) {
  const av = el("div", "avatar sm", Array.from(name || "●")[0]);
  return av;
}

function message(role, text, extra) {
  const wrap = el("div", `message ${role === "user" ? "user" : ""}`);
  if (role !== "user") wrap.appendChild(avatarSm(role === "agent" ? "A" : "?"));
  const inner = el("div", "");
  inner.appendChild(el("div", "bubble", text));
  inner.appendChild(el("div", "msg-time", t("ui.now")));
  if (extra) inner.appendChild(extra);
  wrap.appendChild(inner);
  return wrap;
}

// 轻量 turn 生命周期指示（§39.x：turn.started → processing → completed），非 token 流式。
function thinkingMessage() {
  const wrap = el("div", "message");
  wrap.appendChild(avatarSm("…"));
  const inner = el("div", "");
  const bubble = el("div", "bubble", "turn.started…");
  inner.appendChild(bubble);
  wrap.appendChild(inner);
  const states = ["turn.started", "turn.processing", "turn.completed"];
  let i = 0;
  const timer = setInterval(() => {
    i = (i + 1) % states.length;
    bubble.textContent = `${states[i]}${".".repeat((i % 3) + 1)}`;
  }, 500);
  wrap._stop = () => clearInterval(timer);
  return wrap;
}

// Why：取该 tick 的时间线条目，展示交互后的状态快照（真实数据，不猜原因，§39.17）
async function renderWhy(lifeId, tickId, traceRef) {
  const box = el("div", "why");
  if (traceRef) box.appendChild(el("div", "why-ref", `trace_ref: ${traceRef}`));
  try {
    const timeline = await api.timeline(lifeId);
    const tick = timeline.find((t) => t.tick_id === tickId);
    if (tick) {
      box.appendChild(el("div", "why-sec", t("talk.snapshotTick", { tick: tickId })));
      box.appendChild(renderGeneric(tick.payloads || {}));
    } else {
      box.appendChild(el("div", "empty", t("talk.tickNotFound")));
    }
  } catch (e) {
    box.appendChild(el("div", "empty", t("talk.timelineFail", { msg: e.message })));
  }
  return box;
}

// 记忆语境：展示已形成的 Memory（§13F.24 公开读）；「想不起来」是合法结果（§14C.17）。
function memoryList(memories) {
  const box = el("div", "ctx-memories");
  if (!memories || !memories.length) {
    box.appendChild(el("div", "ctx-note", t("talk.noMemory")));
    return box;
  }
  for (const m of memories.slice(0, 6)) {
    const text = m.summary_text || (typeof m.content === "string" ? m.content : t("talk.structured"));
    const row = el("div", "ctx-mem");
    row.appendChild(el("span", "ctx-mem-type", m.memory_type));
    row.appendChild(el("span", "ctx-mem-text", text));
    box.appendChild(row);
  }
  return box;
}

function contextItem(label, value) {
  const item = el("div", "context-item");
  item.appendChild(el("small", "", label));
  item.appendChild(el("b", "", value === undefined || value === null || value === "" ? "—" : String(value)));
  return item;
}

export async function renderTalk(app, { lifeId }) {
  loading(app);

  let life;
  try {
    life = await api.getLife(lifeId);
  } catch (e) {
    clear(app).appendChild(el("div", "empty", e instanceof ApiError ? e.message : String(e)));
    return;
  }
  let memories = [];
  try {
    memories = await api.memories(lifeId);
  } catch (e) {
    memories = [];
  }
  clear(app);

  const head = el("div", "page-head");
  head.appendChild(el("h2", "page-title", `${life.primary_name || life.life_id} · Talk`));
  head.appendChild(el("div", "page-sub", t("talk.subtitle")));
  app.appendChild(head);

  const layout = el("div", "talk-layout");

  // 语境栏
  const ctx = el("aside", "card context-panel");
  const ctxHead = el("div", "section-head");
  ctxHead.appendChild(el("div", "card-title", t("talk.contextTitle")));
  ctx.appendChild(ctxHead);
  const mood = life.mood || {};
  ctx.appendChild(contextItem(t("talk.mood"), `valence ${fmt(mood.valence)} · arousal ${fmt(mood.arousal)}`));
  ctx.appendChild(contextItem(t("talk.stage"), stageLabel(life.life_stage)));
  ctx.appendChild(contextItem(t("talk.values"), (life.top_values || []).join(t("sep"))));
  ctx.appendChild(contextItem(t("talk.memory"), ""));
  ctx.appendChild(memoryList(memories));
  ctx.appendChild(el("div", "ctx-note", t("talk.seeMind")));
  const whyBtn = el("button", "btn", t("talk.whyBtn"));
  whyBtn.style.width = "100%";
  whyBtn.style.marginTop = "16px";
  whyBtn.addEventListener("click", () => {
    openDrawer("Why", el("div", "empty", t("talk.whyHint")));
  });
  ctx.appendChild(whyBtn);
  layout.appendChild(ctx);

  // 对话区
  const convo = el("div", "card chat-card");
  const chatHead = el("div", "chat-head");
  chatHead.appendChild(avatarSm(life.primary_name || life.life_id));
  const who = el("div", "");
  who.appendChild(el("b", "", life.primary_name || life.life_id));
  const stage = life.life_stage ? stageLabel(life.life_stage) : "—";
  who.appendChild(el("small", "", `${formatAge(life.chronological_age)} · ${stage} · ${vitalLabel(life.vital_status)}`));
  chatHead.appendChild(who);
  convo.appendChild(chatHead);

  const log = el("div", "chat-body");
  const form = el("form", "chat-input");
  const input = el("textarea", "");
  input.placeholder = t("talk.inputPh");
  input.autocomplete = "off";
  const send = el("button", "btn primary", t("ui.send"));
  send.type = "submit";
  form.appendChild(input);
  form.appendChild(send);

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    send.disabled = true;
    log.appendChild(message("user", text));
    const thinking = thinkingMessage();
    log.appendChild(thinking);
    log.scrollTop = log.scrollHeight;
    try {
      const result = await api.say(lifeId, text);
      thinking._stop();
      log.removeChild(thinking);
      const whyBtn2 = el("button", "why-btn", "Why ↗");
      whyBtn2.addEventListener("click", async () => {
        openDrawer("Why", await renderWhy(lifeId, result.tick_id, result.trace_ref));
      });
      log.appendChild(message("agent", result.text, whyBtn2));
    } catch (e) {
      thinking._stop();
      log.removeChild(thinking);
      log.appendChild(message("agent", t("talk.error", { msg: e instanceof ApiError ? e.message : e })));
    } finally {
      send.disabled = false;
      log.scrollTop = log.scrollHeight;
    }
  });

  convo.appendChild(log);
  convo.appendChild(form);
  layout.appendChild(convo);
  app.appendChild(layout);
}
