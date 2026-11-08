import { apiUrl } from '../config/api';

export class DiagramUploadError extends Error {
  readonly reason: 'type' | 'empty' | 'http';
  readonly status: number | null;

  constructor(reason: 'type' | 'empty' | 'http', status: number | null = null) {
    super(reason);
    this.name = 'DiagramUploadError';
    this.reason = reason;
    this.status = status;
  }
}

export interface UploadedDiagram {
  id: number;
  title: string;
}

/** Creates a diagram from a `.drawio` / `.xml` file. Does not log file contents. */
export async function createDiagramFromFile(
  token: string,
  file: File,
): Promise<UploadedDiagram> {
  const lower = file.name.toLowerCase();
  if (!lower.endsWith('.drawio') && !lower.endsWith('.xml')) {
    throw new DiagramUploadError('type');
  }
  const xml = await file.text();
  if (!xml.trim()) throw new DiagramUploadError('empty');
  const title = file.name.replace(/\.(drawio|xml)$/i, '') || '匯入架構圖';
  const res = await fetch(apiUrl('/api/collab/diagrams'), {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ xml_data: xml, title }),
  });
  if (!res.ok) throw new DiagramUploadError('http', res.status);
  const data: unknown = await res.json();
  const id =
    data && typeof data === 'object' && 'id' in data ? Number((data as { id: unknown }).id) : NaN;
  if (!Number.isInteger(id) || id < 1) throw new DiagramUploadError('http', res.status);
  const returnedTitle =
    data && typeof data === 'object' && 'title' in data && typeof (data as { title: unknown }).title === 'string'
      ? (data as { title: string }).title
      : title;
  return { id, title: returnedTitle };
}
