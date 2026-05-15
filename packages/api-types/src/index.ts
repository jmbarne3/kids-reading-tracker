/**
 * @kids-reading-tracker/api-types
 *
 * Friendly re-exports of the auto-generated OpenAPI schema types.
 * Import from this file, not from ./generated directly.
 *
 * Regenerate with: npm run generate:types (from the repo root)
 */

export type { components, operations, paths } from './generated';
import type { components } from './generated';

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

/**
 * Authenticated user. All fields are always present in API responses even
 * though the underlying Django model marks some as optional.
 */
export type User = {
  readonly id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  date_of_birth: string | null;
  avatar_url: string;
};

/** @enum {string} */
export type UserRole = components['schemas']['RoleEnum'];

export type ChildProfile = components['schemas']['ChildProfile'];
export type CreateChildAccount = components['schemas']['CreateChildAccount'];
export type AuthTokenResponse = components['schemas']['AuthTokenResponse'];
export type TokenRefreshResponse = components['schemas']['TokenRefreshResponse'];

/** Registration request payload (includes password + confirm). */
export type RegisterPayload = components['schemas']['Register'];

// ---------------------------------------------------------------------------
// Library / shelf
// ---------------------------------------------------------------------------

/** @enum {string} */
export type ShelfType = components['schemas']['ShelfEnum'];

export type BookBrief = components['schemas']['BookBrief'];
export type ShelfEntry = components['schemas']['ShelfEntry'];
export type ReadingSession = components['schemas']['ReadingSession'];
export type ReadingProgress = components['schemas']['ReadingProgress'];
export type AddByISBNResponse = components['schemas']['AddByISBNResponse'];

/** Human-readable labels for each shelf. */
export const SHELF_LABELS: Record<ShelfType, string> = {
  currently_reading: 'Currently Reading',
  want_to_read: 'Want to Read',
  read: 'Read',
  did_not_finish: 'Did Not Finish',
};

/** Canonical display order for shelf tabs. */
export const SHELF_ORDER: ShelfType[] = [
  'currently_reading',
  'want_to_read',
  'read',
  'did_not_finish',
];
