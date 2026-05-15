import AsyncStorage from '@react-native-async-storage/async-storage';

/**
 * Base URL of the Django API.
 * Configured via the EXPO_PUBLIC_API_URL environment variable.
 * - iOS Simulator:      EXPO_PUBLIC_API_URL=http://localhost:8000
 * - Android Emulator:   EXPO_PUBLIC_API_URL=http://10.0.2.2:8000
 * - Physical device:    EXPO_PUBLIC_API_URL=http://192.168.x.x:8000
 * Set the variable in .env (local dev) or as a build secret in CI.
 */
export const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

const TOKEN_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';

// In-memory cache so we don't hit AsyncStorage on every request.
let _accessToken: string | null = null;

/** Called once on app launch to hydrate the in-memory token from storage. */
export async function loadStoredTokens(): Promise<void> {
  _accessToken = await AsyncStorage.getItem(TOKEN_KEY);
}

/** Persist a fresh token pair after login or token refresh. */
export async function storeTokens(access: string, refresh: string): Promise<void> {
  _accessToken = access;
  await AsyncStorage.multiSet([
    [TOKEN_KEY, access],
    [REFRESH_KEY, refresh],
  ]);
}

/** Clear tokens on logout. */
export async function clearTokens(): Promise<void> {
  _accessToken = null;
  await AsyncStorage.multiRemove([TOKEN_KEY, REFRESH_KEY]);
}

/** Authenticated fetch — injects Bearer token when available. */
export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined ?? {}),
  };
  if (_accessToken) {
    headers['Authorization'] = `Bearer ${_accessToken}`;
  }
  return fetch(`${API_BASE}${path}`, { ...options, headers });
}

/** Parse a DRF error response and throw a human-readable Error. */
export async function handleApiError(res: Response): Promise<never> {
  const body = await res.json().catch(() => ({})) as Record<string, unknown>;
  if (typeof body['detail'] === 'string') throw new Error(body['detail']);
  const nonField = body['non_field_errors'];
  if (Array.isArray(nonField) && nonField.length > 0) throw new Error(String(nonField[0]));
  const messages = Object.entries(body)
    .flatMap(([, v]) => (Array.isArray(v) ? v : [String(v)]))
    .join(' ');
  throw new Error(messages || 'Request failed.');
}
