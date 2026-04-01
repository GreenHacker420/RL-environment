"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type HealthResponse = { status: string };

type MetadataResponse = {
  name: string;
  description: string;
  version: string;
  author: string | null;
  documentation_url: string | null;
};

type StateResponse = {
  episode_id?: string | null;
  step_count?: number;
  task_type?: string;
  current_score?: number;
  safety_violations?: number;
};

type Observation = {
  done?: boolean;
  reward?: number | null;
  prompt?: string;
  task_id?: string;
  task_type?: string;
  feedback?: string;
  partial_score?: number;
  valid_severity_levels?: string[];
  metadata?: Record<string, unknown>;
};

type ResetResponse = {
  observation: Observation;
  reward: number;
  done: boolean;
};

type StepResponse = {
  observation: Observation;
  reward: number | null;
  done: boolean;
};

type BenchmarkEpisode = {
  episode_id: string;
  task_type: string;
  reward: number;
  feedback: string;
  duration_s: number;
};

type BenchmarkSummary = {
  model: string;
  n_episodes: number;
  mean_score: number;
  std_score: number;
  p25: number;
  p50: number;
  p75: number;
  safety_violations: number;
  by_difficulty: Record<string, number>;
  episodes: BenchmarkEpisode[];
};

type InteractionDraft = {
  drug1: string;
  drug2: string;
  severity: string;
};

type ActionDraft = {
  severity: string;
  explanation: string;
  interactions: InteractionDraft[];
  triage: string;
  revised_medications: string;
  metadata: Record<string, unknown>;
};

type LogEntry = {
  id: string;
  title: string;
  detail: string;
};

type WsResponse<T> = {
  type: string;
  data: T;
};

const severityOptions = ["none", "mild", "moderate", "severe"];
const triageOptions = ["normal", "caution", "emergency"];
const WS_URL =
  process.env.NEXT_PUBLIC_OPENENV_WS_URL ?? "ws://127.0.0.1:8000/ws";

const initialAction = (): ActionDraft => ({
  severity: "moderate",
  explanation: "",
  interactions: [],
  triage: "caution",
  revised_medications: "",
  metadata: {},
});

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    cache: "no-store",
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

function scoreTone(score: number | undefined) {
  if (score === undefined) {
    return "warn";
  }
  if (score >= 0.8) {
    return "good";
  }
  if (score >= 0.45) {
    return "warn";
  }
  return "bad";
}

function statusTone(status: string | undefined) {
  return status === "healthy" ? "good" : "bad";
}

export default function Page() {
  const wsRef = useRef<WebSocket | null>(null);
  const wsConnectingRef = useRef<Promise<WebSocket> | null>(null);
  const pendingMessageRef = useRef<{
    resolve: (value: WsResponse<unknown>) => void;
    reject: (reason?: unknown) => void;
  } | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [metadata, setMetadata] = useState<MetadataResponse | null>(null);
  const [state, setState] = useState<StateResponse | null>(null);
  const [currentObservation, setCurrentObservation] = useState<Observation | null>(null);
  const [lastResult, setLastResult] = useState<StepResponse | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkSummary | null>(null);
  const [action, setAction] = useState<ActionDraft>(initialAction);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [socketReady, setSocketReady] = useState(false);

  const currentScore = state?.current_score ?? currentObservation?.partial_score;
  const latestFeedback = currentObservation?.feedback || lastResult?.observation.feedback;
  const latestPrompt = currentObservation?.prompt;

  const benchmarkEpisodes = useMemo(
    () => benchmark?.episodes.slice(0, 5) ?? [],
    [benchmark],
  );

  useEffect(() => {
    void refreshDashboard();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  async function connectWs(): Promise<WebSocket> {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      setSocketReady(true);
      return wsRef.current;
    }

    if (wsConnectingRef.current) {
      return wsConnectingRef.current;
    }

    wsConnectingRef.current = new Promise<WebSocket>((resolve, reject) => {
      const socket = new WebSocket(WS_URL);

      socket.onopen = () => {
        wsRef.current = socket;
        wsConnectingRef.current = null;
        setSocketReady(true);
        resolve(socket);
      };

      socket.onmessage = (event) => {
        const pending = pendingMessageRef.current;
        if (!pending) {
          return;
        }

        pendingMessageRef.current = null;
        const message = JSON.parse(event.data) as WsResponse<unknown>;
        if (message.type === "error") {
          pending.reject(
            new Error(JSON.stringify(message.data) || "WebSocket request failed"),
          );
          return;
        }

        pending.resolve(message);
      };

      socket.onerror = () => {
        setSocketReady(false);
      };

      socket.onclose = () => {
        setSocketReady(false);
        wsRef.current = null;
        wsConnectingRef.current = null;
        if (pendingMessageRef.current) {
          pendingMessageRef.current.reject(new Error("WebSocket connection closed."));
          pendingMessageRef.current = null;
        }
      };

      socket.addEventListener("error", () => {
        wsConnectingRef.current = null;
        reject(new Error(`Failed to connect to ${WS_URL}`));
      });
    });

    return wsConnectingRef.current;
  }

  async function sendWs<T>(message: { type: string; data?: unknown }): Promise<WsResponse<T>> {
    const socket = await connectWs();

    if (pendingMessageRef.current) {
      throw new Error("A WebSocket request is already in flight.");
    }

    const responsePromise = new Promise<WsResponse<T>>((resolve, reject) => {
      pendingMessageRef.current = {
        resolve: (value) => resolve(value as WsResponse<T>),
        reject,
      };
    });

    socket.send(JSON.stringify(message));
    return responsePromise;
  }

  async function refreshDashboard() {
    setError(null);
    try {
      const [healthPayload, metadataPayload, statePayload] = await Promise.all([
        getJson<HealthResponse>("/api/env/health"),
        getJson<MetadataResponse>("/api/env/metadata"),
        sendWs<StateResponse>({ type: "state" }).then((response) => response.data),
      ]);

      setHealth(healthPayload);
      setMetadata(metadataPayload);
      setState(statePayload);

      try {
        const resultsPayload = await getJson<BenchmarkSummary>("/api/results");
        setBenchmark(resultsPayload);
      } catch {
        setBenchmark(null);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Dashboard refresh failed");
    }
  }

  function appendLog(title: string, detail: string) {
    setLogs((current) => [
      {
        id: `${Date.now()}-${Math.random()}`,
        title,
        detail,
      },
      ...current,
    ].slice(0, 8));
  }

  async function handleReset() {
    setBusy(true);
    setError(null);
    try {
      const resetEnvelope = await sendWs<ResetResponse>({ type: "reset", data: {} });
      setCurrentObservation(resetEnvelope.data.observation);
      setLastResult(null);
      setAction(initialAction());
      appendLog(
        "Episode reset",
        `${resetEnvelope.data.observation.task_type ?? "unknown"} task loaded: ${resetEnvelope.data.observation.task_id ?? "no-id"}`,
      );
      await refreshDashboard();
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Reset failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleStep() {
    setBusy(true);
    setError(null);
    try {
      const payload = await sendWs<StepResponse>({
        type: "step",
        data: action,
      });

      setLastResult(payload.data);
      setCurrentObservation(payload.data.observation);
      appendLog(
        "Action submitted",
        `reward=${payload.data.reward ?? 0} done=${payload.data.done} severity=${action.severity} triage=${action.triage}`,
      );
      await refreshDashboard();
    } catch (stepError) {
      setError(stepError instanceof Error ? stepError.message : "Step failed");
    } finally {
      setBusy(false);
    }
  }

  function updateInteraction(index: number, patch: Partial<InteractionDraft>) {
    setAction((current) => ({
      ...current,
      interactions: current.interactions.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...patch } : item,
      ),
    }));
  }

  function addInteraction() {
    setAction((current) => ({
      ...current,
      interactions: [
        ...current.interactions,
        { drug1: "", drug2: "", severity: "moderate" },
      ],
    }));
  }

  function removeInteraction(index: number) {
    setAction((current) => ({
      ...current,
      interactions: current.interactions.filter((_, itemIndex) => itemIndex !== index),
    }));
  }

  return (
    <main className="shell">
      <section className="hero">
        <div className="heroCard">
          <span className="eyebrow">OpenEnv Operations Console</span>
          <h1>Drug Interaction Control Room</h1>
          <p>
            This dashboard sits on top of the real environment service. Reset an
            episode, inspect the task prompt, submit a graded action, and compare
            the live run against the latest benchmark output.
          </p>
        </div>

        <div className="heroCard">
          <div className="panelTitle">
            <h2>Run Surface</h2>
            <span className={`pill ${statusTone(health?.status)}`}>
              {health?.status ?? "unknown"}
            </span>
          </div>
          <div className="sectionStack">
            <div className="keyValue">
              <span className="subtle">Environment</span>
              <span>{metadata?.name ?? "DrugInteractionEnv"}</span>
            </div>
            <div className="keyValue">
              <span className="subtle">Version</span>
              <span className="mono">{metadata?.version ?? "n/a"}</span>
            </div>
            <div className="keyValue">
              <span className="subtle">API proxy</span>
              <span className="mono">/api/env/*</span>
            </div>
            <div className="keyValue">
              <span className="subtle">Session transport</span>
              <span className={`pill ${socketReady ? "good" : "warn"}`}>
                {socketReady ? "websocket connected" : "connects on demand"}
              </span>
            </div>
            <div className="buttonRow">
              <button className="button" onClick={handleReset} disabled={busy}>
                {busy ? "Working..." : "Reset Episode"}
              </button>
              <button className="button secondary" onClick={() => void refreshDashboard()} disabled={busy}>
                Refresh Signals
              </button>
            </div>
            {error ? <div className="feedbackBox">{error}</div> : null}
          </div>
        </div>
      </section>

      <section className="statusGrid">
        <div className="statCard panel">
          <span className="label">Current Task</span>
          <div className="value">{currentObservation?.task_type ?? state?.task_type ?? "idle"}</div>
          <div className="subtle">{currentObservation?.task_id ?? "Reset to start an episode"}</div>
        </div>
        <div className="statCard panel">
          <span className="label">Current Score</span>
          <div className="value">{typeof currentScore === "number" ? currentScore.toFixed(3) : "--"}</div>
          <span className={`pill ${scoreTone(currentScore)}`}>graded reward signal</span>
        </div>
        <div className="statCard panel">
          <span className="label">Episode</span>
          <div className="value mono">{state?.episode_id ? state.episode_id.slice(0, 8) : "--"}</div>
          <div className="subtle">step count: {state?.step_count ?? 0}</div>
        </div>
        <div className="statCard panel">
          <span className="label">Safety Violations</span>
          <div className="value">{state?.safety_violations ?? 0}</div>
          <div className="subtle">dangerous misses tracked server-side</div>
        </div>
      </section>

      <section className="dashboardGrid">
        <div className="sectionStack">
          <div className="panel">
            <div className="panelTitle">
              <h2>Task Prompt</h2>
              <span className="pill">{currentObservation?.task_type ?? "no episode"}</span>
            </div>
            {latestPrompt ? (
              <div className="taskPrompt">{latestPrompt}</div>
            ) : (
              <div className="emptyState">
                No active task yet. Use <span className="mono">Reset Episode</span> to sample one
                from the environment.
              </div>
            )}
          </div>

          <div className="panel">
            <div className="panelTitle">
              <h2>Action Composer</h2>
              <span className="subtle">typed payload for /step</span>
            </div>
            <div className="formGrid">
              <label className="field">
                <span className="label">Severity</span>
                <select
                  className="select"
                  value={action.severity}
                  onChange={(event) =>
                    setAction((current) => ({ ...current, severity: event.target.value }))
                  }
                >
                  {severityOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span className="label">Triage</span>
                <select
                  className="select"
                  value={action.triage}
                  onChange={(event) =>
                    setAction((current) => ({ ...current, triage: event.target.value }))
                  }
                >
                  {triageOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>

              <label className="wideField">
                <span className="label">Explanation</span>
                <textarea
                  className="textarea"
                  value={action.explanation}
                  onChange={(event) =>
                    setAction((current) => ({ ...current, explanation: event.target.value }))
                  }
                  placeholder="Explain the mechanism, risk, and why the severity or triage choice is justified."
                />
              </label>

              <label className="wideField">
                <span className="label">Revised Medications / Advice</span>
                <input
                  className="input"
                  value={action.revised_medications}
                  onChange={(event) =>
                    setAction((current) => ({
                      ...current,
                      revised_medications: event.target.value,
                    }))
                  }
                  placeholder="Hold warfarin, avoid ibuprofen, recheck INR..."
                />
              </label>

              <div className="wideField">
                <div className="panelTitle">
                  <h3>Interaction Pairs</h3>
                  <button className="button secondary" type="button" onClick={addInteraction}>
                    Add Pair
                  </button>
                </div>
                <div className="interactionsList">
                  {action.interactions.length === 0 ? (
                    <div className="emptyState">
                      Add explicit pairs for medium and hard tasks when you want the grader to
                      match named interactions directly.
                    </div>
                  ) : null}
                  {action.interactions.map((item, index) => (
                    <div className="interactionRow" key={`${item.drug1}-${item.drug2}-${index}`}>
                      <input
                        className="input"
                        value={item.drug1}
                        placeholder="drug 1"
                        onChange={(event) =>
                          updateInteraction(index, { drug1: event.target.value })
                        }
                      />
                      <input
                        className="input"
                        value={item.drug2}
                        placeholder="drug 2"
                        onChange={(event) =>
                          updateInteraction(index, { drug2: event.target.value })
                        }
                      />
                      <select
                        className="select"
                        value={item.severity}
                        onChange={(event) =>
                          updateInteraction(index, { severity: event.target.value })
                        }
                      >
                        {severityOptions.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                      <button
                        className="ghostButton"
                        type="button"
                        onClick={() => removeInteraction(index)}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="wideField">
                <div className="buttonRow">
                  <button className="button" onClick={handleStep} disabled={busy || !latestPrompt}>
                    Submit Action
                  </button>
                  <button
                    className="button secondary"
                    type="button"
                    disabled={busy}
                    onClick={() => setAction(initialAction())}
                  >
                    Clear Form
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panelTitle">
              <h2>Latest Reward</h2>
              <span className={`pill ${scoreTone(lastResult?.reward ?? currentObservation?.partial_score)}`}>
                {typeof (lastResult?.reward ?? currentObservation?.partial_score) === "number"
                  ? (lastResult?.reward ?? currentObservation?.partial_score)?.toFixed(3)
                  : "no score"}
              </span>
            </div>
            {latestFeedback ? (
              <div className="feedbackBox">{latestFeedback}</div>
            ) : (
              <div className="emptyState">No grader feedback yet.</div>
            )}
          </div>
        </div>

        <div className="sectionStack">
          <div className="panel">
            <div className="panelTitle">
              <h2>Benchmark Snapshot</h2>
              <span className="pill">{benchmark?.model ?? "results unavailable"}</span>
            </div>
            {benchmark ? (
              <div className="sectionStack">
                <div className="miniGrid">
                  <div className="statCard panel">
                    <span className="label">Mean</span>
                    <div className="value">{benchmark.mean_score.toFixed(3)}</div>
                  </div>
                  <div className="statCard panel">
                    <span className="label">Episodes</span>
                    <div className="value">{benchmark.n_episodes}</div>
                  </div>
                  <div className="statCard panel">
                    <span className="label">P50</span>
                    <div className="value">{benchmark.p50.toFixed(3)}</div>
                  </div>
                  <div className="statCard panel">
                    <span className="label">Safety</span>
                    <div className="value">{benchmark.safety_violations}</div>
                  </div>
                </div>
                <div className="resultsList">
                  {Object.entries(benchmark.by_difficulty).map(([difficulty, score]) => (
                    <div className="keyValue" key={difficulty}>
                      <span className="subtle">{difficulty}</span>
                      <span>{score.toFixed(3)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="emptyState">
                No <span className="mono">results.json</span> found yet. Run the benchmark script to
                populate this panel.
              </div>
            )}
          </div>

          <div className="panel">
            <div className="panelTitle">
              <h2>Recent Benchmark Episodes</h2>
              <span className="subtle">latest 5 from results.json</span>
            </div>
            {benchmarkEpisodes.length > 0 ? (
              <div className="resultsList">
                {benchmarkEpisodes.map((episode) => (
                  <div className="episodeItem" key={episode.episode_id}>
                    <div>
                      <div>{episode.feedback}</div>
                      <div className="episodeMeta">
                        {episode.task_type} · {episode.duration_s.toFixed(2)}s
                      </div>
                    </div>
                    <span className={`pill ${scoreTone(episode.reward)}`}>
                      {episode.reward.toFixed(3)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="emptyState">No benchmark episodes loaded.</div>
            )}
          </div>

          <div className="panel">
            <div className="panelTitle">
              <h2>Event Log</h2>
              <span className="subtle">local UI actions</span>
            </div>
            {logs.length > 0 ? (
              <div className="logList">
                {logs.map((log) => (
                  <div className="logItem" key={log.id}>
                    <div>
                      <div>{log.title}</div>
                      <div className="episodeMeta">{log.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="emptyState">Reset an episode or submit an action to build a trace.</div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
