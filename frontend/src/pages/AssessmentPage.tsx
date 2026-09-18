import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/auth-context';
import { apiUrl } from '../config/api';
import { LensCriteriaEditor } from '../components/LensCriteriaEditor';
import { DiagramPreviewPanel } from '../components/DiagramPreviewPanel';
import { downloadReviewPdf } from '../utils/exportReviewPdf';
import { exportDiagramToPngDataUrl } from '../utils/exportDiagramPng';
import { buildOptimizeSuggestionsSummary, normalizeOptimizeFinding } from '../utils/optimizeSuggestions';
import { toPlainSuggestionText } from '../lib/plainText';

type DiagramItem = {
  id: number;
  title: string;
  updated_at?: string;
  is_owner?: boolean;
};

type Finding = {
  code: string;
  pillar: string;
  severity: string;
  title: string;
  message: string;
  recommendation_hint?: string;
  node_ids?: string[];
  source?: string;
  lens_risk?: string;
};

type RiskCounts = {
  HIGH_RISK?: number;
  MEDIUM_RISK?: number;
  NO_RISK?: number;
};

type Review = {
  id: number;
  diagram_id: number | null;
  status: string;
  overall_score: number | null;
  scores?: {
    source_of_truth?: string;
    pillar_scores?: Record<string, number>;
    weights?: Record<string, number>;
    overall_score?: number;
    risk_counts?: RiskCounts;
    heuristic?: {
      pillar_scores?: Record<string, number>;
      overall_score?: number;
    };
    lens?: {
      risk_counts?: RiskCounts;
      overall_score?: number;
      pillar_scores?: Record<string, number>;
      lens_name?: string;
    };
    lens_error?: string;
    findings_source?: string;
  } | null;
  findings?: Finding[];
  suggestions_text?: string | null;
  error_message?: string | null;
  created_at?: string | null;
  provider?: string;
  xml_snapshot?: string | null;
  has_xml_snapshot?: boolean;
};

type CollabDraftReview = {
  overall_score: number;
  high_risk_count: number;
  findings: Finding[];
  pillar_scores?: Record<string, number>;
  risk_counts?: RiskCounts;
  provider: string;
  collab_status: string;
  lens?: NonNullable<Review['scores']>['lens'];
  suggestions_text?: string;
  rule_pack_version?: string;
  passed?: boolean;
};

type OptimizeDraft = {
  baselineXml: string;
  newXml: string;
  baselineReview: Review | null;
  draftReview: CollabDraftReview;
};

const PILLAR_LABELS: Record<string, string> = {
  operational_excellence: 'Operational Excellence',
  security: 'Security',
  reliability: 'Reliability',
  performance_efficiency: 'Performance Efficiency',
  cost_optimization: 'Cost Optimization',
};

async function readSse(
  response: Response,
  onEvent: (data: Record<string, unknown>) => void
) {
  if (!response.body) throw new Error('無串流回應');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() || '';
    for (const part of parts) {
      const line = part
        .split('\n')
        .find((l) => l.startsWith('data: '));
      if (!line) continue;
      try {
        onEvent(JSON.parse(line.slice(6)));
      } catch {
        /* ignore malformed chunk */
      }
    }
  }
}

export const AssessmentPage = () => {
  const { token, can, canArch } = useAuth();
  const canEdit = can('A3', 'edit');
  const canEditArch = canArch('edit');
  const canEditLens = can('A3', 'review');
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mainTab, setMainTab] = useState<'reviews' | 'lens'>('reviews');

  const [diagrams, setDiagrams] = useState<DiagramItem[]>([]);
  // URL 的 ?diagramId= 只作為初始值；使用者從下拉改選後以其選擇為準（derive，
  // 不用 effect 從 searchParams 同步 state）。
  const [diagramOverride, setDiagramOverride] = useState<number | null>(null);
  const [provider, setProvider] = useState('aws');
  const [replaceLatest, setReplaceLatest] = useState(false);
  const [uploadedXml, setUploadedXml] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [saveDiagram, setSaveDiagram] = useState(false);
  const [saveTitle, setSaveTitle] = useState('');
  const [detectingProvider, setDetectingProvider] = useState(false);
  const [selectedXml, setSelectedXml] = useState<string | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [active, setActive] = useState<Review | null>(null);
  const [suggestionsLive, setSuggestionsLive] = useState('');
  const [phase, setPhase] = useState<string>('idle');
  const [error, setError] = useState<string | null>(null);
  const [collabRunning, setCollabRunning] = useState(false);
  const [collabLog, setCollabLog] = useState<string[]>([]);
  const [collabPreviewXml, setCollabPreviewXml] = useState<string | null>(null);
  const [collabScore, setCollabScore] = useState<number | null>(null);
  const [collabStatus, setCollabStatus] = useState<string | null>(null);
  const [optimizeDraft, setOptimizeDraft] = useState<OptimizeDraft | null>(null);
  const [savingOptimize, setSavingOptimize] = useState(false);
  const [savingPersist, setSavingPersist] = useState(false);
  const [deletingReviewId, setDeletingReviewId] = useState<number | null>(null);
  const [deletingDiagram, setDeletingDiagram] = useState(false);
  const optimizeBaselineRef = useRef<{ xml: string; review: Review | null } | null>(
    null,
  );
  // 記錄「歷史評核已載入哪張圖」，loadingList 由此推導；如此 effect body 內不需
  // 同步 setState（react-hooks/set-state-in-effect）。事件處理可直接設回 null 以
  // 重新顯示載入中。
  const [loadedFor, setLoadedFor] = useState<number | null>(null);
  const [openingId, setOpeningId] = useState<number | null>(null);
  const [exportingPdf, setExportingPdf] = useState(false);
  const resultRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const saveDiagramRef = useRef(false);

  const authHeaders = useMemo(
    () => ({
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    }),
    [token]
  );

  // 純抓取，完全不碰 state。react-hooks/set-state-in-effect 會做過程間分析：
  // 只要 effect 同步呼叫的函式內部有 setState 就會被擋，因此 state 更新一律留在
  // 呼叫端的 callback 內（規則允許的形式）。
  const fetchDiagrams = useCallback(async () => {
    const res = await fetch(apiUrl('/api/collab/diagrams'), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null;
    return res.json();
  }, [token]);

  const fetchReviews = useCallback(
    async (diagramId: number) => {
      const res = await fetch(
        apiUrl(`/api/architecture/reviews?diagram_id=${diagramId}`),
        { headers: { Authorization: `Bearer ${token}` } }
      );
      return res.ok ? res.json() : null;
    },
    [token]
  );

  const fetchEphemeralReviews = useCallback(async () => {
    const res = await fetch(
      apiUrl('/api/architecture/reviews?ephemeral=true'),
      { headers: { Authorization: `Bearer ${token}` } },
    );
    return res.ok ? res.json() : null;
  }, [token]);

  // 事件處理呼叫用：先切到 loading 再抓。
  const loadReviews = useCallback(
    (diagramId: number) => {
      setLoadedFor(null);
      return fetchReviews(diagramId)
        .then((data) => { if (data) setReviews(data); })
        .finally(() => setLoadedFor(diagramId));
    },
    [fetchReviews]
  );

  const loadEphemeralReviews = useCallback(() => {
    setLoadedFor(null);
    return fetchEphemeralReviews()
      .then((data) => { if (data) setReviews(data); })
      .finally(() => setLoadedFor(0));
  }, [fetchEphemeralReviews]);

  const urlDiagramId = useMemo(() => {
    const q = searchParams.get('diagramId');
    if (!q) return null;
    const id = Number(q);
    return Number.isNaN(id) ? null : id;
  }, [searchParams]);
  const selectedDiagramId = diagramOverride ?? urlDiagramId;
  const loadingList =
    selectedDiagramId !== null
      ? loadedFor !== selectedDiagramId
      : loadedFor !== 0;

  useEffect(() => {
    let cancelled = false;
    fetchDiagrams().then((data) => { if (!cancelled && data) setDiagrams(data); });
    return () => { cancelled = true; };
  }, [fetchDiagrams]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedDiagramId) {
      fetchEphemeralReviews()
        .then((data) => {
          if (cancelled) return;
          setReviews(Array.isArray(data) ? data : []);
        })
        .finally(() => {
          if (!cancelled) setLoadedFor(0);
        });
      return () => {
        cancelled = true;
      };
    }

    // loadedFor !== selectedDiagramId 時 loadingList 已為 true，不必同步清 loadedFor
    fetchReviews(selectedDiagramId)
      .then(async (data) => {
        if (cancelled || !data) return;
        setReviews(data);
        if (!Array.isArray(data) || data.length === 0) {
          setActive(null);
          setSuggestionsLive('');
          setPhase('idle');
          return;
        }
        const latest = data[0] as Review;
        try {
          const res = await fetch(
            apiUrl(`/api/architecture/reviews/${latest.id}`),
            { headers: { Authorization: `Bearer ${token}` } },
          );
          if (cancelled) return;
          if (res.ok) {
            const full = (await res.json()) as Review;
            setActive(full);
            setSuggestionsLive(full.suggestions_text || '');
            setPhase(full.status);
            setError(full.error_message || null);
          } else {
            setActive(latest);
            setSuggestionsLive(latest.suggestions_text || '');
            setPhase(latest.status);
          }
        } catch {
          if (!cancelled) {
            setActive(latest);
            setSuggestionsLive(latest.suggestions_text || '');
            setPhase(latest.status);
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoadedFor(selectedDiagramId);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedDiagramId, fetchReviews, fetchEphemeralReviews, token]);

  const detectProviderFromXml = async (xml: string) => {
    if (!xml.trim() || !token) return;
    setDetectingProvider(true);
    try {
      const res = await fetch(apiUrl('/api/architecture/reviews/detect-provider'), {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ xml_data: xml }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `偵測雲端失敗（HTTP ${res.status}）`);
      }
      const data = (await res.json()) as { provider?: string };
      if (data.provider) setProvider(data.provider);
    } catch (e) {
      setError(e instanceof Error ? e.message : '偵測雲端提供者失敗');
    } finally {
      setDetectingProvider(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    if (!selectedDiagramId || !token) {
      Promise.resolve().then(() => {
        if (!cancelled) setSelectedXml(null);
      });
      return () => {
        cancelled = true;
      };
    }
    if (uploadedXml) return;
    (async () => {
      try {
        const res = await fetch(apiUrl(`/api/collab/diagrams/${selectedDiagramId}`), {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
          if (!cancelled) setSelectedXml(null);
          return;
        }
        const data = await res.json();
        const xml = (data.xml_data as string) || null;
        if (cancelled) return;
        setSelectedXml(xml);
        if (xml) await detectProviderFromXml(xml);
      } catch {
        if (!cancelled) setSelectedXml(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedDiagramId, token, uploadedXml]);

  const previewXml =
    optimizeDraft?.newXml ||
    uploadedXml ||
    selectedXml ||
    active?.xml_snapshot ||
    null;
  const previewTitle =
    uploadedFileName ||
    diagrams.find((d) => d.id === selectedDiagramId)?.title ||
    diagrams.find((d) => d.id === active?.diagram_id)?.title ||
    '架構圖預覽';

  const countHighRiskFromReview = (review: Review | null | undefined) => {
    const fromCounts =
      review?.scores?.risk_counts?.HIGH_RISK ??
      review?.scores?.lens?.risk_counts?.HIGH_RISK;
    if (typeof fromCounts === 'number') return fromCounts;
    return (review?.findings || []).filter(
      (f) => f.severity === 'high' || f.lens_risk === 'HIGH_RISK',
    ).length;
  };

  const buildDraftSuggestions = (
    baselineReview: Review | null,
    draftReview: CollabDraftReview,
  ) => {
    const baselineFindings = (baselineReview?.findings || []).map((f) =>
      normalizeOptimizeFinding(f),
    );
    const newFindings = (draftReview.findings || []).map((f) =>
      normalizeOptimizeFinding(f),
    );
    return buildOptimizeSuggestionsSummary(baselineFindings, newFindings, {
      baselineScore: baselineReview?.overall_score,
      newScore: draftReview.overall_score,
      baselineHighRisk: countHighRiskFromReview(baselineReview),
      newHighRisk: draftReview.high_risk_count,
    });
  };

  const clearOptimizeDraft = () => {
    setOptimizeDraft(null);
    setCollabPreviewXml(null);
    setCollabLog([]);
    setCollabScore(null);
    setCollabStatus(null);
    optimizeBaselineRef.current = null;
  };

  const cancelOptimizeDraft = () => {
    if (!optimizeDraft) return;
    const base = optimizeDraft.baselineReview;
    clearOptimizeDraft();
    if (base) {
      setActive(base);
      setSuggestionsLive(base.suggestions_text || '');
      setPhase(base.status);
    } else {
      setActive(null);
      setSuggestionsLive('');
      setPhase('idle');
    }
  };

  const finalizeOptimizeDraft = (data: Record<string, unknown>) => {
    const base = optimizeBaselineRef.current;
    if (!base || typeof data.xml !== 'string' || !data.xml) return;
    const dr = (data.draft_review || {}) as Record<string, unknown>;
    const rawFindings =
      (Array.isArray(dr.findings) && dr.findings.length > 0
        ? dr.findings
        : data.findings) || [];
    const draftReview: CollabDraftReview = {
      overall_score: Number(dr.overall_score ?? data.overall_score ?? 0),
      high_risk_count: Number(dr.high_risk_count ?? data.high_risk_count ?? 0),
      findings: (rawFindings as Finding[]).map((f) => normalizeOptimizeFinding(f)),
      pillar_scores: dr.pillar_scores as Record<string, number> | undefined,
      risk_counts: dr.risk_counts as RiskCounts | undefined,
      provider: String(dr.provider || provider),
      collab_status: String(data.status || dr.collab_status || 'complete'),
      lens: dr.lens as CollabDraftReview['lens'],
      rule_pack_version: dr.rule_pack_version as string | undefined,
      passed: Boolean(dr.passed ?? data.status === 'passed'),
      suggestions_text: '',
    };
    const serverSuggestions = String(dr.suggestions_text || '').trim();
    draftReview.suggestions_text =
      serverSuggestions || buildDraftSuggestions(base.review, draftReview);
    setOptimizeDraft({
      baselineXml: base.xml,
      newXml: data.xml,
      baselineReview: base.review,
      draftReview,
    });
    setCollabPreviewXml(data.xml);
    setActive({
      id: 0,
      diagram_id: selectedDiagramId,
      status: 'draft',
      overall_score: draftReview.overall_score,
      findings: draftReview.findings,
      scores: {
        source_of_truth: 'offline_lens',
        overall_score: draftReview.overall_score,
        pillar_scores: draftReview.pillar_scores,
        risk_counts: draftReview.risk_counts,
        lens: draftReview.lens,
      },
      provider: draftReview.provider,
      suggestions_text: draftReview.suggestions_text,
    });
    setPhase('draft');
    setSuggestionsLive(draftReview.suggestions_text || '');
    requestAnimationFrame(() => {
      resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };

  const saveOptimizeDraft = async () => {
    if (!optimizeDraft || !selectedDiagramId) {
      setError('請先選擇已建檔的架構圖再儲存優化結果');
      return;
    }
    setSavingOptimize(true);
    setError(null);
    try {
      const dr = optimizeDraft.draftReview;
      const res = await fetch(apiUrl('/api/architecture/reviews/commit-collab'), {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          diagram_id: selectedDiagramId,
          xml_data: optimizeDraft.newXml,
          provider: dr.provider || provider,
          overall_score: dr.overall_score,
          pillar_scores: dr.pillar_scores,
          findings: dr.findings,
          high_risk_count: dr.high_risk_count,
          passed: dr.passed ?? false,
          rule_pack_version: dr.rule_pack_version,
          suggestions_text:
            optimizeDraft.draftReview.suggestions_text ||
            collabLog.join('\n\n').slice(0, 8000) ||
            undefined,
          lens: dr.lens,
          collab_status: dr.collab_status,
        }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `儲存失敗（HTTP ${res.status}）`);
      }
      const saved = (await res.json()) as Review;
      setSelectedXml(optimizeDraft.newXml);
      clearOptimizeDraft();
      setActive(saved);
      setSuggestionsLive(saved.suggestions_text || '');
      setPhase(saved.status);
      await loadReviews(selectedDiagramId);
    } catch (e) {
      setError(e instanceof Error ? e.message : '儲存優化結果失敗');
    } finally {
      setSavingOptimize(false);
    }
  };

  const applySseEvent = (data: Record<string, unknown>) => {
    const type = String(data.type || '');
    const maybeAdoptSavedDiagram = (reviewId: number | null) => {
      if (!saveDiagramRef.current) return;
      saveDiagramRef.current = false;
      const adopt = async () => {
        const list = await fetchDiagrams();
        if (list) setDiagrams(list);
        let newId: number | null =
          data.diagram_id != null && !Number.isNaN(Number(data.diagram_id))
            ? Number(data.diagram_id)
            : null;
        if (newId == null && reviewId != null) {
          try {
            const res = await fetch(
              apiUrl(`/api/architecture/reviews/${reviewId}`),
              { headers: { Authorization: `Bearer ${token}` } }
            );
            if (res.ok) {
              const review = (await res.json()) as Review;
              if (review.diagram_id) newId = review.diagram_id;
            }
          } catch {
            /* ignore */
          }
        }
        if (newId != null) {
          setDiagramOverride(newId);
          setUploadedXml(null);
          setUploadedFileName(null);
          setSaveDiagram(false);
        }
      };
      void adopt();
    };

    if (type === 'rules_done') {
      setPhase('rules');
      const reviewId = Number(data.review_id);
      maybeAdoptSavedDiagram(Number.isNaN(reviewId) ? null : reviewId);
      setActive((prev) => ({
        ...(prev || { id: reviewId, diagram_id: selectedDiagramId, status: 'rules_complete' }),
        id: reviewId,
        status: 'rules_complete',
        overall_score: (data.overall_score as number) ?? null,
        scores: data.scores as Review['scores'],
        findings: data.findings as Finding[],
        provider: (data.provider as string) || (data.resolved_provider as string) || prev?.provider,
        diagram_id:
          data.diagram_id != null
            ? Number(data.diagram_id)
            : (prev?.diagram_id ?? selectedDiagramId ?? null),
      }));
    } else if (type === 'lens_done') {
      setPhase('lens');
      setActive((prev) => ({
        ...(prev || { id: Number(data.review_id), diagram_id: selectedDiagramId, status: 'rules_complete' }),
        id: Number(data.review_id),
        status: 'rules_complete',
        overall_score: (data.overall_score as number) ?? null,
        scores: data.scores as Review['scores'],
        findings: (data.findings as Finding[]) || prev?.findings || [],
      }));
      requestAnimationFrame(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    } else if (type === 'suggestion_delta') {
      setPhase('suggestions');
      setSuggestionsLive((s) => s + String(data.content || ''));
      // Keep result panel in view while streaming
      requestAnimationFrame(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
    } else if (type === 'complete') {
      setPhase('done');
      const text = String(data.suggestions_text || '');
      if (text) setSuggestionsLive(text);
      const reviewId = Number(data.review_id);
      maybeAdoptSavedDiagram(Number.isNaN(reviewId) ? null : reviewId);
      setActive((prev) =>
        prev
          ? {
              ...prev,
              status: 'complete',
              suggestions_text: text || prev.suggestions_text,
              overall_score:
                data.overall_score != null
                  ? (data.overall_score as number)
                  : prev.overall_score,
              scores: (data.scores as Review['scores']) || prev.scores,
              error_message: null,
            }
          : prev
      );
      if (selectedDiagramId) loadReviews(selectedDiagramId);
      else void loadEphemeralReviews();
      requestAnimationFrame(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    } else if (type === 'unsupported') {
      setPhase('unsupported');
      setError(String(data.message || '未支援的雲端提供者'));
      saveDiagramRef.current = false;
      if (selectedDiagramId) loadReviews(selectedDiagramId);
    } else if (type === 'error') {
      if (data.code === 'lens_error') {
        // Q6=A / Q5=B: heuristics continue; soft warning; may include heuristic findings
        setError(`Lens 失敗，已保留啟發式分數／發現：${String(data.message || '')}`);
        setActive((prev) =>
          prev
            ? {
                ...prev,
                scores: (data.scores as Review['scores']) || prev.scores,
                findings:
                  (data.findings as Finding[]) || prev.findings || [],
              }
            : prev
        );
        return;
      }
      setPhase('error');
      setError(String(data.message || '評核失敗'));
      saveDiagramRef.current = false;
      const fallbackText = String(data.suggestions_text || '');
      if (fallbackText) setSuggestionsLive(fallbackText);
      setActive((prev) =>
        prev
          ? {
              ...prev,
              status: String(data.status || prev.status),
              error_message: String(data.message || ''),
              scores: (data.scores as Review['scores']) || prev.scores,
              overall_score:
                data.overall_score != null
                  ? (data.overall_score as number)
                  : prev.overall_score,
              suggestions_text: fallbackText || prev.suggestions_text,
            }
          : prev
      );
      if (selectedDiagramId) loadReviews(selectedDiagramId);
    }
  };

  const handleUploadFile = async (file: File | null) => {
    if (!file) return;
    setError(null);
    try {
      const text = await file.text();
      if (!text.trim()) {
        setError('檔案內容為空');
        return;
      }
      setUploadedXml(text);
      setUploadedFileName(file.name);
      await detectProviderFromXml(text);
    } catch (e) {
      setError(e instanceof Error ? e.message : '讀取檔案失敗');
    }
  };

  const clearUpload = () => {
    setUploadedXml(null);
    setUploadedFileName(null);
    setSaveDiagram(false);
    setSaveTitle('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const reviewNeedsPersist =
    Boolean(active) &&
    canEdit &&
    canEditArch &&
    !optimizeDraft &&
    (active?.diagram_id == null || active.diagram_id === 0) &&
    Boolean(uploadedXml || active?.xml_snapshot || active?.has_xml_snapshot);

  const selectedDiagramMeta = diagrams.find((d) => d.id === selectedDiagramId);
  const canDeleteSelectedDiagram =
    Boolean(selectedDiagramId) &&
    canEditArch &&
    (selectedDiagramMeta?.is_owner !== false);

  const persistUploadReview = async () => {
    if (!active || !reviewNeedsPersist) return;
    setSavingPersist(true);
    setError(null);
    try {
      const res = await fetch(
        apiUrl(`/api/architecture/reviews/${active.id}/persist-diagram`),
        {
          method: 'POST',
          headers: authHeaders,
          body: JSON.stringify({
            title: saveTitle.trim() || uploadedFileName || '上傳的架構圖',
            xml_data: uploadedXml || active.xml_snapshot || undefined,
          }),
        },
      );
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `儲存失敗（HTTP ${res.status}）`);
      }
      const data = (await res.json()) as {
        diagram_id: number;
        review_id: number;
        review?: Review;
      };
      const list = await fetchDiagrams();
      if (list) setDiagrams(list);
      setDiagramOverride(data.diagram_id);
      clearUpload();
      if (data.review) {
        setActive(data.review);
        setSuggestionsLive(data.review.suggestions_text || '');
        setPhase(data.review.status);
      } else {
        setActive((prev) =>
          prev ? { ...prev, diagram_id: data.diagram_id } : prev,
        );
      }
      await loadReviews(data.diagram_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : '儲存架構圖與評核失敗');
    } finally {
      setSavingPersist(false);
    }
  };

  const deleteReviewById = async (reviewId: number) => {
    if (!canEdit) return;
    if (!window.confirm(`確定刪除評核 #${reviewId}？此操作會自列表隱藏該報告。`)) {
      return;
    }
    setDeletingReviewId(reviewId);
    setError(null);
    try {
      const res = await fetch(apiUrl(`/api/architecture/reviews/${reviewId}`), {
        method: 'DELETE',
        headers: authHeaders,
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `刪除評核失敗（HTTP ${res.status}）`);
      }
      if (active?.id === reviewId) {
        setActive(null);
        setSuggestionsLive('');
        setPhase('idle');
      }
      if (selectedDiagramId) await loadReviews(selectedDiagramId);
      else await loadEphemeralReviews();
    } catch (e) {
      setError(e instanceof Error ? e.message : '刪除評核失敗');
    } finally {
      setDeletingReviewId(null);
    }
  };

  const deleteSelectedDiagram = async () => {
    if (!selectedDiagramId || !canDeleteSelectedDiagram) return;
    const title = selectedDiagramMeta?.title || `#${selectedDiagramId}`;
    if (
      !window.confirm(
        `確定刪除架構圖「${title}」？\n該圖的評核紀錄與聊天也會一併刪除，且無法復原。`,
      )
    ) {
      return;
    }
    setDeletingDiagram(true);
    setError(null);
    try {
      const res = await fetch(apiUrl(`/api/collab/diagrams/${selectedDiagramId}`), {
        method: 'DELETE',
        headers: authHeaders,
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `刪除架構圖失敗（HTTP ${res.status}）`);
      }
      setDiagramOverride(null);
      setActive(null);
      setSuggestionsLive('');
      setPhase('idle');
      setReviews([]);
      const list = await fetchDiagrams();
      if (list) setDiagrams(list);
      await loadEphemeralReviews();
    } catch (e) {
      setError(e instanceof Error ? e.message : '刪除架構圖失敗');
    } finally {
      setDeletingDiagram(false);
    }
  };

  const canRunReview = Boolean(selectedDiagramId || uploadedXml) && canEdit;
  const reviewInProgress =
    phase === 'running' ||
    phase === 'rules' ||
    phase === 'lens' ||
    phase === 'suggestions';
  const highRiskCount = (() => {
    const fromCounts =
      active?.scores?.risk_counts?.HIGH_RISK ??
      active?.scores?.lens?.risk_counts?.HIGH_RISK;
    if (typeof fromCounts === 'number' && fromCounts > 0) return fromCounts;
    const fromFindings = (active?.findings || []).filter(
      (f) => f.severity === 'high' || f.lens_risk === 'HIGH_RISK',
    ).length;
    if (fromFindings > 0) return fromFindings;
    return typeof fromCounts === 'number' ? fromCounts : 0;
  })();
  const hasHighRisk = highRiskCount > 0;
  const overallScore = (() => {
    const fromActive = active?.overall_score;
    if (typeof fromActive === 'number') return fromActive;
    const fromScores = active?.scores?.overall_score ?? active?.scores?.lens?.overall_score;
    return typeof fromScores === 'number' ? fromScores : null;
  })();
  const SCORE_TARGET = 80;
  const scoreBelowTarget =
    typeof overallScore === 'number' && overallScore < SCORE_TARGET;
  const needsOptimize = hasHighRisk || scoreBelowTarget;
  const canRunWaCollab =
    Boolean(previewXml) &&
    Boolean(selectedDiagramId) &&
    canEdit &&
    canEditArch &&
    !collabRunning &&
    !reviewInProgress &&
    !optimizeDraft &&
    needsOptimize;

  const waCollabDisabledReason = !canEditArch
    ? '需要架構圖編輯權才能啟動 Design↔Review 協作'
    : !selectedDiagramId
      ? '請先選擇已建檔架構圖（儲存時覆蓋原圖）'
      : optimizeDraft
        ? '請先儲存或取消目前的優化結果'
        : reviewInProgress || collabRunning
          ? '評核進行中，請稍候再優化'
          : !needsOptimize
            ? `目前無高風險且分數 ≥ ${SCORE_TARGET}，無需優化`
            : !previewXml
              ? '請先選擇或上傳架構圖'
              : hasHighRisk && scoreBelowTarget
                ? `依高風險與分數（< ${SCORE_TARGET}）優化架構圖`
                : hasHighRisk
                  ? '依高風險建議優化架構圖'
                  : `分數未達 ${SCORE_TARGET}，依建議優化架構圖`;

  const runReview = async () => {
    if (!canRunReview) return;
    setError(null);
    setSuggestionsLive('');
    setActive(null);
    setPhase('running');
    saveDiagramRef.current = Boolean(uploadedXml && saveDiagram);
    try {
      const body: Record<string, unknown> = {
        provider,
        auto_detect_provider: false,
        replace_latest: replaceLatest,
      };
      if (uploadedXml) {
        body.xml_data = uploadedXml;
        if (saveDiagram) {
          body.save_diagram = true;
          body.title = saveTitle.trim() || uploadedFileName || '上傳的架構圖';
        }
      } else if (selectedDiagramId) {
        body.diagram_id = selectedDiagramId;
      }
      const res = await fetch(apiUrl('/api/architecture/reviews'), {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `HTTP ${res.status}`);
      }
      await readSse(res, applySseEvent);
    } catch (e) {
      setPhase('error');
      setError(e instanceof Error ? e.message : '發起評核失敗');
      saveDiagramRef.current = false;
    }
  };

  const runWaOptimize = async () => {
    if (!canRunWaCollab || !previewXml || !selectedDiagramId) return;
    setError(null);
    setCollabRunning(true);
    setCollabLog([]);
    setCollabPreviewXml(null);
    setCollabScore(null);
    setCollabStatus(null);
    optimizeBaselineRef.current = {
      xml: previewXml,
      review: active ? { ...active, findings: active.findings ? [...active.findings] : [] } : null,
    };
    const logLines: string[] = [];
    try {
      const res = await fetch(apiUrl('/api/architecture/generate-wa-collab'), {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          messages: [
            {
              role: 'user',
              content:
                '請依 Well-Architected 高風險發現改善目前架構圖。' +
                '目標：架構圖不得再含 HIGH_RISK；請呼叫 draw_architecture_diagram 改圖。',
            },
          ],
          current_xml: previewXml,
          provider,
          diagram_id: selectedDiagramId,
          persist_review: false,
          baseline_findings: active?.findings || [],
          baseline_overall_score: active?.overall_score ?? null,
        }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `HTTP ${res.status}`);
      }
      await readSse(res, (data) => {
        if (data.type === 'message') {
          const who =
            data.speaker === 'review'
              ? 'Review'
              : data.speaker === 'design'
                ? 'Design'
                : '系統';
          const chunk = String(data.content || '');
          const prefix = `[${who}] `;
          const last = logLines[logLines.length - 1];
          if (last?.startsWith(prefix)) {
            logLines[logLines.length - 1] = last + chunk;
          } else {
            logLines.push(prefix + chunk);
          }
          setCollabLog([...logLines]);
        } else if (data.type === 'progress') {
          const line = String(data.content || '');
          logLines.push(line);
          setCollabLog([...logLines]);
        } else if (data.type === 'xml_preview') {
          const xmlData = String(data.content || '');
          if (xmlData) setCollabPreviewXml(xmlData);
        } else if (data.type === 'score') {
          if (typeof data.overall_score === 'number') {
            setCollabScore(data.overall_score);
          }
          logLines.push(
            `第 ${data.round ?? '?'} 輪分數：${
              typeof data.overall_score === 'number'
                ? Math.round(data.overall_score)
                : '—'
            }（高風險 ${data.high_risk_count ?? '—'} 項）`,
          );
          setCollabLog([...logLines]);
        } else if (data.type === 'complete') {
          setCollabStatus(String(data.status || ''));
          if (typeof data.overall_score === 'number') {
            setCollabScore(data.overall_score);
          }
          if (typeof data.xml === 'string' && data.xml) {
            setCollabPreviewXml(data.xml);
            finalizeOptimizeDraft(data);
          }
        } else if (data.type === 'error') {
          setError(String(data.content || data.message || '協作失敗'));
        }
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : '優化失敗');
      optimizeBaselineRef.current = null;
    } finally {
      setCollabRunning(false);
    }
  };

  const retrySuggestions = async () => {
    if (!active?.id || !canEdit) return;
    setError(null);
    setSuggestionsLive('');
    setPhase('suggestions');
    try {
      const res = await fetch(
        apiUrl(`/api/architecture/reviews/${active.id}/retry-suggestions`),
        { method: 'POST', headers: authHeaders }
      );
      if (!res.ok) throw new Error(await res.text());
      await readSse(res, applySseEvent);
    } catch (e) {
      setPhase('error');
      setError(e instanceof Error ? e.message : '重試建議失敗');
    }
  };

  const openReview = async (preview: Review) => {
    setError(null);
    setOpeningId(preview.id);
    // 先用列表資料立刻顯示，避免「沒反應」
    setActive(preview);
    setSuggestionsLive(preview.suggestions_text || '');
    setPhase(preview.status);
    requestAnimationFrame(() => {
      resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    try {
      const res = await fetch(apiUrl(`/api/architecture/reviews/${preview.id}`), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const detail = await res.text();
        setError(detail || `無法開啟評核 #${preview.id}（HTTP ${res.status}）`);
        return;
      }
      const data = (await res.json()) as Review;
      setActive(data);
      setSuggestionsLive(data.suggestions_text || '');
      setPhase(data.status);
      setError(data.error_message || null);
      requestAnimationFrame(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : '開啟評核失敗');
    } finally {
      setOpeningId(null);
    }
  };

  const canDownloadPdf =
    Boolean(active) &&
    active?.id !== 0 &&
    phase !== 'draft' &&
    (active?.status === 'complete' || active?.status === 'rules_only') &&
    can('A3', 'view');

  const exportPdf = async () => {
    if (!active || !canDownloadPdf) return;
    setExportingPdf(true);
    setError(null);
    try {
      const diagramTitle =
        diagrams.find((d) => d.id === active.diagram_id)?.title ||
        diagrams.find((d) => d.id === selectedDiagramId)?.title ||
        uploadedFileName ||
        undefined;

      let diagramImageDataUrl: string | null = null;
      const xmlForPdf =
        previewXml ||
        active.xml_snapshot ||
        selectedXml ||
        uploadedXml ||
        null;
      if (xmlForPdf) {
        try {
          diagramImageDataUrl = await exportDiagramToPngDataUrl(xmlForPdf);
        } catch {
          // 後端轉圖備援（外部 API 常不可用）
          try {
            const renderRes = await fetch(
              apiUrl('/api/architecture/diagrams/render-png'),
              {
                method: 'POST',
                headers: authHeaders,
                body: JSON.stringify({ xml_data: xmlForPdf }),
              }
            );
            if (renderRes.ok) {
              const rendered = await renderRes.json();
              if (typeof rendered.data_url === 'string') {
                diagramImageDataUrl = rendered.data_url;
              }
            }
          } catch {
            /* PDF 仍可匯出，僅缺圖 */
          }
        }
      }

      await downloadReviewPdf({
        id: active.id,
        diagramTitle,
        status: active.status,
        overall_score: active.overall_score,
        created_at: active.created_at,
        provider: active.provider,
        lensName: active.scores?.lens?.lens_name,
        findings_source: active.scores?.findings_source,
        pillar_scores: active.scores?.pillar_scores,
        risk_counts: active.scores?.risk_counts || active.scores?.lens?.risk_counts,
        findings: active.findings,
        suggestions_text: suggestionsLive || active.suggestions_text,
        diagramImageDataUrl,
      });
      if (xmlForPdf && !diagramImageDataUrl) {
        setError('PDF 已下載，但架構圖匯出失敗（報告未附圖）。請確認可連線 diagrams.net 後重試。');
      }    } catch (e) {
      setError(e instanceof Error ? e.message : 'PDF 匯出失敗');
    } finally {
      setExportingPdf(false);
    }
  };

  // Prefer Lens scores; also accept lens payload without source_of_truth (compat)
  const lensReady =
    active?.scores?.source_of_truth === 'offline_lens' ||
    Boolean(active?.scores?.lens) ||
    Boolean(active?.scores?.risk_counts);
  const pillarScores = lensReady
    ? active?.scores?.pillar_scores || active?.scores?.lens?.pillar_scores || {}
    : {};
  const riskCounts = lensReady
    ? active?.scores?.risk_counts || active?.scores?.lens?.risk_counts || null
    : null;
  const displayOverall = lensReady
    ? active?.overall_score ?? active?.scores?.overall_score ?? null
    : null;
  const lensPending =
    active != null &&
    !lensReady &&
    (phase === 'running' ||
      phase === 'rules' ||
      active.scores?.source_of_truth === 'pending_lens');
  const lensFailed =
    !lensReady &&
    (active?.scores?.source_of_truth === 'heuristic' ||
      Boolean(active?.scores?.lens_error));
  const optimizeSuggestionsText = optimizeDraft
    ? optimizeDraft.draftReview.suggestions_text ||
      buildDraftSuggestions(optimizeDraft.baselineReview, optimizeDraft.draftReview)
    : '';
  const suggestionsText = (
    optimizeSuggestionsText ||
    suggestionsLive ||
    active?.suggestions_text ||
    ''
  ).trim();
  const isStreamingSuggestions =
    !optimizeDraft &&
    (phase === 'suggestions' || phase === 'lens' || phase === 'running');
  const suggestionsPlaceholder = (() => {
    if (phase === 'draft') {
      return '（優化完成後將顯示改善摘要與剩餘風險建議）';
    }
    if (phase === 'running' || phase === 'rules' || phase === 'lens') {
      return '（評核進行中，稍後串流建議…）';
    }
    if (phase === 'suggestions') {
      return '（Agent 正在串流產生建議…）';
    }
    if (active?.status === 'rules_only') {
      return '（Agent 建議失敗，可點「重試建議」；若已有備援文字會顯示於上方）';
    }
    if (active?.status === 'complete' || active?.status === 'unsupported') {
      return '（本次評核無 Agent 建議文字）';
    }
    return '（尚無建議）';
  })();

  return (
    <div className="h-full overflow-y-auto bg-gray-50 p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">評估儀表板</h1>
            <p className="text-sm text-gray-500 mt-1">
              Well-Architected 評核：離線 Lens 分數與風險計數＋AI 改善建議（支援 AWS／GCP／Azure）
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/workspace')}
            className="text-sm font-semibold text-brand-700 hover:underline"
          >
            返回工作區
          </button>
        </div>

        {canEditLens && (
          <div className="flex gap-1 border-b border-gray-200">
            <button
              type="button"
              onClick={() => setMainTab('reviews')}
              className={`px-4 py-2 text-sm font-semibold border-b-2 -mb-px ${
                mainTab === 'reviews'
                  ? 'border-brand-600 text-brand-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              評核
            </button>
            <button
              type="button"
              onClick={() => setMainTab('lens')}
              className={`px-4 py-2 text-sm font-semibold border-b-2 -mb-px ${
                mainTab === 'lens'
                  ? 'border-brand-600 text-brand-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Lens 標準
            </button>
          </div>
        )}

        {canEditLens && mainTab === 'lens' && token ? (
          <LensCriteriaEditor token={token} />
        ) : (
          <>
        <div className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm space-y-3">
          <div className="flex flex-wrap gap-3 items-end">
            <label className="flex flex-col gap-1 text-xs font-semibold text-gray-500">
              架構圖
              <select
                className="border border-gray-200 rounded-xl px-3 py-2 text-sm font-semibold text-gray-800 min-w-[12rem]"
                value={selectedDiagramId ?? ''}
                onChange={(e) => {
                  const id = e.target.value ? Number(e.target.value) : null;
                  if (optimizeDraft) {
                    cancelOptimizeDraft();
                  } else {
                    setCollabLog([]);
                    setCollabPreviewXml(null);
                    setCollabScore(null);
                    setCollabStatus(null);
                  }
                  setDiagramOverride(id);
                  setUploadedXml(null);
                  setUploadedFileName(null);
                  setSaveDiagram(false);
                  setSaveTitle('');
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
              >
                <option value="">— 選擇 —</option>
                {diagrams.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title}
                  </option>
                ))}
              </select>
            </label>
            {canDeleteSelectedDiagram && (
              <button
                type="button"
                onClick={() => void deleteSelectedDiagram()}
                disabled={deletingDiagram || reviewInProgress || collabRunning}
                className="px-3 py-2 rounded-xl text-sm font-bold text-red-700 bg-red-50 border border-red-100 disabled:opacity-40"
                title="刪除所選架構圖（含評核紀錄）"
              >
                {deletingDiagram ? '刪除中…' : '刪除架構圖'}
              </button>
            )}
            <label className="flex flex-col gap-1 text-xs font-semibold text-gray-500">
              上傳 .drawio / .xml
              <div className="flex items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".drawio,.xml,application/xml,text/xml"
                  className="block w-full max-w-[14rem] text-sm text-gray-700 file:mr-2 file:py-2 file:px-3 file:rounded-xl file:border-0 file:bg-gray-100 file:text-xs file:font-bold file:text-gray-700 hover:file:bg-gray-200"
                  onChange={(e) => {
                    void handleUploadFile(e.target.files?.[0] ?? null);
                  }}
                />
                {uploadedXml && (
                  <button
                    type="button"
                    onClick={clearUpload}
                    className="text-xs font-semibold text-gray-500 hover:text-red-600 whitespace-nowrap"
                  >
                    清除
                  </button>
                )}
              </div>
            </label>
            <label className="flex flex-col gap-1 text-xs font-semibold text-gray-500">
              Provider
              <select
                className="border border-gray-200 rounded-xl px-3 py-2 text-sm font-semibold text-gray-800"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              >
                <option value="aws">AWS</option>
                <option value="gcp">GCP</option>
                <option value="azure">Azure</option>
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700 pb-2">
              <input
                type="checkbox"
                checked={replaceLatest}
                onChange={(e) => setReplaceLatest(e.target.checked)}
              />
              隱藏先前完整評核（replace_latest）
            </label>
            <button
              type="button"
              disabled={!canRunReview || phase === 'running' || collabRunning}
              onClick={runReview}
              className="ml-auto px-4 py-2 rounded-xl bg-brand-600 text-white text-sm font-bold disabled:opacity-40"
            >
              {phase === 'running' ? '評核中…' : '執行評核'}
            </button>
            <button
              type="button"
              disabled={!canRunWaCollab}
              onClick={() => void runWaOptimize()}
              className="px-4 py-2 rounded-xl bg-indigo-50 text-indigo-800 text-sm font-bold border border-indigo-100 disabled:opacity-40"
              title={waCollabDisabledReason}
            >
              {collabRunning ? '優化中…' : '優化'}
            </button>
          </div>
          {(collabLog.length > 0 || (collabPreviewXml && !optimizeDraft)) && (
            <div className="border border-indigo-100 rounded-2xl bg-indigo-50/40 p-4 space-y-3">
              <div className="flex flex-wrap items-center gap-2 justify-between">
                <p className="text-sm font-bold text-indigo-900">
                  Design ↔ Review 協作
                  {collabScore != null && (
                    <span className="ml-2 font-semibold">
                      {Math.round(collabScore)} 分
                      {collabStatus === 'passed'
                        ? ' · 已達標'
                        : collabStatus === 'failed'
                          ? ' · 未達標'
                          : ''}
                    </span>
                  )}
                </p>
              </div>
              {collabLog.length > 0 && (
                <pre className="text-xs text-gray-700 whitespace-pre-wrap max-h-48 overflow-y-auto bg-white/80 rounded-xl p-3 border border-indigo-50">
                  {collabLog.join('\n\n')}
                </pre>
              )}
            </div>
          )}
          {uploadedFileName && (
            <p className="text-xs text-gray-500">
              已上傳：{uploadedFileName}
              {detectingProvider ? ' · 偵測雲端中…' : ` · 將以 ${provider.toUpperCase()} 評核`}
            </p>
          )}
          {uploadedXml && (
            <div className="flex flex-wrap gap-3 items-end border-t border-gray-50 pt-3">
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={saveDiagram}
                  onChange={(e) => setSaveDiagram(e.target.checked)}
                />
                評核時同時存成架構圖
              </label>
              {(saveDiagram || reviewNeedsPersist) && (
                <label className="flex flex-col gap-1 text-xs font-semibold text-gray-500">
                  架構圖標題
                  <input
                    type="text"
                    className="border border-gray-200 rounded-xl px-3 py-2 text-sm font-semibold text-gray-800 min-w-[12rem]"
                    value={saveTitle}
                    placeholder={uploadedFileName || '上傳的架構圖'}
                    onChange={(e) => setSaveTitle(e.target.value)}
                  />
                </label>
              )}
              {reviewNeedsPersist && (
                <button
                  type="button"
                  onClick={() => void persistUploadReview()}
                  disabled={savingPersist}
                  className="px-4 py-2 rounded-xl bg-emerald-600 text-white text-sm font-bold disabled:opacity-40"
                  title="將目前上傳的架構圖與評核結果一併存檔"
                >
                  {savingPersist ? '儲存中…' : '儲存架構圖與評核'}
                </button>
              )}
            </div>
          )}
          {!uploadedXml && reviewNeedsPersist && (
            <div className="flex flex-wrap gap-3 items-end border-t border-gray-50 pt-3">
              <label className="flex flex-col gap-1 text-xs font-semibold text-gray-500">
                架構圖標題
                <input
                  type="text"
                  className="border border-gray-200 rounded-xl px-3 py-2 text-sm font-semibold text-gray-800 min-w-[12rem]"
                  value={saveTitle}
                  placeholder="上傳的架構圖"
                  onChange={(e) => setSaveTitle(e.target.value)}
                />
              </label>
              <button
                type="button"
                onClick={() => void persistUploadReview()}
                disabled={savingPersist}
                className="px-4 py-2 rounded-xl bg-emerald-600 text-white text-sm font-bold disabled:opacity-40"
              >
                {savingPersist ? '儲存中…' : '儲存架構圖與評核'}
              </button>
            </div>
          )}
          {provider === 'azure' && (
            <p className="text-xs text-amber-800 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
              Azure 評核使用 WARA 對齊的 Reliability Lens（架構圖離線規則；非即時{' '}
              <a
                className="underline"
                href="https://github.com/Azure/Well-Architected-Reliability-Assessment"
                target="_blank"
                rel="noreferrer"
              >
                WARA Collector
              </a>
              ）
            </p>
          )}
          {provider === 'gcp' && (
            <p className="text-xs text-amber-800 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
              GCP 評核對齊{' '}
              <a
                className="underline"
                href="https://docs.cloud.google.com/architecture/framework"
                target="_blank"
                rel="noreferrer"
              >
                Google Cloud Well-Architected Framework
              </a>
              （架構圖離線規則；Sustainability 暫未納入第六支柱計分）
            </p>
          )}
          {!canEdit && (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
              您僅有檢視權限，可開啟歷史報告，無法發起新評核。
            </p>
          )}
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
          {!optimizeDraft && (
            <DiagramPreviewPanel
              xml={previewXml}
              title={previewTitle}
              heightClass="h-72"
              emptyHint="選擇架構圖或上傳 .drawio／.xml 後，將在此預覽圖面"
            />
          )}
          {optimizeDraft && (
            <div className="border border-amber-200 rounded-2xl bg-amber-50/50 p-4 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-bold text-amber-900">
                  新舊架構圖比對
                  <span className="ml-2 text-xs font-semibold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                    新圖
                  </span>
                </h3>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={savingOptimize}
                    onClick={() => void saveOptimizeDraft()}
                    className="px-4 py-2 rounded-xl bg-brand-600 text-white text-sm font-bold disabled:opacity-40"
                  >
                    {savingOptimize ? '儲存中…' : '儲存'}
                  </button>
                  <button
                    type="button"
                    disabled={savingOptimize}
                    onClick={cancelOptimizeDraft}
                    className="px-4 py-2 rounded-xl bg-white text-gray-700 text-sm font-bold border border-gray-200"
                  >
                    取消
                  </button>
                </div>
              </div>
              <p className="text-xs text-amber-800">
                儲存將覆蓋原架構圖（不更名）並寫入新評核報告；取消則捨棄本次優化結果。
              </p>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-bold text-gray-500 mb-2">舊架構圖</p>
                  <DiagramPreviewPanel
                    xml={optimizeDraft.baselineXml}
                    title="優化前"
                    heightClass="h-56"
                  />
                </div>
                <div>
                  <p className="text-xs font-bold text-indigo-700 mb-2">新架構圖（未儲存）</p>
                  <DiagramPreviewPanel
                    xml={optimizeDraft.newXml}
                    title="優化後"
                    heightClass="h-56"
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div className="bg-white/80 rounded-xl p-3 border border-gray-100">
                  <p className="font-bold text-gray-700 mb-1">舊報告</p>
                  <p>
                    分數{' '}
                    {optimizeDraft.baselineReview?.overall_score != null
                      ? Math.round(optimizeDraft.baselineReview.overall_score)
                      : '—'}
                  </p>
                  <p>
                    高風險{' '}
                    {(
                      optimizeDraft.baselineReview?.scores?.risk_counts?.HIGH_RISK ??
                      optimizeDraft.baselineReview?.scores?.lens?.risk_counts
                        ?.HIGH_RISK ??
                      (optimizeDraft.baselineReview?.findings || []).filter(
                        (f) => f.severity === 'high' || f.lens_risk === 'HIGH_RISK',
                      ).length
                    )}
                    {' '}
                    項
                  </p>
                </div>
                <div className="bg-white/80 rounded-xl p-3 border border-indigo-100">
                  <p className="font-bold text-indigo-800 mb-1">新報告（未儲存）</p>
                  <p>
                    分數 {Math.round(optimizeDraft.draftReview.overall_score)}
                  </p>
                  <p>高風險 {optimizeDraft.draftReview.high_risk_count} 項</p>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">
          <h2 className="text-sm font-bold text-gray-800 mb-3">
            {selectedDiagramId ? '歷史評核' : '未建檔評核'}{' '}
            {loadingList ? '（載入中）' : ''}
          </h2>
          {!selectedDiagramId && reviews.length === 0 && !loadingList && (
            <p className="text-sm text-gray-400">
              {uploadedXml
                ? '上傳檔案可直接評核；完成後可按「儲存架構圖與評核」建檔'
                : '請先選擇架構圖，或上傳 .drawio／.xml 後評核'}
            </p>
          )}
          {selectedDiagramId && reviews.length === 0 && !loadingList && (
            <p className="text-sm text-gray-400">尚無評核紀錄</p>
          )}
          <ul className="divide-y divide-gray-100">
            {reviews.map((r) => {
              const selected = active?.id === r.id;
              return (
                <li
                  key={r.id}
                  className={`py-3 flex items-center gap-3 ${
                    selected ? 'bg-brand-50/60 -mx-2 px-2 rounded-xl' : ''
                  }`}
                >
                  <button
                    type="button"
                    className="flex-1 min-w-0 text-left"
                    onClick={() => openReview(r)}
                    disabled={openingId === r.id}
                  >
                    <div className="text-sm font-semibold text-gray-900">
                      #{r.id} · {r.status} · 分數 {r.overall_score ?? '—'}
                      {r.suggestions_text ? ' · 有建議' : ''}
                      {r.diagram_id == null ? ' · 未建檔' : ''}
                    </div>
                    <div className="text-xs text-gray-400">
                      {r.created_at ? new Date(r.created_at).toLocaleString() : ''}
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => openReview(r)}
                    disabled={openingId === r.id}
                    className="text-xs font-bold text-brand-700 px-3 py-1.5 rounded-lg bg-brand-50 disabled:opacity-50"
                  >
                    {openingId === r.id ? '開啟中…' : selected ? '檢視中' : '開啟'}
                  </button>
                  {canEdit && (
                    <button
                      type="button"
                      onClick={() => void deleteReviewById(r.id)}
                      disabled={deletingReviewId === r.id}
                      className="text-xs font-bold text-red-700 px-3 py-1.5 rounded-lg bg-red-50 border border-red-100 disabled:opacity-50"
                    >
                      {deletingReviewId === r.id ? '刪除中…' : '刪除'}
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        </div>

        {active && (
          <div
            ref={resultRef}
            className="bg-white border border-brand-100 rounded-2xl p-5 shadow-sm space-y-4 scroll-mt-4"
          >
            {phase === 'draft' && (
              <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-2 text-sm text-amber-900">
                <span className="font-bold">新報告（未儲存）</span>
                — 請確認上方比對結果後按「儲存」或「取消」。
              </div>
            )}
            {(reviewNeedsPersist || canEdit) && (
              <div className="flex flex-wrap gap-2">
                {reviewNeedsPersist && (
                  <button
                    type="button"
                    onClick={() => void persistUploadReview()}
                    disabled={savingPersist}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-bold disabled:opacity-40"
                  >
                    {savingPersist ? '儲存中…' : '儲存架構圖與評核'}
                  </button>
                )}
                {canEdit && (
                  <button
                    type="button"
                    onClick={() => void deleteReviewById(active.id)}
                    disabled={deletingReviewId === active.id}
                    className="px-3 py-1.5 rounded-lg bg-red-50 text-red-700 text-xs font-bold border border-red-100 disabled:opacity-40"
                  >
                    {deletingReviewId === active.id ? '刪除中…' : '刪除此評核'}
                  </button>
                )}
              </div>
            )}
            <div className="flex flex-wrap items-baseline gap-3">
              <div className="text-3xl font-bold text-gray-900">
                {displayOverall ?? '—'}
              </div>
              <div className="text-sm text-gray-500">
                評核 #{active.id} · Lens 總分 · 狀態{' '}
                <span className="font-semibold text-gray-800">{active.status}</span>
                {lensReady && (
                  <span className="ml-2 text-xs font-semibold text-brand-700">
                    離線 Lens
                  </span>
                )}
                {lensPending && (
                  <span className="ml-2 text-xs font-semibold text-amber-700">
                    Lens 評分中…
                  </span>
                )}
                {lensFailed && (
                  <span className="ml-2 text-xs font-semibold text-red-700">
                    Lens 失敗（無分數可顯示）
                  </span>
                )}
                {!lensReady && !lensPending && !lensFailed && (
                  <span className="ml-2 text-xs font-semibold text-gray-500">
                    無 Lens 分數（舊版或未完成）
                  </span>
                )}
              </div>
              <div className="ml-auto flex flex-wrap gap-2">
                {canDownloadPdf && (
                  <button
                    type="button"
                    onClick={exportPdf}
                    disabled={exportingPdf}
                    className="text-sm font-bold text-brand-700 bg-brand-50 px-3 py-1.5 rounded-lg disabled:opacity-50"
                  >
                    {exportingPdf ? '產生 PDF…' : '下載 PDF'}
                  </button>
                )}
                {active.status === 'rules_only' && canEdit && (
                  <button
                    type="button"
                    onClick={retrySuggestions}
                    className="text-sm font-bold text-indigo-700 bg-indigo-50 px-3 py-1.5 rounded-lg"
                  >
                    重試建議
                  </button>
                )}
              </div>            </div>

            {riskCounts && (
              <div className="flex flex-wrap gap-2">
                {(
                  [
                    ['HIGH_RISK', '高風險', 'bg-red-100 text-red-800'],
                    ['MEDIUM_RISK', '中風險', 'bg-amber-100 text-amber-900'],
                    ['NO_RISK', '無風險', 'bg-emerald-100 text-emerald-800'],
                  ] as const
                ).map(([key, label, cls]) => (
                  <div
                    key={key}
                    className={`rounded-xl px-3 py-2 text-sm font-bold ${cls}`}
                  >
                    {label}{' '}
                    <span className="tabular-nums">
                      {riskCounts[key] ?? 0}
                    </span>
                  </div>
                ))}
                {active.scores?.lens?.lens_name && (
                  <div className="text-xs text-gray-500 self-center">
                    Lens：{active.scores.lens.lens_name}
                  </div>
                )}
              </div>
            )}

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {Object.keys(PILLAR_LABELS).map((key) => (
                <div
                  key={key}
                  className="border border-gray-100 rounded-xl px-3 py-2 bg-gray-50"
                >
                  <div className="text-[11px] font-semibold text-gray-500">
                    {PILLAR_LABELS[key]}
                  </div>
                  <div className="text-lg font-bold text-gray-900">
                    {pillarScores[key] != null ? Math.round(pillarScores[key]) : '—'}
                  </div>
                </div>
              ))}
            </div>

            <div>
              <h2 className="text-sm font-bold text-gray-800 mb-2">
                發現
                {active.scores?.findings_source === 'offline_lens' && (
                  <span className="ml-2 text-[11px] font-semibold text-brand-700">
                    Custom Lens
                  </span>
                )}
                {active.scores?.findings_source === 'heuristic' && (
                  <span className="ml-2 text-[11px] font-semibold text-amber-700">
                    啟發式備援
                  </span>
                )}
              </h2>
              <ul className="space-y-2 max-h-64 overflow-y-auto">
                {(active.findings || []).map((f) => (
                  <li
                    key={`${f.code}-${f.title}`}
                    className="border border-gray-100 rounded-xl px-3 py-2 text-sm"
                  >
                    <div className="flex gap-2 items-center flex-wrap">
                      <span className="text-[10px] font-bold uppercase tracking-wide text-white bg-gray-700 px-1.5 py-0.5 rounded">
                        {f.pillar}
                      </span>
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded ${
                          f.severity === 'high' || f.severity === 'critical'
                            ? 'bg-red-100 text-red-800'
                            : f.severity === 'warn'
                              ? 'bg-amber-100 text-amber-900'
                              : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {f.lens_risk || f.severity}
                      </span>
                      <span className="font-semibold text-gray-900">{f.title}</span>
                      <span className="text-xs text-gray-400 ml-auto">{f.code}</span>
                    </div>
                    <p className="text-gray-600 mt-1">{f.message}</p>
                    {f.recommendation_hint || (f as Finding & { hint?: string }).hint ? (
                      <p className="text-xs text-brand-700 mt-1">
                        提示：{f.recommendation_hint || (f as Finding & { hint?: string }).hint}
                      </p>
                    ) : null}
                  </li>
                ))}
                {(active.findings || []).length === 0 && (
                  <li className="text-sm text-gray-400">
                    {phase === 'running' || phase === 'rules' || phase === 'lens'
                      ? '（等待 Lens 評核結果…）'
                      : '尚無中／高風險發現'}
                  </li>
                )}
              </ul>
            </div>

            <div>
              <h2 className="text-sm font-bold text-gray-800 mb-2 flex items-center gap-2">
                {phase === 'draft' ? '優化改善建議' : '改善建議'}
                {phase === 'draft' && (
                  <span className="text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full">
                    比對摘要
                  </span>
                )}
                {isStreamingSuggestions && (
                  <span className="text-[11px] font-semibold text-brand-600 animate-pulse">
                    串流中…
                  </span>
                )}
              </h2>
              <div className="bg-white border border-gray-100 rounded-xl p-4 min-h-[6rem] shadow-sm">
                {suggestionsText ? (
                  <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                    {toPlainSuggestionText(suggestionsText)}
                    {isStreamingSuggestions ? (
                      <span className="inline-block w-1.5 h-4 ml-0.5 align-middle bg-brand-500 animate-pulse" />
                    ) : null}
                  </p>
                ) : (
                  <p className="text-sm text-gray-400">{suggestionsPlaceholder}</p>
                )}
              </div>
              {active.error_message && active.status === 'rules_only' && (
                <p className="text-xs text-red-600 mt-2">
                  Agent 錯誤：{active.error_message}
                  {canEdit ? ' — 可點「重試建議」再試。' : ''}
                </p>
              )}
            </div>
          </div>
        )}
          </>
        )}
      </div>
    </div>
  );
};
