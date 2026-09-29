// 日记页（§13M）：Narrative 的对外呈现 —— 生命默认首页。
//
// 重要的事会自动写一篇（后端确定性触发）；也可点击写某话题 / 某时间段。正文是第一人称
// 散文（LLM 文风，失败回退确定性模板），但它只是「它的叙述」，不是客观事实（事实见世界）。

import { api, ApiError } from "../api.js";
import { el, clear, toast, empty, spinner, pageHead, pill, formatTime } from "../ui.js";
import { t } from "../i18n.js";

// 一条日记卡片：日期 + 标题 + 第一人称正文 + 溯源小标。
function entryCard(entry) {
  const card = el("article", "diary-entry");
  const head = el("div", "diary-head");
  head.appendChild(el("time", "diary-date", formatTime(entry.time)));
  head.appendChild(el("h3", "diary-title", entry.title || t("diary.untitled")));
  card.appendChild(head);
  card.appendChild(el("p", "diary-body", entry.summary || ""));
  const foot = el("div", "diary-foot");
  foot.appendChild(pill(t("diary.provenance"), "purple"));
  const n = (entry.memory_refs || []).length;
  if (n) foot.appendChild(el("span", "diary-refs", t("diary.provenanceRefs", { n })));
  card.appendChild(foot);
  return card;
}

// 写日记：话题 + 时间段（均可空）。
function writeForm(lifeId, refresh) {
  const panel = el("section", "card", "");
  panel.style.padding = "18px 22px";
  panel.appendChild(el("div", "card-title", t("diary.writeTitle")));
  panel.appendChild(el("div", "page-sub", t("diary.writeSub")));

  const form = el("form", "diary-form");
  form.setAttribute("autocomplete", "off");

  const topicLabel = el("label", "");
  topicLabel.appendChild(el("span", "", t("diary.topicLabel")));
  const topicInput = el("input", "obs-input");
  topicInput.type = "text";
  topicInput.placeholder = t("diary.topicPh");
  topicLabel.appendChild(topicInput);
  form.appendChild(topicLabel);

  const timeRow = el("div", "diary-time-row");
  const startInput = el("input", "obs-input");
  startInput.type = "text";
  startInput.placeholder = t("diary.timeStartPh");
  const endInput = el("input", "obs-input");
  endInput.type = "text";
  endInput.placeholder = t("diary.timeEndPh");
  timeRow.appendChild(startInput);
  timeRow.appendChild(endInput);
  form.appendChild(timeRow);

  const btn = el("button", "btn primary", t("diary.writeBtn"));
  btn.type = "submit";
  form.appendChild(btn);

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const payload = {};
    const topic = topicInput.value.trim();
    if (topic) payload.topic = topic;
    if (startInput.value.trim()) payload.time_start = startInput.value.trim();
    if (endInput.value.trim()) payload.time_end = endInput.value.trim();
    btn.disabled = true;
    btn.textContent = t("diary.writing");
    try {
      await api.writeDiary(lifeId, payload);
      topicInput.value = "";
      startInput.value = "";
      endInput.value = "";
      toast(t("diary.written"), "ok");
      await refresh();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : String(e));
    } finally {
      btn.disabled = false;
      btn.textContent = t("diary.writeBtn");
    }
  });

  panel.appendChild(form);
  return panel;
}

// 紧凑推进 / 主动行动条：首页即可推进时间触发自动日记。
function advanceStrip(lifeId, refresh) {
  const panel = el("section", "card", "");
  panel.style.padding = "18px 22px";
  panel.appendChild(el("div", "card-title", t("diary.advanceTitle")));
  panel.appendChild(el("div", "page-sub", t("diary.advanceSub")));

  const row = el("div", "action-row");
  for (const [labelKey, sec] of [
    ["life.deltaDay", 86400],
    ["life.deltaMonth", 2592000],
    ["life.deltaYear", 31536000],
  ]) {
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
    row.appendChild(b);
  }

  const actBtn = el("button", "btn", t("diary.act"));
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
  row.appendChild(actBtn);
  panel.appendChild(row);
  return panel;
}

export async function renderDiary(app, { lifeId }) {
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
    let entries;
    try {
      entries = await api.diary(lifeId);
    } catch (e) {
      clear(app).appendChild(empty(e instanceof ApiError ? e.message : String(e)));
      return;
    }
    clear(app);

    app.appendChild(pageHead(t("diary.title"), t("diary.subtitle")));
    app.appendChild(writeForm(lifeId, refresh));
    app.appendChild(advanceStrip(lifeId, refresh));

    const list = el("div", "diary-list");
    if (!entries.length) list.appendChild(empty(t("diary.empty")));
    else entries.forEach((entry) => list.appendChild(entryCard(entry)));
    app.appendChild(list);
  }

  await draw();
}
