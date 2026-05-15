import { apiFetch, clearTokens, handleApiError, storeTokens } from './client';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'parent' | 'child';
}

export async function login(email: string, password: string): Promise<User> {
  const res = await apiFetch('/api/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) await handleApiError(res);
  const data = await res.json() as { user: User; access: string; refresh: string };
  await storeTokens(data.access, data.refresh);
  return data.user;
}

export async function getMe(): Promise<User | null> {
  const res = await apiFetch('/api/auth/me/');
  if (!res.ok) return null;
  return res.json() as Promise<User>;
}

export async function logout(): Promise<void> {
  await apiFetch('/api/auth/logout/', { method: 'POST' }).catch(() => {});
  await clearTokens();
}
