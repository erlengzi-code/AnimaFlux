// Branches & Checkpoints 页面（§12.8 / §12.9 / §33 / §39.10）。
// Checkpoint ≠ Branch；支持：checkpoint 列表 + Restore、从 Checkpoint Fork、Branch 树、Branch Compare。

import { api, ApiError } from "../api.js";
import { el, clear, empty, toast, pageHead, openDrawer, formatTime } from "../ui.js";
import { renderGeneric } from "../renderers.js";
import { t } from "../i18n.js";

function checkpointCard(lifeId, cp, onChanged) {
  const card = el("div", "ckpt-card");
  const head = el("div", "ckpt-head");
  head.appendChild(el("span", "ckpt-id", cp.checkpoint_id));
  head.appendChild(el("span", "ckpt-time", formatTime(cp.fork_world_time)));
  card.appendChild(head);
  card.appendChild(el("div", "ckpt-ns", t("branches.nsCount", { n: (cp.namespaces || []).length })));

  const actions = el("div", "action-row");
  const forkBtn = el("button", "btn", t("branches.fork"));
  forkBtn.addEventListener("click", async () => {
    forkBtn.disabled = true;
    try {
      await api.createBranch(lifeId, `branch-${cp.checkpoint_id.slice(0, 6)}`, cp.checkpoint_id);
      toast(t("branches.forked"), "ok");
      onChanged();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : String(e));
      forkBtn.disabled = false;
    }
  });
  const restoreBtn = el("button", "btn danger", t("branches.restore"));
  restoreBtn.addEventListener("click", async () => {
    const ok = window.confirm(t("branches.restoreConfirm", { id: cp.checkpoint_id }));
    if (!ok) return;
    restoreBtn.disabled = true;
    try {
      await api.restore(lifeId, cp.checkpoint_id);
      toast(t("branches.restored"), "ok");
      onChanged();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : String(e));
      restoreBtn.disabled = false;
    }
  });
  actions.appendChild(forkBtn);
  actions.appendChild(restoreBtn);
  card.appendChild(actions);
  return card;
}

function branchNode(lifeId, branch) {
  const node = el("div", "branch-node");
  const head = el("div", "branch-head");
  head.appendChild(el("span", "branch-dot", "●"));
  head.appendChild(el("span", "branch-name", branch.branch_name));
  head.appendChild(el("span", "branch-id", branch.branch_id));
  head.appendChild(el("span", "branch-parent", `← ${branch.parent_branch_id || "main"}`));
  const snapBtn = el("button", "btn small", t("branches.snapshot"));
  snapBtn.addEventListener("click", async () => {
    snapBtn.disabled = true;
    try {
      const snap = await api.branchSnapshot(lifeId, branch.branch_id);
      openDrawer(`${t("branches.snapshot")} · ${branch.branch_name}`, renderGeneric(snap));
    } catch (e) {
      toast(e instanceof ApiError ? e.message : String(e));
    } finally {
      snapBtn.disabled = false;
    }
  });
  head.appendChild(snapBtn);
  node.appendChild(head);
  return node;
}

function branchTree(lifeId, branches) {
  const root = el("div", "branch-tree");
  const main = el("div", "branch-root");
  main.appendChild(el("span", "branch-dot accent", "●"));
  main.appendChild(el("span", "branch-name", "main"));
  main.appendChild(el("span", "branch-id", t("branches.mainline")));
  root.appendChild(main);

  const kids = el("div", "branch-children");
  if (!branches.length) {
    kids.appendChild(el("div", "empty", t("branches.noBranch")));
  } else {
    for (const b of branches) kids.appendChild(branchNode(lifeId, b));
  }
  root.appendChild(kids);
  return root;
}

function renderCompare(snapA, snapB) {
  const keys = [...new Set([...Object.keys(snapA || {}), ...Object.keys(snapB || {})])].sort();
  const box = el("div", "compare");
  if (!keys.length) {
    box.appendChild(el("div", "empty", t("branches.noSnapshot")));
    return box;
  }
  let diffCount = 0;
  for (const k of keys) {
    const a = snapA && snapA[k];
    const b = snapB && snapB[k];
    const same = JSON.stringify(a) === JSON.stringify(b);
    if (!same) diffCount += 1;
    const row = el("div", "compare-row");
    if (!same) row.classList.add("diff");
    const ns = el("div", "compare-ns");
    ns.appendChild(el("span", "compare-ns-name", k));
    ns.appendChild(el("span", "compare-ns-tag", same ? t("branches.same") : t("branches.diff")));
    row.appendChild(ns);
    if (same) {
      row.appendChild(el("div", "compare-same", t("branches.identical")));
    } else {
      const ca = el("div", "compare-col");
      ca.appendChild(el("div", "compare-col-label", "A"));
      ca.appendChild(renderGeneric(a));
      const cb = el("div", "compare-col");
      cb.appendChild(el("div", "compare-col-label", "B"));
      cb.appendChild(renderGeneric(b));
      row.appendChild(ca);
      row.appendChild(cb);
    }
    box.appendChild(row);
  }
  const summary = el("div", "compare-summary", t("branches.compareSummary", { total: keys.length, diff: diffCount }));
  box.insertBefore(summary, box.firstChild);
  return box;
}

export async function renderBranches(app, { lifeId }) {
  async function draw() {
    clear(app);
    app.appendChild(pageHead("Branches & Checkpoints", t("branches.subtitle")));

    // —— Checkpoints ——
    const ckptPanel = el("section", "card", "");
    ckptPanel.style.padding = "18px 22px";
    ckptPanel.appendChild(el("div", "card-title", t("branches.checkpoints")));
    ckptPanel.appendChild(el("div", "page-sub", t("branches.checkpointsSub")));
    const ckptList = el("div", "ckpt-list");
    ckptPanel.appendChild(ckptList);
    app.appendChild(ckptPanel);

    // —— Branches ——
    const branchPanel = el("section", "card", "");
    branchPanel.style.padding = "18px 22px";
    branchPanel.appendChild(el("div", "card-title", t("branches.branches")));
    branchPanel.appendChild(el("div", "page-sub", t("branches.branchesSub")));
    const form = el("form", "action-row");
    const nameInput = el("input", "obs-input");
    nameInput.type = "text";
    nameInput.placeholder = t("branches.namePh");
    const cpSelect = el("select", "obs-input");
    const createBtn = el("button", "btn primary", t("branches.createBranch"));
    createBtn.type = "submit";
    form.appendChild(nameInput);
    form.appendChild(cpSelect);
    form.appendChild(createBtn);
    branchPanel.appendChild(form);
    const tree = el("div", "");
    branchPanel.appendChild(tree);
    app.appendChild(branchPanel);

    // —— Compare ——
    const cmpPanel = el("section", "card", "");
    cmpPanel.style.padding = "18px 22px";
    cmpPanel.appendChild(el("div", "card-title", t("branches.compare")));
    cmpPanel.appendChild(el("div", "page-sub", t("branches.compareSub")));
    const cmpForm = el("form", "action-row");
    const selA = el("select", "obs-input");
    const selB = el("select", "obs-input");
    const cmpBtn = el("button", "btn", t("branches.compareBtn"));
    cmpBtn.type = "submit";
    cmpForm.appendChild(el("span", "action-label", t("branches.branchA")));
    cmpForm.appendChild(selA);
    cmpForm.appendChild(el("span", "action-label", t("branches.branchB")));
    cmpForm.appendChild(selB);
    cmpForm.appendChild(cmpBtn);
    cmpPanel.appendChild(cmpForm);
    app.appendChild(cmpPanel);

    let checkpoints = [];
    let branches = [];
    try {
      checkpoints = await api.listCheckpoints(lifeId);
      branches = await api.listBranches(lifeId);
    } catch (e) {
      ckptList.appendChild(empty(e instanceof ApiError ? e.message : String(e)));
    }

    if (!checkpoints.length) ckptList.appendChild(empty(t("branches.noCheckpoint")));
    else checkpoints.forEach((cp) => ckptList.appendChild(checkpointCard(lifeId, cp, draw)));

    const options = [{ id: "main", label: t("branches.mainOpt") }];
    for (const b of branches) options.push({ id: b.branch_id, label: `${b.branch_name} (${b.branch_id})` });

    const cpOptions = [{ id: "", label: t("branches.autoOpt") }];
    for (const cp of checkpoints) cpOptions.push({ id: cp.checkpoint_id, label: cp.checkpoint_id });
    for (const o of cpOptions) {
      const opt = el("option", "", o.label);
      opt.value = o.id;
      cpSelect.appendChild(opt);
    }
    for (const o of options) {
      const a = el("option", "", o.label);
      a.value = o.id;
      selA.appendChild(a);
      const b = el("option", "", o.label);
      b.value = o.id;
      selB.appendChild(b);
    }
    if (options.length > 1) selB.value = options[1].id;

    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      createBtn.disabled = true;
      try {
        await api.createBranch(lifeId, nameInput.value.trim() || "branch", cpSelect.value || null);
        nameInput.value = "";
        toast(t("branches.created"), "ok");
        draw();
      } catch (e) {
        toast(e instanceof ApiError ? e.message : String(e));
        createBtn.disabled = false;
      }
    });

    cmpForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      cmpBtn.disabled = true;
      try {
        const [a, b] = await Promise.all([
          api.branchSnapshot(lifeId, selA.value),
          api.branchSnapshot(lifeId, selB.value),
        ]);
        openDrawer(t("branches.compare"), renderCompare(a, b));
      } catch (e) {
        toast(e instanceof ApiError ? e.message : String(e));
      } finally {
        cmpBtn.disabled = false;
      }
    });

    tree.appendChild(branchTree(lifeId, branches));
  }

  await draw();
}
