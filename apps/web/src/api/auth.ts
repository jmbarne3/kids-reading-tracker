const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'parent' | 'child';
  date_of_birth: string | null;
  avatar_url: string;
}

export interface RegisterData {
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  password: string;
  password2: string;
}

async function handleError(res: Response): Promise<never> {
  const body = await res.json().catch(() => ({})) as Record<string, unknown>;
  // DRF can return errors as { field: [msg], non_field_errors: [msg], detail: msg }
  const nonField = body['non_field_errors'];
  if (Array.isArray(nonField) && nonField.length > 0) {
    throw new Error(String(nonField[0]));
  }
  if (typeof body['detail'] === 'string') {
    throw new Error(body['detail']);
  }
  const messages = Object.entries(body)
    .flatMap(([, v]) => (Array.isArray(v) ? v : [v]))
    .join(' ');
  throw new Error(messages || 'Request failed.');
}

export async function login(email: string, password: string): Promise<User> {
  const res = await fetch(`${API_BASE}/api/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) await handleError(res);
  const data = await res.json() as { user: User };
  return data.user;
}

export async function register(payload: RegisterData): Promise<User> {
  const res = await fetch(`${API_BASE}/api/auth/register/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  });
  if (!res.ok) await handleError(res);
  const data = await res.json() as { user: User };
  return data.user;
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE}/api/auth/logout/`, {
    method: 'POST',
    credentials: 'include',
  });
}

export async function getMe(): Promise<User | null> {
  const res = await fetch(`${API_BASE}/api/auth/me/`, {
    credentials: 'include',
  });
  if (!res.ok) return null;
  return res.json() as Promise<User>;
}
