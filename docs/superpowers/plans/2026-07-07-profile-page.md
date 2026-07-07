# Profile Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give users a dedicated `/profile` page to change their username, email, and password, replacing the inline username editor currently buried in the dashboard's hamburger dropdown.

**Architecture:** Two new backend endpoints (`PATCH /api/auth/me/email`, `PATCH /api/auth/me/password`) alongside the existing `PATCH /api/auth/me` (username), each requiring `current_password` re-entry. A new `ProfileView.vue` at `/profile` with three independent form sections (Username/Email/Password), each with its own error/success state, matching this codebase's existing per-concern-error-state convention. The dashboard's inline username editor is removed and replaced with a "Profile" link.

**Tech Stack:** FastAPI + SQLAlchemy (async) + Pydantic (backend), Vue 3 `<script setup>` + Pinia + Vue Router (frontend), pytest + httpx (backend tests), Vitest + @vue/test-utils (frontend tests).

## Global Constraints

- New password minimum length: 12 characters (matches `UserCreate`'s existing validator).
- New password maximum length: 128 characters, enforced manually at the endpoint (matches how `register` enforces it — not a schema field constraint).
- Username pattern: `^[a-zA-Z0-9_-]+$`, 1-50 chars (existing `UserUpdate` schema, unchanged).
- Both new endpoints require `current_password` and return 401 with detail `"Incorrect password"` if it doesn't match.
- Rate limit both new endpoints at `10/minute` (matches existing `PATCH /api/auth/me`).
- No email verification/confirmation flow — this repo has no email-sending infrastructure. Email change is immediate, same as registration today.
- Password change must revoke the caller's current JWT `jti` via the existing `token_blocklist` service, then issue a fresh `access_token` cookie (same flags as `/login`) so the current tab keeps working.

---

### Task 1: Backend — `PATCH /api/auth/me/email`

**Files:**
- Modify: `backend/src/app/schemas.py` (add `EmailChange` after `UserUpdate`, around line 88)
- Modify: `backend/src/app/routers/auth.py` (add import + endpoint after `update_me`, around line 202)
- Test: `backend/tests/test_auth.py` (add tests after `test_update_me_unauthenticated_gets_401`, around line 510)

**Interfaces:**
- Consumes: `verify_password_async(plain: str, hashed: str) -> bool` and `hash_password_async` from `app.services.auth` (already imported in `auth.py`); `User` model (`email`, `password_hash`, `id` fields); `get_current_user` dependency.
- Produces: `PATCH /api/auth/me/email` endpoint, request body `{current_password: str, new_email: str}`, response `UserOut` (200), 401/409/422 on failure. Later tasks do not depend on this endpoint's internals, only its HTTP contract.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_auth.py`, after the `# --- get_current_user security edge cases ---` section (end of file, after `test_deleted_user_with_valid_token_gets_401`):

```python
# --- PATCH /me/email endpoint ---

async def test_update_email_success(client):
    await client.post("/api/auth/register", json={"email": "old@b.com", "password": "pass12345678"})
    await client.post("/api/auth/login", data={"username": "old@b.com", "password": "pass12345678"})
    resp = await client.patch(
        "/api/auth/me/email",
        json={"current_password": "pass12345678", "new_email": "new@b.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "new@b.com"


async def test_update_email_wrong_password_gets_401(client):
    await client.post("/api/auth/register", json={"email": "wrongpw@b.com", "password": "pass12345678"})
    await client.post("/api/auth/login", data={"username": "wrongpw@b.com", "password": "pass12345678"})
    resp = await client.patch(
        "/api/auth/me/email",
        json={"current_password": "notmypassword", "new_email": "new2@b.com"},
    )
    assert resp.status_code == 401


async def test_update_email_conflict_gets_409(client):
    await client.post("/api/auth/register", json={"email": "taken@b.com", "password": "pass12345678"})
    await client.post("/api/auth/register", json={"email": "wantstaken@b.com", "password": "pass12345678"})
    await client.post("/api/auth/login", data={"username": "wantstaken@b.com", "password": "pass12345678"})
    resp = await client.patch(
        "/api/auth/me/email",
        json={"current_password": "pass12345678", "new_email": "taken@b.com"},
    )
    assert resp.status_code == 409


async def test_update_email_malformed_gets_422(client):
    await client.post("/api/auth/register", json={"email": "malformed@b.com", "password": "pass12345678"})
    await client.post("/api/auth/login", data={"username": "malformed@b.com", "password": "pass12345678"})
    resp = await client.patch(
        "/api/auth/me/email",
        json={"current_password": "pass12345678", "new_email": "not-an-email"},
    )
    assert resp.status_code == 422


async def test_update_email_unauthenticated_gets_401(client):
    resp = await client.patch(
        "/api/auth/me/email",
        json={"current_password": "whatever12345", "new_email": "anon@b.com"},
    )
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run python -m pytest tests/test_auth.py -k update_email -v`
Expected: FAIL — `404 Not Found` for all 5 (the endpoint doesn't exist yet).

- [ ] **Step 3: Add the `EmailChange` schema**

In `backend/src/app/schemas.py`, immediately after the `UserUpdate` class (after line 87, before `class AdminUserOut`):

```python
class EmailChange(BaseModel):
    current_password: str
    new_email: EmailStr
```

- [ ] **Step 4: Add the endpoint**

In `backend/src/app/routers/auth.py`, change the schemas import line (line 14) from:

```python
from app.schemas import UserCreate, UserOut, UserUpdate, Token
```

to:

```python
from app.schemas import UserCreate, UserOut, UserUpdate, EmailChange, PasswordChange, Token
```

(`PasswordChange` is added now so Task 2 doesn't need to touch this import line again.)

Then add this endpoint immediately after `update_me` (after line 202, before `@router.post("/users", ...)`):

```python
@router.patch("/me/email", response_model=UserOut)
@limiter.limit("10/minute")
async def update_email(
    request: Request,
    data: EmailChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await verify_password_async(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")
    result = await db.execute(
        select(User).where(User.email == data.new_email, User.id != current_user.id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    current_user.email = data.new_email
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    await db.refresh(current_user)
    return current_user
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run python -m pytest tests/test_auth.py -k update_email -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Run the full backend test suite to check for regressions**

Run: `cd backend && uv run python -m pytest -v`
Expected: all tests pass (no regressions from the schema/import changes)

- [ ] **Step 7: Commit**

```bash
git add backend/src/app/schemas.py backend/src/app/routers/auth.py backend/tests/test_auth.py
git commit -m "feat(backend): add PATCH /api/auth/me/email endpoint"
```

---

### Task 2: Backend — `PATCH /api/auth/me/password`

**Files:**
- Modify: `backend/src/app/schemas.py` (add `PasswordChange` after `EmailChange`)
- Modify: `backend/src/app/routers/auth.py` (add endpoint after `update_email`)
- Test: `backend/tests/test_auth.py` (add tests after the email tests from Task 1)

**Interfaces:**
- Consumes: `EmailChange` schema pattern from Task 1 (same file region); `create_access_token`, `decode_token`, `hash_password_async`, `verify_password_async` from `app.services.auth`; `TokenBlocklist`, `get_token_blocklist` from `app.services.token_blocklist` (already imported in `auth.py`); the `blocklist` pytest fixture from `test_auth.py` (already defined, around line 244).
- Produces: `PATCH /api/auth/me/password` endpoint, request body `{current_password: str, new_password: str}`, response `{token_type: "bearer"}` (200) with a new `access_token` cookie set, 401/422 on failure. No later task depends on this endpoint's internals.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_auth.py`, after the email tests added in Task 1:

```python
# --- PATCH /me/password endpoint ---

async def test_update_password_success_and_old_password_stops_working(client):
    await client.post("/api/auth/register", json={"email": "pwchange@b.com", "password": "oldpassword123"})
    await client.post("/api/auth/login", data={"username": "pwchange@b.com", "password": "oldpassword123"})
    resp = await client.patch(
        "/api/auth/me/password",
        json={"current_password": "oldpassword123", "new_password": "newpassword456"},
    )
    assert resp.status_code == 200
    assert "token_type" in resp.json()

    await client.post("/api/auth/logout")
    old_login = await client.post(
        "/api/auth/login", data={"username": "pwchange@b.com", "password": "oldpassword123"}
    )
    assert old_login.status_code == 401
    new_login = await client.post(
        "/api/auth/login", data={"username": "pwchange@b.com", "password": "newpassword456"}
    )
    assert new_login.status_code == 200


async def test_update_password_wrong_current_password_gets_401(client):
    await client.post("/api/auth/register", json={"email": "wrongcur@b.com", "password": "correctpass123"})
    await client.post("/api/auth/login", data={"username": "wrongcur@b.com", "password": "correctpass123"})
    resp = await client.patch(
        "/api/auth/me/password",
        json={"current_password": "notcorrect123", "new_password": "brandnewpass1"},
    )
    assert resp.status_code == 401


async def test_update_password_too_short_gets_422(client):
    await client.post("/api/auth/register", json={"email": "shortnew@b.com", "password": "correctpass123"})
    await client.post("/api/auth/login", data={"username": "shortnew@b.com", "password": "correctpass123"})
    resp = await client.patch(
        "/api/auth/me/password",
        json={"current_password": "correctpass123", "new_password": "short"},
    )
    assert resp.status_code == 422


async def test_update_password_too_long_gets_422(client):
    await client.post("/api/auth/register", json={"email": "toolongnew@b.com", "password": "correctpass123"})
    await client.post("/api/auth/login", data={"username": "toolongnew@b.com", "password": "correctpass123"})
    resp = await client.patch(
        "/api/auth/me/password",
        json={"current_password": "correctpass123", "new_password": "a" * 129},
    )
    assert resp.status_code == 422


async def test_update_password_revokes_old_token(client, blocklist):
    from app.services.auth import decode_token

    await client.post("/api/auth/register", json={"email": "revokepw@b.com", "password": "oldpassword123"})
    await client.post("/api/auth/login", data={"username": "revokepw@b.com", "password": "oldpassword123"})

    old_raw_token = client.cookies.get("access_token")
    assert old_raw_token
    old_jti = decode_token(old_raw_token)["jti"]

    resp = await client.patch(
        "/api/auth/me/password",
        json={"current_password": "oldpassword123", "new_password": "newpassword456"},
    )
    assert resp.status_code == 200
    assert await blocklist.is_revoked(old_jti) is True

    # The new cookie set by the response keeps the session alive.
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "revokepw@b.com"


async def test_update_password_unauthenticated_gets_401(client):
    resp = await client.patch(
        "/api/auth/me/password",
        json={"current_password": "whatever12345", "new_password": "newpassword456"},
    )
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run python -m pytest tests/test_auth.py -k update_password -v`
Expected: FAIL — `404 Not Found` for all 6 (the endpoint doesn't exist yet).

- [ ] **Step 3: Add the `PasswordChange` schema**

In `backend/src/app/schemas.py`, immediately after the `EmailChange` class added in Task 1:

```python
class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        return v
```

- [ ] **Step 4: Add the endpoint**

In `backend/src/app/routers/auth.py`, add this endpoint immediately after `update_email` (added in Task 1):

```python
@router.patch("/me/password")
@limiter.limit("10/minute")
async def update_password(
    request: Request,
    response: Response,
    data: PasswordChange,
    token: str | None = Depends(oauth2_scheme),
    cookie_token: str | None = Cookie(default=None, alias="access_token"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    blocklist: TokenBlocklist = Depends(get_token_blocklist),
):
    if len(data.new_password) > 128:
        raise HTTPException(status_code=422, detail="Password too long")
    if not await verify_password_async(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")
    current_user.password_hash = await hash_password_async(data.new_password)
    await db.commit()
    # Revoke the current token so any other copy of it (other tabs, a stolen
    # cookie) is rejected immediately after a password change.
    actual_token = cookie_token or token
    if actual_token:
        try:
            payload = decode_token(actual_token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                ttl = int(exp - datetime.now(timezone.utc).timestamp())
                await blocklist.revoke(jti, ttl)
        except (JWTError, TypeError, ValueError):
            pass
    new_token = create_access_token({"sub": str(current_user.id)})
    response.set_cookie(
        key="access_token",
        value=new_token,
        httponly=True,
        samesite="strict",
        secure=_COOKIE_SECURE,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"token_type": "bearer"}
```

This reuses `datetime`, `timezone`, `JWTError`, `TokenBlocklist`, `get_token_blocklist`, `create_access_token`, `decode_token`, `_COOKIE_SECURE`, `ACCESS_TOKEN_EXPIRE_MINUTES` — all already imported/defined in `auth.py` (see `logout` and `login` for the identical patterns this borrows from). No new imports needed beyond the `EmailChange, PasswordChange` added to the schemas import line in Task 1.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run python -m pytest tests/test_auth.py -k update_password -v`
Expected: PASS (6 passed)

- [ ] **Step 6: Run the full backend test suite to check for regressions**

Run: `cd backend && uv run python -m pytest -v`
Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/src/app/schemas.py backend/src/app/routers/auth.py backend/tests/test_auth.py
git commit -m "feat(backend): add PATCH /api/auth/me/password endpoint with token rotation"
```

---

### Task 3: Frontend — API client and auth store methods

**Files:**
- Modify: `frontend/src/api/auth.ts` (add `updateEmail`, `updatePassword` to `authApi`)
- Modify: `frontend/src/stores/auth.ts` (add `updateEmail`, `updatePassword` actions)
- Test: `frontend/src/stores/__tests__/auth.spec.ts` (add store tests)

**Interfaces:**
- Consumes: `PATCH /api/auth/me/email` and `PATCH /api/auth/me/password` HTTP contracts from Tasks 1-2; `apiClient` from `./client` (already used by every other `authApi` method); `UserOut`, `Token` interfaces (already defined in `auth.ts`).
- Produces: `authApi.updateEmail(currentPassword: string, newEmail: string): Promise<UserOut>`, `authApi.updatePassword(currentPassword: string, newPassword: string): Promise<Token>`, `useAuthStore().updateEmail(currentPassword: string, newEmail: string): Promise<void>`, `useAuthStore().updatePassword(currentPassword: string, newPassword: string): Promise<void>`. Task 5 (ProfileView) calls these exact store method names and signatures.

- [ ] **Step 1: Write the failing store tests**

In `frontend/src/stores/__tests__/auth.spec.ts`, change the mock (lines 6-15) from:

```typescript
vi.mock('../../api/auth', () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
    register: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
    updateUsername: vi.fn(),
    addUser: vi.fn(),
  },
}))
```

to:

```typescript
vi.mock('../../api/auth', () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
    register: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
    updateUsername: vi.fn(),
    updateEmail: vi.fn(),
    updatePassword: vi.fn(),
    addUser: vi.fn(),
  },
}))
```

Then add these two tests at the end of the `describe('auth store', ...)` block, right before its closing `})` (after the `restore clears user without calling logout when me() fails` test):

```typescript
  it('updateEmail calls authApi and updates user', async () => {
    vi.mocked(authApiModule.authApi.updateEmail).mockResolvedValue({ email: 'new@b.com', created_at: '', is_admin: false, username: null })
    const store = useAuthStore()
    await store.updateEmail('currentpass123', 'new@b.com')
    expect(store.user?.email).toBe('new@b.com')
  })

  it('updatePassword calls authApi without mutating user', async () => {
    vi.mocked(authApiModule.authApi.updatePassword).mockResolvedValue({ token_type: 'bearer' })
    const store = useAuthStore()
    store.$patch({ user: { email: 'a@b.com', created_at: '', is_admin: false, username: null } })
    await store.updatePassword('oldpass123456', 'newpass123456')
    expect(authApiModule.authApi.updatePassword).toHaveBeenCalledWith('oldpass123456', 'newpass123456')
    expect(store.user?.email).toBe('a@b.com')
  })
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && bun run test:unit --run src/stores/__tests__/auth.spec.ts`
Expected: FAIL — `store.updateEmail is not a function` / `store.updatePassword is not a function`

- [ ] **Step 3: Add the API client methods**

In `frontend/src/api/auth.ts`, add these two methods to the `authApi` object, right after `updateUsername`:

```typescript
  async updateEmail(currentPassword: string, newEmail: string): Promise<UserOut> {
    const { data } = await apiClient.patch<UserOut>('/api/auth/me/email', {
      current_password: currentPassword,
      new_email: newEmail,
    })
    return data
  },
  async updatePassword(currentPassword: string, newPassword: string): Promise<Token> {
    const { data } = await apiClient.patch<Token>('/api/auth/me/password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
    return data
  },
```

- [ ] **Step 4: Add the store actions**

In `frontend/src/stores/auth.ts`, add these two functions right after `updateUsername`:

```typescript
  async function updateEmail(currentPassword: string, newEmail: string) {
    user.value = await authApi.updateEmail(currentPassword, newEmail)
  }

  async function updatePassword(currentPassword: string, newPassword: string) {
    await authApi.updatePassword(currentPassword, newPassword)
  }
```

Then update the `return` statement at the bottom of `useAuthStore` from:

```typescript
  return { user, isAuthenticated, login, logout, restore, updateUsername }
```

to:

```typescript
  return { user, isAuthenticated, login, logout, restore, updateUsername, updateEmail, updatePassword }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && bun run test:unit --run src/stores/__tests__/auth.spec.ts`
Expected: PASS (7 passed)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/auth.ts frontend/src/stores/auth.ts frontend/src/stores/__tests__/auth.spec.ts
git commit -m "feat(frontend): add updateEmail/updatePassword to auth API client and store"
```

---

### Task 4: Frontend — `/profile` route

**Files:**
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- Consumes: nothing new (uses the existing `component: () => import(...)` lazy-route pattern).
- Produces: route named `profile` at path `/profile`, `meta: { requiresAuth: true }`. Task 5 creates the `ProfileView.vue` this route imports; Task 6's "Profile" link in `DashboardView.vue` navigates to this path.

- [ ] **Step 1: Add the route**

In `frontend/src/router/index.ts`, add this route object to the `routes` array, right after the `/dashboard` route (after line 14, before the `/admin` route):

```typescript
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../views/ProfileView.vue'),
      meta: { requiresAuth: true },
    },
```

- [ ] **Step 2: Verify the app still type-checks**

Run: `cd frontend && bun run type-check`
Expected: FAIL with an error that `../views/ProfileView.vue` does not exist yet — this is expected until Task 5. If your toolchain runs type-check as a blocking pre-commit hook, skip strict verification here and continue to Task 5 immediately; otherwise note the expected failure and proceed.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/router/index.ts
git commit -m "feat(frontend): add /profile route"
```

---

### Task 5: Frontend — `ProfileView.vue`

**Files:**
- Create: `frontend/src/views/ProfileView.vue`
- Test: `frontend/src/views/__tests__/ProfileView.spec.ts`

**Interfaces:**
- Consumes: `useAuthStore()` with `user`, `updateUsername(username: string)`, `updateEmail(currentPassword: string, newEmail: string)`, `updatePassword(currentPassword: string, newPassword: string)` from Task 3; `useThemeStore()` with `isDark`, `toggle()` (existing, used identically in `AdminView.vue` and `DashboardView.vue`); the `/profile` route from Task 4 registers this component.
- Produces: a mounted `ProfileView.vue` with a hamburger menu containing a "← Dashboard" link, and three form sections (`#profile-username`, `#profile-email-password` + `#profile-new-email`, `#profile-current-password` + `#profile-new-password` + `#profile-confirm-password`). No later task in this plan depends on this component's internals.

- [ ] **Step 1: Write the failing component test**

Create `frontend/src/views/__tests__/ProfileView.spec.ts`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import ProfileView from '../ProfileView.vue'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/dashboard', component: { template: '<div />' } },
  ],
})

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

vi.mock('../../api/auth', () => ({
  authApi: {
    updateUsername: vi.fn(),
    updateEmail: vi.fn(),
    updatePassword: vi.fn(),
  },
}))

import * as authApiModule from '../../api/auth'

function setupStore() {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  const store = useAuthStore()
  store.$patch({ user: { email: 'user@example.com', username: 'testuser', is_admin: false, created_at: '' } })
  return store
}

const globalOptions = { plugins: [router] }

describe('ProfileView username section', () => {
  it('shows success message on successful save', async () => {
    setupStore()
    vi.mocked(authApiModule.authApi.updateUsername).mockResolvedValue({
      email: 'user@example.com', username: 'newname', is_admin: false, created_at: '',
    })
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-username').setValue('newname')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Username updated.')
  })

  it('shows conflict error on 409', async () => {
    setupStore()
    vi.mocked(authApiModule.authApi.updateUsername).mockRejectedValue({ response: { status: 409 } })
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-username').setValue('taken')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Username already taken.')
  })
})

describe('ProfileView email section', () => {
  it('shows success message and clears inputs on successful save', async () => {
    setupStore()
    vi.mocked(authApiModule.authApi.updateEmail).mockResolvedValue({
      email: 'new@example.com', username: 'testuser', is_admin: false, created_at: '',
    })
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-email-password').setValue('currentpass123')
    await wrapper.find('#profile-new-email').setValue('new@example.com')
    const forms = wrapper.findAll('form')
    await forms[1]!.trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Email updated.')
    expect((wrapper.find('#profile-new-email').element as HTMLInputElement).value).toBe('')
  })

  it('shows incorrect-password error on 401', async () => {
    setupStore()
    vi.mocked(authApiModule.authApi.updateEmail).mockRejectedValue({ response: { status: 401 } })
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-email-password').setValue('wrongpass123')
    await wrapper.find('#profile-new-email').setValue('new@example.com')
    const forms = wrapper.findAll('form')
    await forms[1]!.trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Incorrect password.')
  })

  it('shows conflict error on 409', async () => {
    setupStore()
    vi.mocked(authApiModule.authApi.updateEmail).mockRejectedValue({ response: { status: 409 } })
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-email-password').setValue('currentpass123')
    await wrapper.find('#profile-new-email').setValue('taken@example.com')
    const forms = wrapper.findAll('form')
    await forms[1]!.trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Email already registered.')
  })
})

describe('ProfileView password section', () => {
  it('shows client-side error when passwords do not match, without calling the API', async () => {
    setupStore()
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-current-password').setValue('currentpass123')
    await wrapper.find('#profile-new-password').setValue('newpassword456')
    await wrapper.find('#profile-confirm-password').setValue('different789012')
    const forms = wrapper.findAll('form')
    await forms[2]!.trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('New passwords do not match.')
    expect(authApiModule.authApi.updatePassword).not.toHaveBeenCalled()
  })

  it('shows success message and clears inputs on successful save', async () => {
    setupStore()
    vi.mocked(authApiModule.authApi.updatePassword).mockResolvedValue({ token_type: 'bearer' })
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-current-password').setValue('currentpass123')
    await wrapper.find('#profile-new-password').setValue('newpassword456')
    await wrapper.find('#profile-confirm-password').setValue('newpassword456')
    const forms = wrapper.findAll('form')
    await forms[2]!.trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Password updated.')
    expect((wrapper.find('#profile-current-password').element as HTMLInputElement).value).toBe('')
  })

  it('shows incorrect-password error on 401', async () => {
    setupStore()
    vi.mocked(authApiModule.authApi.updatePassword).mockRejectedValue({ response: { status: 401 } })
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('#profile-current-password').setValue('wrongpass123')
    await wrapper.find('#profile-new-password').setValue('newpassword456')
    await wrapper.find('#profile-confirm-password').setValue('newpassword456')
    const forms = wrapper.findAll('form')
    await forms[2]!.trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Incorrect current password.')
  })
})

describe('ProfileView navigation', () => {
  it('has a back-to-dashboard link in the hamburger menu', async () => {
    setupStore()
    const wrapper = mount(ProfileView, { global: globalOptions })
    await wrapper.find('.hamburger-btn').trigger('click')
    const link = wrapper.find('.dropdown-item')
    expect(link.text()).toContain('Dashboard')
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && bun run test:unit --run src/views/__tests__/ProfileView.spec.ts`
Expected: FAIL — `Failed to resolve import "../ProfileView.vue"`

- [ ] **Step 3: Create `ProfileView.vue`**

Create `frontend/src/views/ProfileView.vue`:

```vue
<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'

const authStore = useAuthStore()
const themeStore = useThemeStore()

const showMenu = ref(false)
const menuRef = ref<HTMLDivElement | null>(null)

function handleOutsideClick(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
    showMenu.value = false
  }
}

onMounted(() => document.addEventListener('click', handleOutsideClick))
onBeforeUnmount(() => document.removeEventListener('click', handleOutsideClick))

function extractStatus(e: unknown): number | undefined {
  return (e as { response?: { status?: number } }).response?.status
}

// Username section
const usernameInput = ref(authStore.user?.username ?? '')
const usernameError = ref('')
const usernameSuccess = ref('')
const usernameLoading = ref(false)

async function saveUsername() {
  usernameError.value = ''
  usernameSuccess.value = ''
  usernameLoading.value = true
  try {
    await authStore.updateUsername(usernameInput.value)
    usernameSuccess.value = 'Username updated.'
  } catch (e: unknown) {
    usernameError.value = extractStatus(e) === 409 ? 'Username already taken.' : 'Failed to update username.'
  } finally {
    usernameLoading.value = false
  }
}

// Email section
const emailPassword = ref('')
const newEmail = ref('')
const emailError = ref('')
const emailSuccess = ref('')
const emailLoading = ref(false)

async function saveEmail() {
  emailError.value = ''
  emailSuccess.value = ''
  emailLoading.value = true
  try {
    await authStore.updateEmail(emailPassword.value, newEmail.value)
    emailSuccess.value = 'Email updated.'
    emailPassword.value = ''
    newEmail.value = ''
  } catch (e: unknown) {
    const status = extractStatus(e)
    if (status === 401) emailError.value = 'Incorrect password.'
    else if (status === 409) emailError.value = 'Email already registered.'
    else emailError.value = 'Failed to update email.'
  } finally {
    emailLoading.value = false
  }
}

// Password section
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordError = ref('')
const passwordSuccess = ref('')
const passwordLoading = ref(false)

async function savePassword() {
  passwordError.value = ''
  passwordSuccess.value = ''
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = 'New passwords do not match.'
    return
  }
  if (newPassword.value.length < 12) {
    passwordError.value = 'Password must be at least 12 characters.'
    return
  }
  passwordLoading.value = true
  try {
    await authStore.updatePassword(currentPassword.value, newPassword.value)
    passwordSuccess.value = 'Password updated.'
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  } catch (e: unknown) {
    passwordError.value = extractStatus(e) === 401 ? 'Incorrect current password.' : 'Failed to update password.'
  } finally {
    passwordLoading.value = false
  }
}
</script>

<template>
  <div class="profile">
    <header class="profile-header">
      <h1>Profile</h1>
      <nav class="profile-nav">
        <button
          class="theme-toggle"
          :title="themeStore.isDark ? 'Switch to day mode' : 'Switch to night mode'"
          @click="themeStore.toggle()"
        >
          <span aria-hidden="true">{{ themeStore.isDark ? '☀' : '🌙' }}</span>
        </button>
        <div ref="menuRef" class="hamburger-wrapper">
          <button
            class="hamburger-btn"
            :aria-expanded="showMenu"
            aria-haspopup="true"
            :aria-label="showMenu ? 'Close menu' : 'Open menu'"
            @keydown.esc.prevent="showMenu = false"
            @click.stop="showMenu = !showMenu"
          >
            <span class="bar" />
            <span class="bar" />
            <span class="bar" />
          </button>
          <div v-if="showMenu" class="dropdown-menu" role="menu" @keydown.esc.prevent="showMenu = false">
            <RouterLink
              class="dropdown-item"
              to="/dashboard"
              role="menuitem"
              @click="showMenu = false"
            >
              ← Dashboard
            </RouterLink>
          </div>
        </div>
      </nav>
    </header>

    <main class="profile-content">
      <section class="profile-card">
        <h2>Username</h2>
        <form @submit.prevent="saveUsername">
          <div class="field">
            <label for="profile-username">Username</label>
            <input
              id="profile-username"
              v-model="usernameInput"
              maxlength="50"
              pattern="[a-zA-Z0-9_-]+"
              placeholder="username"
            />
          </div>
          <p v-if="usernameError" class="error" role="alert">{{ usernameError }}</p>
          <p v-if="usernameSuccess" class="success" role="status">{{ usernameSuccess }}</p>
          <div class="actions">
            <button type="submit" class="btn-primary" :disabled="usernameLoading">
              {{ usernameLoading ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </form>
      </section>

      <section class="profile-card">
        <h2>Email</h2>
        <p class="current-value">Current: {{ authStore.user?.email }}</p>
        <form @submit.prevent="saveEmail">
          <div class="field">
            <label for="profile-email-password">Current password</label>
            <input
              id="profile-email-password"
              v-model="emailPassword"
              type="password"
              autocomplete="current-password"
              required
            />
          </div>
          <div class="field">
            <label for="profile-new-email">New email</label>
            <input
              id="profile-new-email"
              v-model="newEmail"
              type="email"
              autocomplete="email"
              required
            />
          </div>
          <p v-if="emailError" class="error" role="alert">{{ emailError }}</p>
          <p v-if="emailSuccess" class="success" role="status">{{ emailSuccess }}</p>
          <div class="actions">
            <button type="submit" class="btn-primary" :disabled="emailLoading">
              {{ emailLoading ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </form>
      </section>

      <section class="profile-card">
        <h2>Password</h2>
        <form @submit.prevent="savePassword">
          <div class="field">
            <label for="profile-current-password">Current password</label>
            <input
              id="profile-current-password"
              v-model="currentPassword"
              type="password"
              autocomplete="current-password"
              required
            />
          </div>
          <div class="field">
            <label for="profile-new-password">New password</label>
            <input
              id="profile-new-password"
              v-model="newPassword"
              type="password"
              autocomplete="new-password"
              minlength="12"
              maxlength="128"
              required
            />
          </div>
          <div class="field">
            <label for="profile-confirm-password">Confirm new password</label>
            <input
              id="profile-confirm-password"
              v-model="confirmPassword"
              type="password"
              autocomplete="new-password"
              required
            />
          </div>
          <p v-if="passwordError" class="error" role="alert">{{ passwordError }}</p>
          <p v-if="passwordSuccess" class="success" role="status">{{ passwordSuccess }}</p>
          <div class="actions">
            <button type="submit" class="btn-primary" :disabled="passwordLoading">
              {{ passwordLoading ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </form>
      </section>
    </main>
  </div>
</template>

<style scoped>
.profile {
  min-height: 100vh;
  background: var(--color-background);
}

.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 2rem;
  background: var(--color-background-soft);
  border-bottom: 1px solid var(--color-border);
  transition: background 0.35s ease, border-color 0.35s ease;
}

.profile-header h1 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--color-heading);
  letter-spacing: 0.02em;
}

.profile-nav {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.hamburger-wrapper {
  position: relative;
}

.hamburger-btn {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  width: 2.1rem;
  height: 2.1rem;
  padding: 0.35rem;
  background: transparent;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.hamburger-btn:hover {
  background: var(--color-border);
}

.hamburger-btn:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.bar {
  display: block;
  width: 100%;
  height: 2px;
  background: var(--color-text);
  border-radius: 2px;
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 160px;
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  padding: 0.25rem 0;
  z-index: 100;
}

.dropdown-item {
  display: block;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  color: var(--color-text);
  text-decoration: none;
  transition: background 0.15s;
}

.dropdown-item:hover {
  background: var(--color-background-mute);
}

.dropdown-item:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: -2px;
}

.theme-toggle {
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 50%;
  border: 1px solid var(--color-border-hover);
  background: transparent;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, border-color 0.2s, transform 0.2s;
  color: var(--color-text);
  padding: 0;
}

.theme-toggle:hover {
  background: var(--color-border);
  transform: rotate(15deg);
}

.theme-toggle:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.profile-content {
  max-width: 480px;
  margin: 0 auto;
  padding: 2rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.profile-card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1.25rem;
  transition: background 0.35s ease, border-color 0.35s ease;
}

.profile-card h2 {
  margin: 0 0 1rem;
  font-size: 1rem;
  color: var(--color-heading);
}

.current-value {
  margin: -0.5rem 0 1rem;
  font-size: 0.85rem;
  color: var(--color-text);
  opacity: 0.7;
}

.field {
  margin-bottom: 1rem;
}

.field label {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--color-text);
}

.field input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  box-sizing: border-box;
  font-size: 0.9375rem;
  background: var(--color-background);
  color: var(--color-text);
  transition: background 0.35s ease, border-color 0.2s, color 0.35s ease;
}

.field input:focus {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
  border-color: var(--color-accent);
}

.error {
  color: var(--color-error);
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

.success {
  color: var(--color-success, #22c55e);
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

.actions {
  display: flex;
  justify-content: flex-end;
}

.btn-primary {
  padding: 0.5rem 1.1rem;
  background: var(--color-accent);
  color: var(--color-background);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9375rem;
  transition: opacity 0.2s;
}

.btn-primary:hover {
  opacity: 0.85;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && bun run test:unit --run src/views/__tests__/ProfileView.spec.ts`
Expected: PASS (8 passed)

- [ ] **Step 5: Type-check**

Run: `cd frontend && bun run type-check`
Expected: PASS (no errors)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/ProfileView.vue frontend/src/views/__tests__/ProfileView.spec.ts
git commit -m "feat(frontend): add ProfileView with username/email/password sections"
```

---

### Task 6: Frontend — Remove inline username editor from `DashboardView.vue`, add Profile link

**Files:**
- Modify: `frontend/src/views/DashboardView.vue`
- Modify: `frontend/src/views/__tests__/DashboardView.spec.ts`

**Interfaces:**
- Consumes: the `/profile` route from Task 4.
- Produces: nothing consumed by later tasks — this is the last task in the plan.

- [ ] **Step 1: Remove the now-obsolete test block**

In `frontend/src/views/__tests__/DashboardView.spec.ts`, delete the entire `describe('DashboardView username editing', ...)` block — it is the last block in the file (currently lines 442-485, ending at the file's final `})`). After deletion the file should end with the `describe('DashboardView logout', ...)` block's closing `})` (currently line 440) as the last line.

Then add this replacement block at the end of the file, in its place:

```typescript
describe('DashboardView profile link', () => {
  it('has a Profile link in the hamburger menu, no click-to-edit username', async () => {
    const store = setupStores({ email: 'user@example.com', username: 'oldname', is_admin: false, created_at: '' })
    vi.spyOn(store, 'fetchAll').mockResolvedValue(undefined)
    const wrapper = mount(DashboardView, { global: globalOptions })
    await flushPromises()
    await wrapper.find('.hamburger-btn').trigger('click')
    const menu = wrapper.find('.dropdown-menu')
    expect(menu.text()).toContain('Profile')
    expect(menu.text()).toContain('oldname')
    expect(wrapper.find('.user-item').exists()).toBe(false)
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && bun run test:unit --run src/views/__tests__/DashboardView.spec.ts`
Expected: FAIL — the new test fails because `.dropdown-menu` doesn't yet contain "Profile" (still shows the click-to-edit username button instead).

- [ ] **Step 3: Remove the inline username editor state and functions**

In `frontend/src/views/DashboardView.vue`, remove these three lines from the `<script setup>` block (lines 37-39):

```typescript
const editingUsername = ref(false)
const usernameInput = ref('')
const usernameError = ref('')
```

Remove these two functions (lines 47-61):

```typescript
function startEditUsername() {
  usernameInput.value = authStore.user?.username ?? ''
  usernameError.value = ''
  editingUsername.value = true
}

async function saveUsername() {
  usernameError.value = ''
  try {
    await authStore.updateUsername(usernameInput.value)
    editingUsername.value = false
  } catch {
    usernameError.value = 'Failed to update username'
  }
}
```

- [ ] **Step 4: Replace the inline editor markup with plain text + Profile link**

In `frontend/src/views/DashboardView.vue`'s `<template>`, replace this block:

```html
            <div class="dropdown-user">
              <template v-if="editingUsername">
                <input
                  v-model="usernameInput"
                  class="username-input"
                  placeholder="username"
                  maxlength="50"
                  @keyup.enter="saveUsername"
                  @keyup.escape="editingUsername = false"
                />
                <div class="username-actions">
                  <button class="btn-save-username" @click="saveUsername">Save</button>
                  <button class="btn-cancel-username" @click="editingUsername = false">Cancel</button>
                </div>
                <span v-if="usernameError" class="error-sm">{{ usernameError }}</span>
              </template>
              <template v-else>
                <button class="dropdown-item user-item" role="menuitem" @click="startEditUsername">
                  <span class="user-display">{{ authStore.user?.username ?? authStore.user?.email }}</span>
                  <span class="edit-hint">edit</span>
                </button>
              </template>
            </div>
            <hr class="dropdown-sep" />
            <RouterLink
              v-if="authStore.user?.is_admin"
              class="dropdown-item"
              to="/admin"
              role="menuitem"
              @click="showMenu = false"
            >Admin</RouterLink>
```

with:

```html
            <div class="dropdown-user">
              <span class="user-display">{{ authStore.user?.username ?? authStore.user?.email }}</span>
            </div>
            <hr class="dropdown-sep" />
            <RouterLink
              class="dropdown-item"
              to="/profile"
              role="menuitem"
              @click="showMenu = false"
            >Profile</RouterLink>
            <RouterLink
              v-if="authStore.user?.is_admin"
              class="dropdown-item"
              to="/admin"
              role="menuitem"
              @click="showMenu = false"
            >Admin</RouterLink>
```

- [ ] **Step 5: Remove the now-dead CSS**

In `frontend/src/views/DashboardView.vue`'s `<style scoped>` block, remove these rules (they only styled the removed inline editor and its "edit" button):

```css
.user-item {
  justify-content: space-between;
  gap: 0.5rem;
}

.edit-hint {
  font-size: 0.75rem;
  opacity: 0.5;
  flex-shrink: 0;
}

.username-input {
  width: 100%;
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  background: var(--color-background);
  color: var(--color-text);
  box-sizing: border-box;
}

.username-input:focus {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
}

.username-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.4rem;
}

.btn-save-username,
.btn-cancel-username {
  flex: 1;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--color-border-hover);
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  color: var(--color-text);
  transition: background 0.2s;
}

.btn-save-username:hover,
.btn-cancel-username:hover {
  background: var(--color-border);
}

.error-sm {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.78rem;
  color: var(--color-error);
}
```

Keep `.user-display` (still used for the plain-text username) and `.dropdown-user` (still used as the wrapper div).

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd frontend && bun run test:unit --run src/views/__tests__/DashboardView.spec.ts`
Expected: PASS (all tests in the file pass, including the new "Profile link" test)

- [ ] **Step 7: Run the full frontend test suite to check for regressions**

Run: `cd frontend && bun run test:unit --run`
Expected: all tests pass

- [ ] **Step 8: Type-check**

Run: `cd frontend && bun run type-check`
Expected: PASS (no errors, no unused-variable warnings for the removed refs/functions)

- [ ] **Step 9: Commit**

```bash
git add frontend/src/views/DashboardView.vue frontend/src/views/__tests__/DashboardView.spec.ts
git commit -m "refactor(frontend): replace inline username editor with Profile link"
```

---

## Manual verification (after all tasks)

- [ ] Start the stack (`docker compose up --build` or local dev servers), log in, open the hamburger menu on `/dashboard` — confirm it shows the username as plain text and a "Profile" link (and "Admin" link if applicable), no click-to-edit affordance.
- [ ] Click "Profile", confirm `/profile` loads with three sections.
- [ ] Change username, confirm success message and the dashboard's dropdown reflects the new name after navigating back.
- [ ] Change email with the wrong current password, confirm "Incorrect password." error.
- [ ] Change email with the correct current password to a fresh address, confirm success and `GET /api/auth/me` reflects it.
- [ ] Change password with the correct current password, confirm success, then open a second tab/incognito window with the old cookie (or just try logging in with the old password) and confirm it's rejected while the original tab is still logged in.
