// 共享 UI 工具（§39.24 / §39.18）。所有不可信文本一律用 textContent 渲染。

import { t, locale } from "./i18n.js";

export function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
  return node;
}

let toastTimer = null;
export function toast(message, kind = "err") {
  const t = document.getElementById("toast");
  t.textContent = message;
  t.className = `toast ${kind}`;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), 4200);
}

// 把 summary 的 chronological_age（秒）格式化成可读年龄
export function formatAge(seconds) {
  const sec = Number(seconds) || 0;
  const days = Math.floor(sec / 86400);
  const years = Math.floor(days / 365.25);
  const remDays = Math.floor(days - years * 365.25);
  if (years > 0) return t("age.years", { years, days: remDays });
  if (days > 0) return t("age.days", { days });
  return t("age.hours", { hours: Math.floor(sec / 3600) });
}

export function formatTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString(locale() === "zh" ? "zh-CN" : "en-US", { hour12: false });
}

export function fmt(n, digits = 2) {
  const x = Number(n);
  if (Number.isNaN(x)) return "—";
  return x.toFixed(digits);
}

// 简单 key-value 行
export function kv(label, valueNode, opts = {}) {
  const row = el("div", "kv");
  row.appendChild(el("span", "kv-label", label));
  const val = el("span", "kv-value");
  if (valueNode instanceof Node) val.appendChild(valueNode);
  else val.textContent = valueNode === undefined || valueNode === null ? "—" : String(valueNode);
  if (opts.accent) val.classList.add("accent");
  row.appendChild(val);
  return row;
}

// 页面骨架：标题 + 副标题 + 返回链接
export function pageHead(title, subtitle) {
  const head = el("div", "page-head");
  head.appendChild(el("h2", "page-title", title));
  if (subtitle) head.appendChild(el("div", "page-sub", subtitle));
  return head;
}

export function empty(text) {
  return el("div", "empty", text);
}

export function badge(text, kind = "") {
  return el("span", `badge badge-${kind}`, text);
}

// 状态徽章（参考动画风的 pill：green/blue/purple/orange/pink/gray）
export function pill(text, kind = "gray") {
  return el("span", `pill ${kind}`, text);
}

// 进度条（0–100），可指定填充色（CSS 颜色字符串）
export function progressBar(pct, color) {
  const bar = el("div", "progress");
  const fill = el("i");
  const v = Math.max(0, Math.min(100, Number(pct) || 0));
  fill.style.width = `${v}%`;
  if (color) fill.style.background = color;
  bar.appendChild(fill);
  return bar;
}

// 头像 monogram：取名字首字（空则回退 "●"）
export function avatar(primaryName) {
  const s = (primaryName || "").trim();
  return el("div", "avatar", s ? Array.from(s)[0] : "●");
}

export function spinner() {
  return el("div", "spinner");
}

// 页面加载占位（§39.24）：清空容器并挂 spinner，随后由视图替换为内容。
export function loading(app) {
  clear(app).appendChild(spinner());
  return app;
}

// 抽屉（Talk 的 Why / Branches 的 Snapshot 共用，§28 / §39.12）。
export function openDrawer(title, bodyNode) {
  const drawer = document.getElementById("drawer");
  document.getElementById("drawer-title").textContent = title;
  clear(document.getElementById("drawer-body")).appendChild(bodyNode);
  drawer.classList.add("open");
  document.getElementById("drawer-backdrop").hidden = false;
}

export function closeDrawer() {
  document.getElementById("drawer").classList.remove("open");
  document.getElementById("drawer-backdrop").hidden = true;
}
