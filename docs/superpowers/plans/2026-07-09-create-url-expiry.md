# Create-URL Expiry Input Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users set an `expires_at` on a link at creation time, instead of only via a follow-up edit.

**Architecture:** Thread `expires_at` through the existing create-URL path end to end: `URLCreate` schema (backend) → `create_url` endpoint (backend) → `urlsApi.create()` (frontend) → `urlsStore.create()` (frontend) → `CreateURLForm.vue` (frontend). No new endpoints, no new components — every touched function already exists and gains one optional parameter/field.

**Tech Stack:** FastAPI + Pydantic v2 (backend), Vue 3 + Pinia + TypeScript + Vitest (frontend), pytest (backend tests).

## Global Constraints

- `expires_at` must be in the future when provided — same rule `URLUpdate` already enforces (`backend/src/app/schemas.py`), reused via a shared mixin, not duplicated.
- No client-side "must be future" validation and no `:min` attribute on the new input — the existing edit-dialog expiry input (`DashboardView.vue:227`) has neither; stay consistent.
- Empty/omitted expiry on create must behave exactly like today (no expiry set) — do not change default behavior for the existing no-expiry path.
- Run backend tests with `uv run python -m pytest`, not `uv run pytest` (project convention).
- Run frontend tests with `bun run test:unit -- run [path]`.

---

### Task 1: Backend — `expires_at` on create

**Files:**
- Modify: `backend/src/app/schemas.py:121-150` (`URLCreate`, `URLUpdate`)
- Modify: `backend/src/app/routers/urls.py:55-60` (`create_url`)
- Test: `backend/tests/test_urls.py`

**Interfaces:**
- Consumes: nothing new from other tasks (backend-only, independent of Tasks 2/3).
- Produces: `POST /api/urls` accepts an optional `expires_at` (ISO 8601 string) in the request body, rejects a past value with `422`, and returns it in the response's `expires_at` field when accepted.

- [ ] **Step 1: Write the failing tests**

Open `backend/tests/test_urls.py` and add these two tests immediately after `test_create_url_password_too_short_rejected` (currently ends at line 95, right before `test_delete_url_not_found`):

```python
async def test_create_url_expiry_future_accepted(auth_client):
    resp = await auth_client.post("/api/urls", json={"original_url": "https://exp3.com", "expires_at": "2099-01-01T00:00:00Z"})
    assert resp.status_code == 201
    assert resp.json()["expires_at"] is not None

async def test_create_url_expiry_past_rejected(auth_client):
    resp = await auth_client.post("/api/urls", json={"original_url": "https://exp4.com", "expires_at": "2020-01-01T00:00:00Z"})
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run python -m pytest tests/test_urls.py -k expiry -v`
Expected: `test_create_url_expiry_future_accepted` FAILs with `assert resp.json()["expires_at"] is not None` (it's `None` — the field is silently dropped since `URLCreate` doesn't declare it yet). `test_create_url_expiry_past_rejected` FAILs with `assert 201 == 422` (no validator exists yet to reject it, so it's accepted).

- [ ] **Step 3: Extract the shared validator and add the field**

In `backend/src/app/schemas.py`, the current `URLCreate`/`URLUpdate` section (lines 121–150) reads:

```python
class URLCreate(BaseModel):
    original_url: AnyHttpUrl
    custom_code: str | None = Field(None, min_length=6, max_length=16, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str | None = Field(None, min_length=6, max_length=128)

    @field_validator("original_url", mode="before")
    @classmethod
    def url_max_length(cls, v: object) -> object:
        if isinstance(v, str) and len(v) > 2048:
            raise ValueError("URL must not exceed 2048 characters")
        return v


class URLUpdate(BaseModel):
    short_code: str = Field(..., min_length=3, max_length=16, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = ""
    remove_password: bool = False
    expires_at: datetime | None = None

    @field_validator("expires_at", mode="after")
    @classmethod
    def expires_must_be_future(cls, v: object) -> object:
        if v is None:
            return v
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v <= datetime.now(timezone.utc):
                raise ValueError("Expiry must be in the future")
        return v
```

Replace that whole block with:

```python
class _ExpiresAtValidatorMixin:
    @field_validator("expires_at", mode="after")
    @classmethod
    def expires_must_be_future(cls, v: object) -> object:
        if v is None:
            return v
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v <= datetime.now(timezone.utc):
                raise ValueError("Expiry must be in the future")
        return v


class URLCreate(_ExpiresAtValidatorMixin, BaseModel):
    original_url: AnyHttpUrl
    custom_code: str | None = Field(None, min_length=6, max_length=16, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str | None = Field(None, min_length=6, max_length=128)
    expires_at: datetime | None = None

    @field_validator("original_url", mode="before")
    @classmethod
    def url_max_length(cls, v: object) -> object:
        if isinstance(v, str) and len(v) > 2048:
            raise ValueError("URL must not exceed 2048 characters")
        return v


class URLUpdate(_ExpiresAtValidatorMixin, BaseModel):
    short_code: str = Field(..., min_length=3, max_length=16, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = ""
    remove_password: bool = False
    expires_at: datetime | None = None
```

Pydantic v2 inherits `field_validator`-decorated methods from mixins, so both models run the same validation logic from one definition — no duplicated rule.

- [ ] **Step 4: Wire the field into the created `URL` row**

In `backend/src/app/routers/urls.py`, `create_url` currently builds the row without `expires_at` (lines 55–60):

```python
    url = URL(
        user_id=current_user.id,
        original_url=str(data.original_url),
        short_code=code,
        password_hash=await hash_password_async(data.password) if data.password else None,
    )
```

Change it to:

```python
    url = URL(
        user_id=current_user.id,
        original_url=str(data.original_url),
        short_code=code,
        password_hash=await hash_password_async(data.password) if data.password else None,
        expires_at=data.expires_at,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run python -m pytest tests/test_urls.py -v`
Expected: all tests in the file PASS, including the two new ones.

- [ ] **Step 6: Commit**

```bash
git add backend/src/app/schemas.py backend/src/app/routers/urls.py backend/tests/test_urls.py
git commit -m "$(cat <<'EOF'
feat(backend): accept expires_at on URL creation

Disclosure: Based on Claude Code generated output.

URLCreate previously had no expires_at field, so setting one required
a create then an immediate edit. Extracts URLUpdate's "must be in the
future" validator into a shared mixin so URLCreate reuses the same
rule instead of duplicating it.
EOF
)"
```

---

### Task 2: Frontend — plumb `expiresAt` through the API client and store

**Files:**
- Modify: `frontend/src/api/urls.ts:44-47` (`urlsApi.create`)
- Modify: `frontend/src/stores/urls.ts:13-17` (`create`)
- Test: `frontend/src/stores/__tests__/urls.spec.ts`

**Interfaces:**
- Consumes: nothing from Task 1 directly (frontend and backend are independently testable — the mocked API layer means this task doesn't require Task 1's backend changes to be live).
- Produces: `urlsStore.create(originalUrl, customCode?, password?, expiresAt?)` — a fourth optional parameter, an ISO 8601 string, forwarded unchanged to `urlsApi.create()`. Task 3 calls this signature.

- [ ] **Step 1: Write the failing test**

In `frontend/src/stores/__tests__/urls.spec.ts`, add this test immediately after the existing `'create prepends url to list'` test (ends at line 42):

```ts
  it('create passes expiresAt through to the API client', async () => {
    vi.mocked(urlsApiModule.urlsApi.list).mockResolvedValue([])
    vi.mocked(urlsApiModule.urlsApi.create).mockResolvedValue(mockURL)
    const store = useURLsStore()
    await store.fetchAll()
    await store.create('https://ex.com', undefined, undefined, '2099-01-01T00:00:00.000Z')
    expect(urlsApiModule.urlsApi.create).toHaveBeenCalledWith(
      'https://ex.com', undefined, undefined, '2099-01-01T00:00:00.000Z',
    )
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && bun run test:unit -- run src/stores/__tests__/urls.spec.ts`
Expected: FAIL — `create` is called with 2 args (`originalUrl`, `undefined` for customCode... actually only whatever `store.create` currently forwards), so the mock's recorded call won't match the 4-arg expectation. The exact failure is a `toHaveBeenCalledWith` mismatch.

- [ ] **Step 3: Add the fourth parameter to the store**

In `frontend/src/stores/urls.ts`, the current `create` function (lines 13–17) reads:

```ts
  async function create(originalUrl: string, customCode?: string, password?: string) {
    const created = await urlsApi.create(originalUrl, customCode, password)
    urls.value.unshift(created)
    return created
  }
```

Change it to:

```ts
  async function create(originalUrl: string, customCode?: string, password?: string, expiresAt?: string) {
    const created = await urlsApi.create(originalUrl, customCode, password, expiresAt)
    urls.value.unshift(created)
    return created
  }
```

- [ ] **Step 4: Add the fourth parameter to the API client**

In `frontend/src/api/urls.ts`, the current `create` method (lines 44–47) reads:

```ts
  async create(original_url: string, custom_code?: string, password?: string): Promise<URLOut> {
    const { data } = await apiClient.post<URLOut>('/api/urls', { original_url, custom_code, password })
    return data
  },
```

Change it to:

```ts
  async create(original_url: string, custom_code?: string, password?: string, expires_at?: string): Promise<URLOut> {
    const { data } = await apiClient.post<URLOut>('/api/urls', { original_url, custom_code, password, expires_at })
    return data
  },
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && bun run test:unit -- run src/stores/__tests__/urls.spec.ts`
Expected: PASS, all tests in the file green.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/urls.ts frontend/src/stores/urls.ts frontend/src/stores/__tests__/urls.spec.ts
git commit -m "$(cat <<'EOF'
feat(frontend): add expiresAt param to urlsApi/urlsStore create()

Disclosure: Based on Claude Code generated output.

Plumbing-only change: forwards an optional ISO expiry string from the
store down to the API client's POST /api/urls call. No UI yet — that's
CreateURLForm.vue, next.
EOF
)"
```

---

### Task 3: Frontend — expiry field in `CreateURLForm.vue`

**Files:**
- Modify: `frontend/src/components/CreateURLForm.vue`
- Test: `frontend/src/components/__tests__/CreateURLForm.spec.ts`

**Interfaces:**
- Consumes: `urlsStore.create(originalUrl, customCode?, password?, expiresAt?)` from Task 2 — must be merged/present before this task's tests can pass, since the store mock in the existing test file is a bare `vi.fn()` (no real signature enforcement), but the *production* call site now sends 4 args, so `urlsStore.create` must already accept a 4th one for the app to behave correctly end to end.
- Produces: nothing consumed by later tasks — this is the last task.

- [ ] **Step 1: Update the four existing call-site assertions (RED first)**

The existing tests in `frontend/src/components/__tests__/CreateURLForm.spec.ts` assert `createSpy` was called with exactly 3 positional args. Once Step 3 below adds a 4th argument to every `handleCreate` call, those assertions will fail on arg-count mismatch unless updated first. Update these four `toHaveBeenCalledWith` calls now (before implementing, so you can watch them fail for the *right* reason in Step 2):

Line 36 (`'calls store.create with valid URL'`), change:
```ts
    expect(createSpy).toHaveBeenCalledWith('https://example.com', undefined, undefined)
```
to:
```ts
    expect(createSpy).toHaveBeenCalledWith('https://example.com', undefined, undefined, undefined)
```

Line 45 (`'prepends https:// when protocol missing'`), same change:
```ts
    expect(createSpy).toHaveBeenCalledWith('https://example.com', undefined, undefined, undefined)
```

Line 55 (`'passes custom code when provided'`), change:
```ts
    expect(createSpy).toHaveBeenCalledWith('https://example.com', 'my-link', undefined)
```
to:
```ts
    expect(createSpy).toHaveBeenCalledWith('https://example.com', 'my-link', undefined, undefined)
```

Line 65 (`'passes password when provided'`), change:
```ts
    expect(createSpy).toHaveBeenCalledWith('https://example.com', undefined, 'secret')
```
to:
```ts
    expect(createSpy).toHaveBeenCalledWith('https://example.com', undefined, 'secret', undefined)
```

Now add a new test right after `'passes password when provided'` (after line 66's closing `})`):

```ts
  it('passes expiry date when provided', async () => {
    createSpy.mockResolvedValue(undefined)
    const wrapper = mount(CreateURLForm)
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#expires-at').setValue('2099-01-01T00:00')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect(createSpy).toHaveBeenCalledWith(
      'https://example.com',
      undefined,
      undefined,
      new Date('2099-01-01T00:00').toISOString(),
    )
  })
```

Finally, update `'clears form fields after successful creation'` (currently lines 107–116) to also set and check the new field. Change:

```ts
  it('clears form fields after successful creation', async () => {
    createSpy.mockResolvedValue(undefined)
    const wrapper = mount(CreateURLForm)
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#custom-code').setValue('mylink')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect((wrapper.find('#original-url').element as HTMLInputElement).value).toBe('')
    expect((wrapper.find('#custom-code').element as HTMLInputElement).value).toBe('')
  })
```

to:

```ts
  it('clears form fields after successful creation', async () => {
    createSpy.mockResolvedValue(undefined)
    const wrapper = mount(CreateURLForm)
    await wrapper.find('#original-url').setValue('https://example.com')
    await wrapper.find('#custom-code').setValue('mylink')
    await wrapper.find('#expires-at').setValue('2099-01-01T00:00')
    await wrapper.find('[data-testid="create-url-form"]').trigger('submit')
    await flushPromises()
    expect((wrapper.find('#original-url').element as HTMLInputElement).value).toBe('')
    expect((wrapper.find('#custom-code').element as HTMLInputElement).value).toBe('')
    expect((wrapper.find('#expires-at').element as HTMLInputElement).value).toBe('')
  })
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && bun run test:unit -- run src/components/__tests__/CreateURLForm.spec.ts`
Expected: FAIL. The four updated assertions fail on arg-count mismatch (3 actual vs 4 expected). `'passes expiry date when provided'` and the updated `'clears form fields...'` test both fail with "Cannot call setValue on an empty wrapper" (`#expires-at` doesn't exist yet).

- [ ] **Step 3: Add the `expiresAt` ref and wire it into `handleCreate`**

In `frontend/src/components/CreateURLForm.vue`, the current script setup (lines 1–51) reads:

```html
<script setup lang="ts">
import { ref } from 'vue'
import { useURLsStore } from '../stores/urls'

const urlsStore = useURLsStore()
const originalUrl = ref('')
const customCode = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleCreate() {
  error.value = ''
  if (originalUrl.value && !/^https?:\/\//i.test(originalUrl.value)) {
    originalUrl.value = 'https://' + originalUrl.value
  }
  try {
    const parsed = new URL(originalUrl.value)
    if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
      error.value = 'Only http and https URLs are allowed.'
      return
    }
  } catch {
    error.value = 'Please enter a valid URL.'
    return
  }
  if (customCode.value && !/^[A-Za-z0-9_-]{6,16}$/.test(customCode.value)) {
    error.value = 'Custom code must be 6–16 characters and contain only letters, digits, hyphens, or underscores.'
    return
  }
  if (password.value && password.value.length < 6) {
    error.value = 'Password must be at least 6 characters.'
    return
  }
  loading.value = true
  try {
    await urlsStore.create(originalUrl.value, customCode.value || undefined, password.value || undefined)
    originalUrl.value = ''
    customCode.value = ''
    password.value = ''
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } }).response?.status
    if (status === 409) {
      error.value = 'Short code already taken.'
    } else {
      error.value = 'Failed to create URL.'
    }
  } finally {
    loading.value = false
  }
}
</script>
```

Change it to:

```html
<script setup lang="ts">
import { ref } from 'vue'
import { useURLsStore } from '../stores/urls'

const urlsStore = useURLsStore()
const originalUrl = ref('')
const customCode = ref('')
const password = ref('')
const expiresAt = ref('')
const error = ref('')
const loading = ref(false)

async function handleCreate() {
  error.value = ''
  if (originalUrl.value && !/^https?:\/\//i.test(originalUrl.value)) {
    originalUrl.value = 'https://' + originalUrl.value
  }
  try {
    const parsed = new URL(originalUrl.value)
    if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
      error.value = 'Only http and https URLs are allowed.'
      return
    }
  } catch {
    error.value = 'Please enter a valid URL.'
    return
  }
  if (customCode.value && !/^[A-Za-z0-9_-]{6,16}$/.test(customCode.value)) {
    error.value = 'Custom code must be 6–16 characters and contain only letters, digits, hyphens, or underscores.'
    return
  }
  if (password.value && password.value.length < 6) {
    error.value = 'Password must be at least 6 characters.'
    return
  }
  loading.value = true
  try {
    await urlsStore.create(
      originalUrl.value,
      customCode.value || undefined,
      password.value || undefined,
      expiresAt.value ? new Date(expiresAt.value).toISOString() : undefined,
    )
    originalUrl.value = ''
    customCode.value = ''
    password.value = ''
    expiresAt.value = ''
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } }).response?.status
    if (status === 409) {
      error.value = 'Short code already taken.'
    } else {
      error.value = 'Failed to create URL.'
    }
  } finally {
    loading.value = false
  }
}
</script>
```

- [ ] **Step 4: Add the template field**

In the same file, the current template's password field block (lines 65–68) reads:

```html
    <div class="field">
      <label for="link-password">Password protection (optional)</label>
      <input id="link-password" v-model="password" type="password" placeholder="Leave blank for public link" minlength="6" maxlength="128" autocomplete="new-password" />
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
```

Change it to:

```html
    <div class="field">
      <label for="link-password">Password protection (optional)</label>
      <input id="link-password" v-model="password" type="password" placeholder="Leave blank for public link" minlength="6" maxlength="128" autocomplete="new-password" />
    </div>
    <div class="field">
      <label for="expires-at">Expires at (optional)</label>
      <input id="expires-at" v-model="expiresAt" type="datetime-local" />
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && bun run test:unit -- run src/components/__tests__/CreateURLForm.spec.ts`
Expected: PASS, all tests in the file green (existing + 1 new + 1 modified).

- [ ] **Step 6: Run the full frontend suite, type-check, and lint**

Run: `cd frontend && bun run test:unit -- run`
Expected: all test files PASS (149 tests: 147 existing + 1 new CreateURLForm test (`'passes expiry date when provided'`) + 1 new urls-store test (`'create passes expiresAt through to the API client'`); the modified `'clears form fields...'` test and the four updated `toHaveBeenCalledWith` assertions don't change the count).

Run: `cd frontend && bun run type-check`
Expected: no errors.

Run: `cd frontend && bun run lint`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/CreateURLForm.vue frontend/src/components/__tests__/CreateURLForm.spec.ts
git commit -m "$(cat <<'EOF'
feat(frontend): add expiry input to the create-URL form

Disclosure: Based on Claude Code generated output.

Adds a third optional field (datetime-local, styled identically to
the existing custom-code/password fields) so users can set an expiry
when first shortening a link instead of only via the Dashboard's edit
dialog. No client-side "must be future" check or :min attribute,
matching the existing edit-dialog expiry input's behavior — a past
value is caught server-side and surfaces through the form's existing
generic error message, same as any other create-time validation
failure.
EOF
)"
```

---

## Post-Implementation

After Task 3's commit, run the full verification one more time from the worktree root to confirm nothing regressed across the whole change set:

```bash
cd backend && uv run python -m pytest -v
cd ../frontend && bun run test:unit -- run && bun run type-check && bun run lint && bun run build
```

Then push the branch and open a PR against `develop`, following this repo's established workflow (worktree → PR → review → merge).
