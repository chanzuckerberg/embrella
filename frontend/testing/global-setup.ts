import { execFileSync } from 'child_process';
import { mkdirSync, writeFileSync } from 'fs';
import { dirname, resolve } from 'path';

// Devcontainer auth bootstrap: gets-or-creates a Playwright test user in
// Django and seeds a session cookie. Tests pick up the resulting storageState
// via `use.storageState` in playwright.config.ts, so they hit authenticated
// routes without going through the Google SSO login form.

export const STORAGE_STATE_PATH = resolve(__dirname, '.auth/storageState.json');

const PYTHON_BOOTSTRAP = `
from django.contrib.auth import get_user_model, HASH_SESSION_KEY, BACKEND_SESSION_KEY, SESSION_KEY
from django.contrib.sessions.backends.db import SessionStore
User = get_user_model()
user, _ = User.objects.get_or_create(
    username='playwright-test',
    defaults={'is_active': True},
)
if not user.is_active:
    user.is_active = True
    user.save(update_fields=['is_active'])
session = SessionStore()
session[SESSION_KEY] = str(user.pk)
session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
session[HASH_SESSION_KEY] = user.get_session_auth_hash()
session.create()
print(session.session_key)
`.trim();

export default async function globalSetup(): Promise<void> {
  if (process.env.DEVCONTAINER !== 'true') return;

  const stdout = execFileSync(
    'python',
    ['umbrella/manage.py', 'shell', '-c', PYTHON_BOOTSTRAP],
    { cwd: '/app', encoding: 'utf-8' },
  );
  const sessionKey = stdout.trim().split('\n').pop();
  if (!sessionKey) throw new Error('global-setup: Django shell returned no session key');

  const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://nginx/';
  const { hostname } = new URL(baseURL);

  mkdirSync(dirname(STORAGE_STATE_PATH), { recursive: true });
  writeFileSync(
    STORAGE_STATE_PATH,
    JSON.stringify({
      cookies: [
        {
          name: 'sessionid',
          value: sessionKey,
          domain: hostname,
          path: '/',
          expires: -1,
          httpOnly: true,
          secure: false,
          sameSite: 'Lax',
        },
      ],
      origins: [],
    }),
  );
}
