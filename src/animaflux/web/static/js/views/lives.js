// Lives 页面（§26）：生命管理 —— 列出 / 创建 / 删除（明亮动漫风卡片）。

import { api, ApiError } from "../api.js";
import { navigate } from "../router.js";
import { el, clear, toast, empty, spinner, pageHead, formatAge, badge, avatar } from "../ui.js";
import { t, stageLabel, vitalLabel } from "../i18n.js";

// 删除按钮：两步确认（第一次点「删除」变「确认删除」，3 秒内再点才真正删除）。
function deleteButton(lifeId, onDeleted) {
  const btn = el("button", "btn danger small", t("lives.delete"));
  let armed = false;
  let timer = null;
  btn.addEventListener("click", (ev) => {
    ev.stopPropagation();
    if (!armed) {
      armed = true;
      btn.textContent = t("lives.confirmDelete");
      btn.classList.add("confirm");
      timer = setTimeout(() => disarm(), 3000);
      return;
    }
    clearTimeout(timer);
    btn.disabled = true;
    btn.textContent = t("lives.deleting");
    (async () => {
      try {
        await api.deleteLife(lifeId);
        toast(t("lives.deleted", { id: lifeId }), "ok");
        onDeleted();
      } catch (e) {
        toast(e instanceof ApiError ? e.message : String(e));
        btn.disabled = false;
        disarm();
      }
    })();
  });
  function disarm() {
    armed = false;
    btn.classList.remove("confirm");
    btn.textContent = t("lives.delete");
  }
  return btn;
}

function lifeCard(life, onDeleted) {
  const card = el("div", "life-card");
  card.appendChild(avatar(life.primary_name || life.life_id));
  const who = el("div", "who");
  who.appendChild(el("div", "name", life.primary_name || life.life_id));
  who.appendChild(el("div", "id", life.life_id));
  card.appendChild(who);

  const meta = el("div", "meta");
  if (life.life_stage) meta.appendChild(el("div", "stage", stageLabel(life.life_stage)));
  if (life.scenario_type) meta.appendChild(el("div", "stage scenario", t(`scenario.${life.scenario_type}`)));
  const status = el("div", "status");
  const alive = String(life.vital_status || "").toLowerCase() === "alive";
  status.appendChild(badge(vitalLabel(life.vital_status), alive ? "alive" : "other"));
  status.appendChild(el("span", "status-age", formatAge(life.chronological_age)));
  meta.appendChild(status);
  meta.appendChild(deleteButton(life.life_id, onDeleted));
  card.appendChild(meta);

  card.addEventListener("click", () => navigate(`/life/${life.life_id}/diary`));
  return card;
}

export async function renderLives(app, _ctx) {
  clear(app);
  app.appendChild(pageHead(t("lives.title"), t("lives.subtitle")));

  const createPanel = el("section", "card", "");
  createPanel.style.padding = "18px 22px";
  createPanel.appendChild(el("div", "card-title", t("lives.createTitle")));
  createPanel.appendChild(el("div", "page-sub", t("lives.createSub")));

  const form = el("form", "create-form");
  form.setAttribute("autocomplete", "off");
  const nameLabel = el("label", "");
  nameLabel.appendChild(el("span", "", t("lives.nameLabel")));
  const nameInput = el("input", "");
  nameInput.type = "text";
  nameInput.value = t("lives.defaultName");
  nameInput.required = true;
  nameLabel.appendChild(nameInput);

  const scenarioLabel = el("label", "");
  scenarioLabel.appendChild(el("span", "", t("lives.scenarioLabel")));
  const scenarioSelect = el("select", "");
  for (const [value, key] of [
    ["none", "scenario.none"],
    ["presentation", "scenario.presentation"],
    ["chronicle", "scenario.chronicle"],
  ]) {
    const opt = el("option", "", t(key));
    opt.value = value;
    scenarioSelect.appendChild(opt);
  }
  scenarioLabel.appendChild(scenarioSelect);

  const btn = el("button", "btn primary", t("lives.createBtn"));
  btn.type = "submit";
  form.appendChild(nameLabel);
  form.appendChild(scenarioLabel);
  form.appendChild(btn);
  const status = el("div", "status");
  status.hidden = true;
  createPanel.appendChild(form);
  createPanel.appendChild(status);

  const list = el("div", "lives-list");

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const payload = {
      primary_name: nameInput.value.trim() || t("lives.defaultName"),
      scenario: scenarioSelect.value,
    };
    btn.disabled = true;
    status.hidden = false;
    status.className = "status";
    status.textContent = t("lives.creating");
    try {
      const life = await api.createLife(payload);
      status.textContent = t("lives.created");
      btn.disabled = false;
      navigate(`/life/${life.life_id}/diary`);
    } catch (e) {
      status.className = "status err";
      status.textContent = e instanceof ApiError ? e.message : String(e);
      btn.disabled = false;
    }
  });

  async function loadList() {
    clear(list).appendChild(spinner());
    try {
      const lives = await api.listLives();
      clear(list);
      if (!lives.length) list.appendChild(empty(t("lives.empty")));
      else lives.forEach((l) => list.appendChild(lifeCard(l, loadList)));
    } catch (e) {
      clear(list).appendChild(empty(e instanceof ApiError ? e.message : String(e)));
    }
  }

  app.appendChild(list);
  app.appendChild(createPanel);
  await loadList();
}
