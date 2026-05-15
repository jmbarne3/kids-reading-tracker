const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

export type ShelfType = 'currently_reading' | 'want_to_read' | 'read' | 'did_not_finish';

export const SHELF_LABELS: Record<ShelfType, string> = {
  currently_reading: 'Currently Reading',
  want_to_read: 'Want to Read',
  read: 'Read',
  did_not_finish: 'Did Not Finish',
};

export interface BookBrief {
  id: number;
  title: string;
  author_names: string[];
  isbn_13: string;
  cover_image_url: string;
  page_count: number | null;
}

export interface ShelfEntry {
  id: number;
  book: BookBrief;
  shelf: ShelfType;
  added_at: string;
  updated_at: string;
}

async function handleError(res: Response): Promise<never> {
  const body = await res.json().catch(() => ({})) as Record<string, unknown>;
  if (typeof body['detail'] === 'string') throw new Error(body['detail']);
  const nonField = body['non_field_errors'];
  if (Array.isArray(nonField) && nonField.length > 0) throw new Error(String(nonField[0]));
  const messages = Object.entries(body)
    .flatMap(([, v]) => (Array.isArray(v) ? v : [String(v)]))
    .join(' ');
  throw new Error(messages || 'Request failed.');
}

export async function addBookByISBN(
  isbn: string,
  shelf: ShelfType,
): Promise<{ shelf_entry: ShelfEntry; imported: boolean }> {
  const res = await fetch(`${API_BASE}/api/library/shelf/by-isbn/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ isbn, shelf }),
  });
  if (!res.ok) await handleError(res);
  return res.json() as Promise<{ shelf_entry: ShelfEntry; imported: boolean }>;
}

export async function getShelf(shelf?: ShelfType): Promise<ShelfEntry[]> {
  const url = shelf
    ? `${API_BASE}/api/library/shelf/?shelf=${shelf}`
    : `${API_BASE}/api/library/shelf/`;
  const res = await fetch(url, { credentials: 'include' });
  if (!res.ok) await handleError(res);
  return res.json() as Promise<ShelfEntry[]>;
}

export async function removeFromShelf(id: number): Promise<void> {
  await fetch(`${API_BASE}/api/library/shelf/${id}/`, {
    method: 'DELETE',
    credentials: 'include',
  });
}

export async function moveToShelf(id: number, shelf: ShelfType): Promise<ShelfEntry> {
  const res = await fetch(`${API_BASE}/api/library/shelf/${id}/`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ shelf }),
  });
  if (!res.ok) await handleError(res);
  return res.json() as Promise<ShelfEntry>;
}
