import type { ReplayBundle, ReplaySnapshot } from "../types";

export type ReplayInspectorTab = "dossier" | "routing" | "compile" | "frozen" | "messages" | "event";

interface ReplayLabProps {
  isOpen: boolean;
  bundles: ReplayBundle[];
  selectedBundle: ReplayBundle | null;
  activeSnapshot: ReplaySnapshot | null;
  importSessionId: string;
  importError: string | null;
  isImporting: boolean;
  inspectorTab: ReplayInspectorTab;
  isReplayActive: boolean;
  onToggle: () => void;
  onImportSessionIdChange: (value: string) => void;
  onImport: () => void;
  onSelectBundle: (bundleId: string) => void;
  onSelectSnapshot: (snapshotKey: string) => void;
  onDeleteBundle: (bundleId: string) => void;
  onCopyBundle: () => void;
  onDownloadBundle: () => void;
  onTabChange: (tab: ReplayInspectorTab) => void;
  onExitReplay: () => void;
}

const TABS: Array<{ id: ReplayInspectorTab; label: string }> = [
  { id: "dossier", label: "Dossier" },
  { id: "routing", label: "Routing" },
  { id: "compile", label: "Compile" },
  { id: "frozen", label: "Frozen" },
  { id: "messages", label: "Messages" },
  { id: "event", label: "Event" },
];

export function ReplayLab({
  isOpen,
  bundles,
  selectedBundle,
  activeSnapshot,
  importSessionId,
  importError,
  isImporting,
  inspectorTab,
  isReplayActive,
  onToggle,
  onImportSessionIdChange,
  onImport,
  onSelectBundle,
  onSelectSnapshot,
  onDeleteBundle,
  onCopyBundle,
  onDownloadBundle,
  onTabChange,
  onExitReplay,
}: ReplayLabProps) {
  return (
    <>
      <button
        className={`replay-lab-toggle${isOpen ? " replay-lab-toggle--open" : ""}`}
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        aria-controls="replay-lab-panel"
      >
        <span className="replay-lab-toggle__label">Replay Lab</span>
        {activeSnapshot ? <span className="replay-lab-toggle__meta">{activeSnapshot.label}</span> : null}
      </button>

      <aside
        id="replay-lab-panel"
        className={`replay-lab${isOpen ? " replay-lab--open" : ""}`}
        aria-hidden={!isOpen}
      >
        <div className="replay-lab__header">
          <div>
            <p className="replay-lab__eyebrow">Dev Only</p>
            <h2>Replay Lab</h2>
          </div>
          {isReplayActive ? (
            <button className="replay-lab__exit" type="button" onClick={onExitReplay}>
              退出回放
            </button>
          ) : null}
        </div>

        <section className="replay-lab__section replay-lab__section--import">
          <div className="replay-lab__section-heading">
            <h3>导入真实 Session</h3>
            <p>输入一个已经完成 `/api/generate` 的 `session_id`。</p>
          </div>
          <div className="replay-lab__import-row">
            <input
              className="replay-lab__input"
              type="text"
              value={importSessionId}
              placeholder="session_id"
              onChange={(event) => onImportSessionIdChange(event.target.value)}
            />
            <button
              className="replay-lab__button"
              type="button"
              disabled={isImporting || !importSessionId.trim()}
              onClick={onImport}
            >
              {isImporting ? "导入中..." : "导入"}
            </button>
          </div>
          {importError ? <p className="replay-lab__error">{importError}</p> : null}
        </section>

        <section className="replay-lab__section">
          <div className="replay-lab__section-heading">
            <h3>已保存样本</h3>
            <p>{bundles.length > 0 ? "本地可反复回放。" : "还没有保存任何 replay bundle。"}</p>
          </div>
          <div className="replay-lab__bundle-list">
            {bundles.map((bundle) => {
              const isSelected = selectedBundle?.id === bundle.id;
              return (
                <div
                  key={bundle.id}
                  className={`replay-lab__bundle${isSelected ? " replay-lab__bundle--selected" : ""}`}
                >
                  <button className="replay-lab__bundle-main" type="button" onClick={() => onSelectBundle(bundle.id)}>
                    <span className="replay-lab__bundle-name">{bundle.name}</span>
                    <span className="replay-lab__bundle-meta">{bundle.source_session_id.slice(0, 12)}</span>
                  </button>
                  <button
                    className="replay-lab__bundle-delete"
                    type="button"
                    onClick={() => onDeleteBundle(bundle.id)}
                    aria-label={`删除 ${bundle.name}`}
                  >
                    删除
                  </button>
                </div>
              );
            })}
          </div>
        </section>

        {selectedBundle ? (
          <>
            <section className="replay-lab__section replay-lab__section--actions">
              <div className="replay-lab__section-heading">
                <h3>当前样本</h3>
                <p>
                  {selectedBundle.name} · {selectedBundle.snapshots.length} 个快照
                </p>
              </div>
              <div className="replay-lab__action-row">
                <button className="replay-lab__button replay-lab__button--ghost" type="button" onClick={onCopyBundle}>
                  复制 JSON
                </button>
                <button className="replay-lab__button replay-lab__button--ghost" type="button" onClick={onDownloadBundle}>
                  下载 Fixture
                </button>
              </div>
            </section>

            <section className="replay-lab__section">
              <div className="replay-lab__section-heading">
                <h3>阶段快照</h3>
                <p>点击后主画面会直接跳到对应阶段。</p>
              </div>
              <div className="replay-lab__snapshot-list">
                {selectedBundle.snapshots.map((snapshot) => (
                  <button
                    key={snapshot.key}
                    className={`replay-lab__snapshot${activeSnapshot?.key === snapshot.key ? " replay-lab__snapshot--active" : ""}`}
                    type="button"
                    onClick={() => onSelectSnapshot(snapshot.key)}
                  >
                    <span>{snapshot.label}</span>
                    <span className="replay-lab__snapshot-phase">{snapshot.ui_phase}</span>
                  </button>
                ))}
              </div>
            </section>
          </>
        ) : null}

        {activeSnapshot ? (
          <section className="replay-lab__section replay-lab__section--inspector">
            <div className="replay-lab__section-heading">
              <h3>后台检查栏</h3>
              <p>{activeSnapshot.label} · 只读回放</p>
            </div>
            <div className="replay-lab__tabs" role="tablist" aria-label="Replay backstage tabs">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  className={`replay-lab__tab${inspectorTab === tab.id ? " replay-lab__tab--active" : ""}`}
                  type="button"
                  role="tab"
                  aria-selected={inspectorTab === tab.id}
                  onClick={() => onTabChange(tab.id)}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            <div className="replay-lab__inspector">{renderInspector(activeSnapshot, inspectorTab)}</div>
          </section>
        ) : null}
      </aside>
    </>
  );
}

function renderInspector(snapshot: ReplaySnapshot, tab: ReplayInspectorTab) {
  const backstage = snapshot.backstage;
  if (tab === "dossier") {
    const scopeState = backstage.twin_dossier.scope_state ?? {
      primary_scope: "unset",
      primary_anchor: "self",
      scope_locked: false,
      reason: "fallback",
      unresolved_foundations: [],
    };
    return (
      <div className="replay-lab__stack">
        <div className="replay-lab__meta-grid">
          <LabelValue label="世界轮廓" value={backstage.twin_dossier.world_dossier.world_premise} />
          <LabelValue label="张力猜测" value={backstage.twin_dossier.world_dossier.tension_guess} />
          <LabelValue label="场景锚点" value={backstage.twin_dossier.world_dossier.scene_anchor} />
          <LabelValue label="位置幻想" value={backstage.twin_dossier.player_dossier.fantasy_vector} />
          <LabelValue label="情绪核心" value={backstage.twin_dossier.player_dossier.emotional_seed} />
          <LabelValue label="审美偏向" value={backstage.twin_dossier.player_dossier.taste_bias} />
          <LabelValue label="主尺度" value={scopeState.primary_scope} />
          <LabelValue label="投注对象" value={scopeState.primary_anchor} />
          <LabelValue label="是否锁定" value={scopeState.scope_locked ? "locked" : "open"} />
          <LabelValue label="锁定来源" value={scopeState.reason} />
          <LabelValue label="缺失支点" value={scopeState.unresolved_foundations.join(", ")} />
        </div>
        <JsonBlock value={backstage.twin_dossier} />
      </div>
    );
  }

  if (tab === "routing") {
    const routing = backstage.twin_dossier.routing_snapshot;
    return (
      <div className="replay-lab__stack">
        <RoutingGroup title="Confirmed" values={routing.confirmed} />
        <RoutingGroup title="Exploring" values={routing.exploring} />
        <RoutingGroup title="Excluded" values={routing.excluded} />
        <RoutingGroup title="Untouched" values={routing.untouched} />
      </div>
    );
  }

  if (tab === "compile") {
    return backstage.compile_output ? <JsonBlock value={backstage.compile_output} /> : <EmptyState label="这个阶段还没有 CompileOutput。" />;
  }

  if (tab === "frozen") {
    return backstage.frozen_compile_package ? (
      <JsonBlock value={backstage.frozen_compile_package} />
    ) : (
      <EmptyState label="这个阶段还没有 FrozenCompilePackage。" />
    );
  }

  if (tab === "messages") {
    return backstage.messages.length > 0 ? (
      <div className="replay-lab__message-list">
        {backstage.messages.map((message, index) => (
          <article className={`replay-lab__message replay-lab__message--${message.role}`} key={`${message.role}:${index}`}>
            <p className="replay-lab__message-role">{message.role}</p>
            <p className="replay-lab__message-content">{message.content}</p>
          </article>
        ))}
      </div>
    ) : (
      <EmptyState label="这个快照没有消息记录。" />
    );
  }

  return backstage.debug_event ? <JsonBlock value={backstage.debug_event} /> : <EmptyState label="这个快照没有独立 debug event。" />;
}

function LabelValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="replay-lab__meta-card">
      <p>{label}</p>
      <strong>{value || "未命中"}</strong>
    </div>
  );
}

function RoutingGroup({ title, values }: { title: string; values: string[] }) {
  return (
    <div className="replay-lab__routing-group">
      <p>{title}</p>
      <div className="replay-lab__chip-row">
        {values.length > 0 ? values.map((value) => <span className="replay-lab__chip" key={value}>{value}</span>) : <span className="replay-lab__chip replay-lab__chip--empty">空</span>}
      </div>
    </div>
  );
}

function JsonBlock({ value }: { value: unknown }) {
  return <pre className="replay-lab__json">{JSON.stringify(value, null, 2)}</pre>;
}

function EmptyState({ label }: { label: string }) {
  return <p className="replay-lab__empty">{label}</p>;
}
