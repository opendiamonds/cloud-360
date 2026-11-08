import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { IacWorkspace } from '../components/iac/IacWorkspace';
import { useAuth } from '../context/auth-context';
import { apiUrl } from '../config/api';
import type { DiagramOption, IacStep } from '../iac/iacTypes';

async function fetchDiagramOptions(token: string): Promise<DiagramOption[]> {
  const response = await fetch(apiUrl('/api/collab/diagrams'), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error(String(response.status));
  const data: unknown = await response.json();
  if (!Array.isArray(data)) return [];
  return data.flatMap((item) => {
    if (!item || typeof item !== 'object') return [];
    const row = item as { id?: unknown; title?: unknown };
    if (typeof row.id !== 'number') return [];
    const title = typeof row.title === 'string' && row.title.trim() ? row.title : '未命名架構圖';
    return [{ id: row.id, title }];
  });
}

export function IacPage({ step }: { step: IacStep }) {
  const navigate = useNavigate();
  const { token, canArch } = useAuth();
  const [diagrams, setDiagrams] = useState<DiagramOption[]>([]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchDiagramOptions(token)
      .then((rows) => {
        if (!cancelled) setDiagrams(rows);
      })
      .catch(() => {
        if (!cancelled) setDiagrams([]);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div className="relative min-h-0 flex-1">
      <IacWorkspace
        key={step}
        initialDiagramId={null}
        initialStep={step}
        diagrams={diagrams}
        onClose={() => navigate(canArch('view') ? '/workspace' : '/')}
        onDiagramCreated={(created) => {
          setDiagrams((prev) => [created, ...prev.filter((item) => item.id !== created.id)]);
        }}
      />
    </div>
  );
}
