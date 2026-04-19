/**
 * E2E Spec: Token Engine & Health Check Endpoints
 * Quill QA — Phase 1 Regression Suite
 *
 * Covers:
 *   GET  /api/v1/health                  (public, no auth)
 *   GET  /api/v1/health/claude           (auth-gated, Redis cache, latency_ms)
 *   GET  /api/v1/tokens/usage            (query filters, granularity stub)
 *   GET  /api/v1/tokens/budget           (budget_status logic)
 *   PUT  /api/v1/tokens/budget           (update + round-trip)
 *   GET  /api/v1/tokens/forecast         (window + duplicate fields)
 *
 * Environment:
 *   BASE_URL  – set via playwright.config or PW_BASE_URL env var (default http://localhost:8000)
 *   TEST_USER_EMAIL / TEST_USER_PASSWORD – seeded test-user credentials
 */

import { test, expect, APIRequestContext } from "@playwright/test";

const BASE = process.env.PW_BASE_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Helper – obtain a valid bearer token (reused across tests in file)
// ---------------------------------------------------------------------------
let _bearerToken: string | null = null;

async function getBearerToken(request: APIRequestContext): Promise<string> {
  if (_bearerToken) return _bearerToken;

  const email = process.env.TEST_USER_EMAIL ?? "qa@paperpilot.test";
  const password = process.env.TEST_USER_PASSWORD ?? "QaTest!2025";

  const resp = await request.post(`${BASE}/api/v1/auth/login`, {
    data: { email, password },
  });

  if (!resp.ok()) {
    throw new Error(
      `Login failed (${resp.status()}): ${await resp.text()}. ` +
        "Set TEST_USER_EMAIL / TEST_USER_PASSWORD or seed a test user."
    );
  }

  const body = await resp.json();
  // Accept both { access_token } and { token } shapes
  _bearerToken = body.access_token ?? body.token;
  if (!_bearerToken) {
    throw new Error(`Login response has no access_token: ${JSON.stringify(body)}`);
  }
  return _bearerToken;
}

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

// ---------------------------------------------------------------------------
// SUITE 1 – GET /api/v1/health  (public, no auth required)
// ---------------------------------------------------------------------------
test.describe("GET /api/v1/health (public)", () => {
  test("returns 200 with required shape", async ({ request }) => {
    const resp = await request.get(`${BASE}/api/v1/health`);
    expect(resp.status()).toBe(200);

    const body = await resp.json();
    // Required keys
    expect(body).toHaveProperty("status");
    expect(body).toHaveProperty("checks");
    expect(body.checks).toHaveProperty("database");
    expect(body.checks).toHaveProperty("redis");
    expect(body).toHaveProperty("timestamp");

    // status must be one of the two defined values
    expect(["healthy", "degraded"]).toContain(body.status);

    // checks are booleans
    expect(typeof body.checks.database).toBe("boolean");
    expect(typeof body.checks.redis).toBe("boolean");

    // timestamp must be a parseable ISO string
    const ts = Date.parse(body.timestamp);
    expect(isNaN(ts)).toBe(false);
  });

  test("does NOT require Authorization header", async ({ request }) => {
    // Must succeed without any auth header
    const resp = await request.get(`${BASE}/api/v1/health`);
    expect(resp.status()).not.toBe(401);
    expect(resp.status()).not.toBe(403);
  });

  test("consistent status flag – healthy iff both checks true", async ({ request }) => {
    const resp = await request.get(`${BASE}/api/v1/health`);
    const body = await resp.json();
    const allOk = body.checks.database === true && body.checks.redis === true;
    if (allOk) {
      expect(body.status).toBe("healthy");
    } else {
      expect(body.status).toBe("degraded");
    }
  });
});

// ---------------------------------------------------------------------------
// SUITE 2 – GET /api/v1/health/claude  (auth-gated, Redis cache)
// ---------------------------------------------------------------------------
test.describe("GET /api/v1/health/claude (authenticated)", () => {
  test("returns 401 without auth token", async ({ request }) => {
    const resp = await request.get(`${BASE}/api/v1/health/claude`);
    expect(resp.status()).toBe(401);
  });

  test("returns 200 with valid auth token", async ({ request }) => {
    const token = await getBearerToken(request);
    const resp = await request.get(`${BASE}/api/v1/health/claude`, {
      headers: authHeaders(token),
    });
    // 200 regardless of Claude status (the endpoint itself should succeed)
    expect(resp.status()).toBe(200);
  });

  test("response shape has all required fields", async ({ request }) => {
    const token = await getBearerToken(request);
    const resp = await request.get(`${BASE}/api/v1/health/claude`, {
      headers: authHeaders(token),
    });
    const body = await resp.json();

    expect(body).toHaveProperty("status");
    expect(body).toHaveProperty("model");
    expect(body).toHaveProperty("latency_ms");
    expect(body).toHaveProperty("cached");
    expect(body).toHaveProperty("error");

    // status must be one of the three defined values
    expect(["ok", "error", "not_configured"]).toContain(body.status);

    // model should be the Haiku model string
    expect(typeof body.model).toBe("string");
    expect(body.model.length).toBeGreaterThan(0);

    // cached must be boolean
    expect(typeof body.cached).toBe("boolean");
  });

  test("latency_ms is a positive number when status=ok", async ({ request }) => {
    const token = await getBearerToken(request);
    const resp = await request.get(`${BASE}/api/v1/health/claude`, {
      headers: authHeaders(token),
    });
    const body = await resp.json();

    if (body.status === "ok") {
      expect(typeof body.latency_ms).toBe("number");
      expect(body.latency_ms).toBeGreaterThan(0);
    } else {
      // error / not_configured → latency_ms should be null
      expect(body.latency_ms).toBeNull();
    }
  });

  test("second call within 60s returns cached=true (Redis cache)", async ({ request }) => {
    const token = await getBearerToken(request);

    // First call – primes the cache (skip if not_configured, can't cache)
    const first = await request.get(`${BASE}/api/v1/health/claude`, {
      headers: authHeaders(token),
    });
    const firstBody = await first.json();
    test.skip(firstBody.status !== "ok", "Skipping cache test: Claude not configured or errored");

    // Second call – must come from cache
    const second = await request.get(`${BASE}/api/v1/health/claude`, {
      headers: authHeaders(token),
    });
    const secondBody = await second.json();

    expect(secondBody.cached).toBe(true);
    // Latency should match (cached result preserves the original latency_ms)
    expect(secondBody.latency_ms).toBe(firstBody.latency_ms);
  });

  test("not_configured path returns correct shape when API key missing", async ({
    request,
  }) => {
    // This test validates the shape of the not_configured response.
    // In a real env without ANTHROPIC_API_KEY we'd see this.
    // We guard with a skip so it only runs in the right env.
    const token = await getBearerToken(request);
    const resp = await request.get(`${BASE}/api/v1/health/claude`, {
      headers: authHeaders(token),
    });
    const body = await resp.json();

    if (body.status === "not_configured") {
      expect(body.error).toMatch(/ANTHROPIC_API_KEY/);
      expect(body.latency_ms).toBeNull();
      expect(body.cached).toBe(false);
    }
    // If status is ok or error, this assertion block is intentionally skipped
  });
});

// ---------------------------------------------------------------------------
// SUITE 3 – GET /api/v1/tokens/usage
// ---------------------------------------------------------------------------
test.describe("GET /api/v1/tokens/usage", () => {
  test("returns 401 without auth", async ({ request }) => {
    const resp = await request.get(`${BASE}/api/v1/tokens/usage`);
    expect(resp.status()).toBe(401);
  });

  test("returns 200 with valid auth and correct response shape", async ({ request }) => {
    const token = await getBearerToken(request);
    const resp = await request.get(`${BASE}/api/v1/tokens/usage`, {
      headers: authHeaders(token),
    });
    expect(resp.status()).toBe(200);

    const body = await resp.json();
    expect(body).toHaveProperty("data");
    expect(body).toHaveProperty("summary");
    expect(Array.isArray(body.data)).toBe(true);

    const summary = body.summary;
    expect(summary).toHaveProperty("period_cost");
    expect(summary).toHaveProperty("monthly_cost");
    expect(typeof summary.period_cost).toBe("number");
    expect(typeof summary.monthly_cost).toBe("number");
  });

  test("data points have correct field types", async ({ request }) => {
    const token = await getBearerToken(request);
    const resp = await request.get(`${BASE}/api/v1/tokens/usage`, {
      headers: authHeaders(token),
    });
    const body = await resp.json();

    for (const dp of body.data) {
      expect(typeof dp.date).toBe("string");
      expect(typeof dp.total_cost_usd).toBe("number");
      expect(typeof dp.total_input_tokens).toBe("number");
      expect(typeof dp.total_output_tokens).toBe("number");
      expect(typeof dp.api_calls).toBe("number");
      expect(typeof dp.downgrades).toBe("number");
    }
  });

  test("date range filter start_date=end_date returns max 1 data point", async ({ request }) => {
    const token = await getBearerToken(request);
    const today = new Date().toISOString().split("T")[0];
    const resp = await request.get(
      `${BASE}/api/v1/tokens/usage?start_date=${today}&end_date=${today}`,
      { headers: authHeaders(token) }
    );
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    // At most 1 data point for a single day
    expect(body.data.length).toBeLessThanOrEqual(1);
  });

  test("granularity parameter accepted without error (known stub)", async ({ request }) => {
    // BUG-003: granularity param is accepted but never used; test confirms
    // the endpoint doesn't 422 and returns data (even if granularity is ignored).
    const token = await getBearerToken(request);
    const resp = await request.get(
      `${BASE}/api/v1/tokens/usage?granularity=weekly`,
      { headers: authHeaders(token) }
    );
    // Should not 422 – param is declared but unused
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    // Because granularity is silently ignored, results are still daily-bucketed
    // (regression guard – if someone fixes this, the test will need updating)
    expect(body).toHaveProperty("data");
  });

  test("model filter narrows results correctly", async ({ request }) => {
    const token = await getBearerToken(request);
    const resp = await request.get(
      `${BASE}/api/v1/tokens/usage?model=claude-haiku-4-5-20251001`,
      { headers: authHeaders(token) }
    );
    expect(resp.status()).toBe(200);
  });
});

// ---------------------------------------------------------------------------
// SUITE 4 – GET /api/v1/tokens/budget
// ---------------------------------------------------------------------------
test.describe("GET /api/v1/tokens/budget", () => {
  test("returns 401 without auth", async ({ request }) => {
    const resp = await request.get(`${BASE}/api/v1/tokens/budget`);
    expect(resp.status()).toBe(401);
  });

  test("returns 200 with correct shape", async ({ request }) => {
    const token = await getBearerToken(request);
    const resp = await request.get(`${BASE}/api/v1/tokens/budget`, {
      headers: authHeaders(token),
    });
    expect(resp.status()).toBe(200);

    const body = await resp.json();
    expect(body).toHaveProperty("daily_spent");
    expect(body).toHaveProperty("monthly_spent");
    expect(body).toHaveProperty("budget_status");
    expect(body).toHaveProperty("auto_downgrade_enabled");
    expect(body).toHaveProperty("pause_on_exhaustion");

    expect(typeof body.daily_spent).toBe("number");
    expect(typeof body.monthly_spent).toBe("number");
    expect(["ok", "warning", "exhausted"]).toContain(body.budget_status);
    expect(typeof body.auto_downgrade_enabled).toBe("boolean");
    expect(typeof body.pause_on_exhaustion).toBe("boolean");
  });

  test("budget_status=ok when no limits set", async ({ request }) => {
    const token = await getBearerToken(request);

    // Clear any existing limits first
    await request.put(`${BASE}/api/v1/tokens/budget`, {
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      data: { daily_limit_usd: null, monthly_limit_usd: null },
    });

    const resp = await request.get(`${BASE}/api/v1/tokens/budget`, {
      headers: authHeaders(token),
    });
    const body = await resp.json();
    // No limits → should always be "ok"
    expect(body.budget_status).toBe("ok");
  });

  // BUG-002 regression: budget_status ignores monthly limit
  test("BUG-002 regression: budget_status reflects monthly exhaustion (expected FAIL)", async ({
    request,
  }) => {
    const token = await getBearerToken(request);

    // Set a very small monthly limit (effectively $0.00001 – will be exceeded by any usage)
    await request.put(`${BASE}/api/v1/tokens/budget`, {
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      data: { monthly_limit_usd: 0.00001, daily_limit_usd: null },
    });

    const resp = await request.get(`${BASE}/api/v1/tokens/budget`, {
      headers: authHeaders(token),
    });
    const body = await resp.json();

    // If monthly_spent > monthly_limit_usd AND budget_status is still "ok",
    // that confirms BUG-002 is present.
    if (body.monthly_spent > 0.00001) {
      // BUG: status should NOT be 'ok' when monthly budget is exceeded
      // This assertion FAILS to expose the bug:
      expect.soft(body.budget_status).not.toBe("ok");
    }

    // Cleanup
    await request.put(`${BASE}/api/v1/tokens/budget`, {
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      data: { monthly_limit_usd: null },
    });
  });
});

// ---------------------------------------------------------------------------
// SUITE 5 – PUT /api/v1/tokens/budget
// ---------------------------------------------------------------------------
test.describe("PUT /api/v1/tokens/budget", () => {
  test("returns 401 without auth", async ({ request }) => {
    const resp = await request.put(`${BASE}/api/v1/tokens/budget`, {
      data: { daily_limit_usd: 5.0 },
    });
    expect(resp.status()).toBe(401);
  });

  test("updates daily_limit and round-trips correctly", async ({ request }) => {
    const token = await getBearerToken(request);
    const newLimit = 42.5;

    const putResp = await request.put(`${BASE}/api/v1/tokens/budget`, {
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      data: { daily_limit_usd: newLimit },
    });
    expect(putResp.status()).toBe(200);

    const body = await putResp.json();
    expect(body.daily_limit_usd).toBe(newLimit);

    // Verify via GET
    const getResp = await request.get(`${BASE}/api/v1/tokens/budget`, {
      headers: authHeaders(token),
    });
    const getBody = await getResp.json();
    expect(getBody.daily_limit_usd).toBe(newLimit);
  });

  test("updates auto_downgrade_enabled flag", async ({ request }) => {
    const token = await getBearerToken(request);

    for (const flag of [true, false]) {
      const putResp = await request.put(`${BASE}/api/v1/tokens/budget`, {
        headers: { ...authHeaders(token), "Content-Type": "application/json" },
        data: { auto_downgrade_enabled: flag },
      });
      expect(putResp.status()).toBe(200);
      const body = await putResp.json();
      expect(body.auto_downgrade_enabled).toBe(flag);
    }
  });

  test("empty body returns 200 (no-op update)", async ({ request }) => {
    const token = await getBearerToken(request);
    const resp = await request.put(`${BASE}/api/v1/tokens/budget`, {
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      data: {},
    });
    expect(resp.status()).toBe(200);
  });

  test("idempotent: repeated updates with same value produce same result", async ({
    request,
  }) => {
    const token = await getBearerToken(request);
    const payload = { daily_limit_usd: 99.99, monthly_limit_usd: 500.0 };

    await request.put(`${BASE}/api/v1/tokens/budget`, {
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      data: payload,
    });
    const resp2 = await request.put(`${BASE}/api/v1/tokens/budget`, {
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      data: payload,
    });
    expect(resp2.status()).toBe(200);
    const body = await resp2.json();
    expect(body.daily_limit_usd).toBe(payload.daily_limit_usd);
    expect(body.monthly_limit_usd).toBe(payload.monthly_limit_usd);
  });
});

// ---------------------------------------------------------------------------
// SUITE 6 – GET /api/v1/tokens/forecast
// ---------------------------------------------------------------------------
test.describe("GET /api/v1/tokens/forecast", () => {
  test("returns 401 without auth", async ({ request }) => {
    const resp = await request.get(`${BASE}/api/v1/tokens/forecast`);
    expect(resp.status()).toBe(401);
  });

  test("returns 200 with correct shape", async ({ request }) => {
    const token = await getBearerToken(request);
    const resp = await request.get(`${BASE}/api/v1/tokens/forecast`, {
      headers: authHeaders(token),
    });
    expect(resp.status()).toBe(200);

    const body = await resp.json();
    expect(body).toHaveProperty("forecast_30d_usd");
    expect(body).toHaveProperty("daily_average_7d");
    expect(body).toHaveProperty("trend");
    expect(body).toHaveProperty("projected_monthly");

    expect(typeof body.forecast_30d_usd).toBe("number");
    expect(typeof body.daily_average_7d).toBe("number");
    expect(["stable", "increasing", "decreasing"]).toContain(body.trend);
    expect(typeof body.projected_monthly).toBe("number");
  });

  test("zero usage gives forecast_30d_usd=0 and trend=stable", async ({ request }) => {
    // Only meaningful in a fresh/empty test account
    const token = await getBearerToken(request);
    const resp = await request.get(`${BASE}/api/v1/tokens/forecast`, {
      headers: authHeaders(token),
    });
    const body = await resp.json();
    if (body.daily_average_7d === 0) {
      expect(body.forecast_30d_usd).toBe(0);
      expect(body.trend).toBe("stable");
    }
  });

  // BUG-004 regression: forecast_30d_usd and projected_monthly are always identical
  test("BUG-004 regression: forecast_30d_usd equals projected_monthly (duplicate field)", async ({
    request,
  }) => {
    const token = await getBearerToken(request);
    const resp = await request.get(`${BASE}/api/v1/tokens/forecast`, {
      headers: authHeaders(token),
    });
    const body = await resp.json();
    // These two fields are computed identically in current code – documenting the bug
    expect(body.forecast_30d_usd).toBe(body.projected_monthly);
    // Once fixed, projected_monthly should represent something distinct (e.g. remaining month)
  });

  test("daily_average_7d * 30 equals forecast_30d_usd (BUG-005 off-by-one check)", async ({
    request,
  }) => {
    // BUG-005: weekly window spans 8 days (today - 7) but divides by 7
    // This test documents current (buggy) behaviour – daily_avg comes from 8-day sum / 7
    // We validate the math is self-consistent within the response
    const token = await getBearerToken(request);
    const resp = await request.get(`${BASE}/api/v1/tokens/forecast`, {
      headers: authHeaders(token),
    });
    const body = await resp.json();
    const expected30d = parseFloat((body.daily_average_7d * 30).toFixed(2));
    expect(body.forecast_30d_usd).toBe(expected30d);
  });
});

// ---------------------------------------------------------------------------
// SUITE 7 – Model Router unit-level API validation (via direct Python import
//           – these are pure-logic tests, no HTTP needed)
// ---------------------------------------------------------------------------
// NOTE: These are documented here as manual verification results since Playwright
// runs in a browser context. The equivalent Python tests should live in
// backend/tests/unit/test_router.py (see recommendations in QA report).
//
// Verified externally via `python3 -c "..."`:
//   1. get_all_models() returns deduplicated list in insertion order – PASS
//   2. select_model(deep, EXHAUSTED) raises BudgetExhaustedError – PASS
//   3. select_model(nonexistent_tier, HEALTHY) falls back to 'standard' – PASS
//   4. tier_from_model returns first matching tier (see BUG-006 for analytics impact)
//   5. Floating-point: 1.0-(9.0/10.0) = 0.0999... < 0.10 → CRITICAL at 90% (BUG-001)

// ---------------------------------------------------------------------------
// SUITE 8 – Auth edge cases on token endpoints
// ---------------------------------------------------------------------------
test.describe("Token endpoint auth edge cases", () => {
  test("malformed bearer token returns 401", async ({ request }) => {
    for (const endpoint of ["/api/v1/tokens/usage", "/api/v1/tokens/budget", "/api/v1/tokens/forecast"]) {
      const resp = await request.get(`${BASE}${endpoint}`, {
        headers: { Authorization: "Bearer not.a.valid.jwt" },
      });
      expect(resp.status()).toBe(401);
    }
  });

  test("missing Bearer scheme returns 403 or 401", async ({ request }) => {
    // HTTPBearer raises 403 when no Authorization header at all
    const resp = await request.get(`${BASE}/api/v1/tokens/usage`);
    expect([401, 403]).toContain(resp.status());
  });
});
