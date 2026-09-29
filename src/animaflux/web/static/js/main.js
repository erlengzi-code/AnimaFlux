// 入口：hash router + 侧边栏导航 + mini-life + 抽屉（§39.2）。

import { parseHash, resolveRoute } from "./router.js";
import { el, clear, closeDrawer } from "./ui.js";
import { t, setLocale, onLocaleChange, locale, stageLabel, vitalLabel } from "./i18n.js";
import { api } from "./api.js";
import { renderLives } from "./views/lives.js";
import { renderDiary } from "./views/diary.js";
import { renderLife } from "./views/life.js";
import { renderTalk } from "./views/talk.js";
import { renderTimeline } from "./views/timeline.js";
import { renderMind } from "./views/mind.js";
import { renderBranches } from "./views/branches.js";
import { renderDevelopment } from "./views/development.js";

const VIEWS = {
  lives: renderLives,
  diary: renderDiary,
  life: renderLife,
  talk: renderTalk,
  timeline: renderTimeline,
  mind: renderMind,
  branches: renderBranches,
  development: renderDevelopment,
};

// 侧边栏导航项（图标仅作视觉区分）：[sub, labelKey, icon]，sub 为空 = Life 总览页。
// label 存 i18n key，渲染时再取当前语言。
const NAV_ITEMS = [
  ["diary", "nav.diary", "✎"],
  ["", "nav.life", "◈"],
  ["talk", "nav.talk", "✦"],
  ["mind", "nav.mind", "◉"],
  ["timeline", "nav.timeline", "◷"],
  ["branches", "nav.branches", "⑂"],
  ["development", "nav.development", "♮"],
];

function navButton(hash, label, icon) {
  const btn = el("button", "nav-btn", "");
  btn.dataset.view = hash;
  btn.appendChild(el("span", "nav-icon", icon || "·"));
  btn.appendChild(el("span", "", label));
  btn.addEventListener("click", () => {
    location.hash = `#${hash}`;
  });
  return btn;
}

function renderNav(route) {
  const nav = document.getElementById("nav");
  clear(nav);
  nav.appendChild(navButton("/lives", t("nav.lives"), "⌂"));
  if (route && route.lifeId) {
    const id = route.lifeId;
    for (const [sub, labelKey, icon] of NAV_ITEMS) {
      nav.appendChild(navButton(`/life/${id}${sub ? `/${sub}` : ""}`, t(labelKey), icon));
    }
  }
  const current = (location.hash || "").replace(/^#/, "");
  for (const btn of nav.querySelectorAll(".nav-btn")) {
    const h = btn.dataset.view;
    if (current === h || (current === "" && h === "/lives")) btn.classList.add("active");
  }
}

// 侧边栏底部 mini-life：有生命时显示名字/阶段 + 头像 monogram。
async function renderMiniLife(route) {
  const box = document.getElementById("miniLife");
  if (!route || !route.lifeId) {
    box.hidden = true;
    return;
  }
  try {
    const life = await api.getLife(route.lifeId);
    document.getElementById("miniLifeAvatar").textContent = Array.from(life.primary_name || "●")[0];
    document.getElementById("miniLifeName").textContent = life.primary_name || life.life_id;
    const sub = life.life_stage ? stageLabel(life.life_stage) : (life.vital_status ? vitalLabel(life.vital_status) : "");
    document.getElementById("miniLifeSub").textContent = sub;
    box.hidden = false;
  } catch (_e) {
    box.hidden = true;
  }
}

async function render() {
  const route = resolveRoute(parseHash());
  const app = document.getElementById("app");
  renderNav(route);
  renderMiniLife(route);
  const view = route.view === "notfound" ? null : VIEWS[route.view];
  if (!view) {
    clear(app).appendChild(el("div", "empty", t("main.notfound")));
    return;
  }
  try {
    await view(app, route);
  } catch (e) {
    clear(app).appendChild(el("div", "empty", t("main.renderError", { msg: e.message || e })));
  }
}

// 语言切换（zh / en）：切换后同步品牌文案 + 触发整体重渲染。
function bindLangToggle() {
  const btn = document.getElementById("langToggle");
  const brandSub = document.getElementById("brandSub");
  const sync = () => {
    if (btn) btn.textContent = locale() === "zh" ? "EN" : "中文";
    if (brandSub) brandSub.textContent = t("brand.sub");
    document.title = t("brand.title");
  };
  sync();
  if (btn) btn.addEventListener("click", () => setLocale(locale() === "zh" ? "en" : "zh"));
  onLocaleChange(sync);
}

document.getElementById("drawer-close").addEventListener("click", closeDrawer);
document.getElementById("drawer-backdrop").addEventListener("click", closeDrawer);
window.addEventListener("hashchange", render);

bindLangToggle();
onLocaleChange(render);
render();
