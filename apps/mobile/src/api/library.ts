import type { ShelfType, BookBrief, ShelfEntry } from '@kids-reading-tracker/api-types';
import { SHELF_LABELS, SHELF_ORDER } from '@kids-reading-tracker/api-types';
import { apiFetch, handleApiError } from './client';

export type { ShelfType, BookBrief, ShelfEntry };
export { SHELF_LABELS, SHELF_ORDER };

export async function getShelf(shelf?: ShelfType): Promise<ShelfEntry[]> {
  const path = shelf
    ? `/api/library/shelf/?shelf=${shelf}`
    : '/api/library/shelf/';
  const res = await apiFetch(path);
  if (!res.ok) await handleApiError(res);
  return res.json() as Promise<ShelfEntry[]>;
}

export async function addBookByISBN(
  isbn: string,
  shelf: ShelfType,
): Promise<{ shelf_entry: ShelfEntry; imported: boolean }> {
  const res = await apiFetch('/api/library/shelf/by-isbn/', {
    method: 'POST',
    body: JSON.stringify({ isbn, shelf }),
  });
  if (!res.ok) await handleApiError(res);
  return res.json() as Promise<{ shelf_entry: ShelfEntry; imported: boolean }>;
}

export async function removeFromShelf(id: number): Promise<void> {
  await apiFetch(`/api/library/shelf/${id}/`, { method: 'DELETE' });
}

export async function moveToShelf(id: number, shelf: ShelfType): Promise<ShelfEntry> {
  const res = await apiFetch(`/api/library/shelf/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify({ shelf }),
  });
  if (!res.ok) await handleApiError(res);
  return res.json() as Promise<ShelfEntry>;
}
