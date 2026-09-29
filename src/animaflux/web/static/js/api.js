// API client（§28 / §39.28）。只依赖文档化 HTTP DTO，不依赖 Core 私有字段。

const BASE = "/api/v1";

class ApiError extends Error {
  constructor(code, message, status) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${BASE}${path}`, opts);
  let payload = null;
  try {
    payload = await res.json();
  } catch (_e) {
    payload = null;
  }
  if (!res.ok) {
    const err = payload && payload.error ? payload.error : {};
    throw new ApiError(
      err.code || "HTTP_ERROR",
      err.message || `HTTP ${res.status}`,
      res.status,
    );
  }
  return payload && "data" in payload ? payload.data : payload;
}

const id = (s) => encodeURIComponent(s);

export const api = {
  // lives
  listLives: () => request("GET", "/lives"),
  getLife: (lifeId) => request("GET", `/lives/${id(lifeId)}`),
  createLife: (payload) => request("POST", "/lives", payload),
  deleteLife: (lifeId) => request("DELETE", `/lives/${id(lifeId)}`),

  // runtime / interaction
  step: (lifeId, delta) => request("POST", `/lives/${id(lifeId)}/step`, { delta }),
  advance: (lifeId, delta) => request("POST", `/lives/${id(lifeId)}/advance`, { delta }),
  observe: (lifeId, content) => request("POST", `/lives/${id(lifeId)}/observe`, { content }),
  say: (lifeId, text) => request("POST", `/lives/${id(lifeId)}/say`, { text }),
  act: (lifeId) => request("POST", `/lives/${id(lifeId)}/act`),
  world: (lifeId) => request("GET", `/lives/${id(lifeId)}/world`),

  // state
  listStates: (lifeId) => request("GET", `/lives/${id(lifeId)}/states`),
  getState: (lifeId, ns) => request("GET", `/lives/${id(lifeId)}/states/${id(ns)}`),

  // diary（§13M）
  diary: (lifeId) => request("GET", `/lives/${id(lifeId)}/diary`),
  writeDiary: (lifeId, payload) => request("POST", `/lives/${id(lifeId)}/diary`, payload),

  // history
  timeline: (lifeId) => request("GET", `/lives/${id(lifeId)}/timeline`),
  agency: (lifeId) => request("GET", `/lives/${id(lifeId)}/agency`),
  development: (lifeId) => request("GET", `/lives/${id(lifeId)}/development`),
  memories: (lifeId) => request("GET", `/lives/${id(lifeId)}/memories`),
  listCheckpoints: (lifeId) => request("GET", `/lives/${id(lifeId)}/checkpoints`),
  createCheckpoint: (lifeId) => request("POST", `/lives/${id(lifeId)}/checkpoints`),
  restore: (lifeId, checkpointId) =>
    request("POST", `/lives/${id(lifeId)}/restore`, { checkpoint_id: checkpointId }),

  // branches
  listBranches: (lifeId) => request("GET", `/lives/${id(lifeId)}/branches`),
  createBranch: (lifeId, name, checkpointId) =>
    request("POST", `/lives/${id(lifeId)}/branches`, { name, checkpoint_id: checkpointId }),
  getBranch: (lifeId, branchId) => request("GET", `/lives/${id(lifeId)}/branches/${id(branchId)}`),
  branchSnapshot: (lifeId, branchId) =>
    request("GET", `/lives/${id(lifeId)}/branches/${id(branchId)}/snapshot`),
};

export { ApiError };
