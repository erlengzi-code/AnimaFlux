// Hash Router（§39.2）。无需服务端 SPA fallback、无 bundler。

// 形如 "#/life/<id>/talk" → ["life", "<id>", "talk"]；空 hash 归到 lives。
export function parseHash() {
  const h = (location.hash || "").replace(/^#\/?/, "");
  return h.split("/").filter(Boolean);
}

export function navigate(hash) {
  if (location.hash === `#${hash}`) return;
  location.hash = hash;
}

// 由 ["life","id","talk"] 解析出 {view, lifeId}
export function resolveRoute(parts) {
  if (parts.length === 0 || parts[0] === "lives") {
    return { view: "lives", lifeId: null };
  }
  if (parts[0] === "life") {
    const lifeId = parts[1] || null;
    const sub = parts[2] || null;
    const view = ["diary", "talk", "timeline", "mind", "branches", "development"].includes(sub)
      ? sub
      : "life";
    return { view, lifeId };
  }
  return { view: "notfound", lifeId: null };
}
