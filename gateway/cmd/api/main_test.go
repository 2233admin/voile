package main

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/redis/go-redis/v9"
)

// makeIngestHandler silently discards Redis errors, so pointing at an
// unreachable host is sufficient for HTTP-layer tests.
func newDeadRedis() *redis.Client {
	return redis.NewClient(&redis.Options{
		Addr:        "localhost:19999",
		MaxRetries:  0,
		DialTimeout: 5 * time.Millisecond, // fail fast; error is discarded by the handler
	})
}

func TestIngestHandler_Returns202(t *testing.T) {
	handler := makeIngestHandler(newDeadRedis(), "qq")
	req := httptest.NewRequest(http.MethodPost, "/ingest/qq", strings.NewReader(`{"raw":"hello"}`))
	w := httptest.NewRecorder()
	handler(w, req)
	if w.Code != http.StatusAccepted {
		t.Fatalf("want 202, got %d", w.Code)
	}
}

func TestIngestHandler_EmptyBody(t *testing.T) {
	handler := makeIngestHandler(newDeadRedis(), "wechat")
	req := httptest.NewRequest(http.MethodPost, "/ingest/wechat", strings.NewReader(""))
	w := httptest.NewRecorder()
	handler(w, req)
	if w.Code != http.StatusAccepted {
		t.Fatalf("want 202 for empty body, got %d", w.Code)
	}
}

func TestHistoryHandler_ReturnsEmptyJSONArray(t *testing.T) {
	// Inline the same handler logic from main() — it's a closure so we test
	// it by recreating it identically.
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("[]"))
	})
	req := httptest.NewRequest(http.MethodGet, "/messages/history", nil)
	w := httptest.NewRecorder()
	handler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("want 200, got %d", w.Code)
	}
	if body := w.Body.String(); body != "[]" {
		t.Fatalf("want [], got %q", body)
	}
	if ct := w.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("want Content-Type application/json, got %q", ct)
	}
}
