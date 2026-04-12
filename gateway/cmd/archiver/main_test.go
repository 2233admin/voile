package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// --- fetchURL tests ---

func TestFetchURL_ExtractsTitle(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html")
		w.Write([]byte(`<html><head><title>Hello World</title></head><body>Test content here</body></html>`))
	}))
	defer srv.Close()

	result := fetchURL(srv.URL)

	if result.Error != "" {
		t.Fatalf("unexpected error: %s", result.Error)
	}
	if result.Title != "Hello World" {
		t.Errorf("want title %q, got %q", "Hello World", result.Title)
	}
	if result.FetchedAt == "" {
		t.Error("FetchedAt should be set")
	}
	if !strings.Contains(result.Summary, "Test content here") {
		t.Errorf("summary should contain page text, got %q", result.Summary)
	}
}

func TestFetchURL_TitleWhitespaceTrimmed(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("<html><head><title>  Padded Title  </title></head></html>"))
	}))
	defer srv.Close()

	result := fetchURL(srv.URL)
	if result.Title != "Padded Title" {
		t.Errorf("title should be trimmed, got %q", result.Title)
	}
}

func TestFetchURL_Non200ReturnsError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	defer srv.Close()

	result := fetchURL(srv.URL)
	if result.Error == "" {
		t.Error("expected error for 404 response")
	}
}

func TestFetchURL_InvalidURLReturnsError(t *testing.T) {
	result := fetchURL("not-a-url")
	if result.Error == "" {
		t.Error("expected error for invalid URL")
	}
	if result.URL != "not-a-url" {
		t.Errorf("URL field should echo input, got %q", result.URL)
	}
}

func TestFetchURL_TagsStrippedFromSummary(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`<html><body><p>visible text</p><script>var x=1;</script></body></html>`))
	}))
	defer srv.Close()

	result := fetchURL(srv.URL)
	if strings.Contains(result.Summary, "<p>") || strings.Contains(result.Summary, "<script>") {
		t.Errorf("HTML tags should be stripped from summary, got %q", result.Summary)
	}
	if !strings.Contains(result.Summary, "visible text") {
		t.Errorf("text content should be preserved, got %q", result.Summary)
	}
}

func TestFetchURL_SummaryTruncatedAtMaxLen(t *testing.T) {
	// Build a page whose stripped text exceeds maxSummaryLen
	repeated := strings.Repeat("word ", maxSummaryLen/5+200)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("<html><body>" + repeated + "</body></html>"))
	}))
	defer srv.Close()

	result := fetchURL(srv.URL)
	if len(result.Summary) > maxSummaryLen {
		t.Errorf("summary too long: %d > %d", len(result.Summary), maxSummaryLen)
	}
}

func TestFetchURL_UserAgentSent(t *testing.T) {
	var gotUA string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotUA = r.Header.Get("User-Agent")
	}))
	defer srv.Close()

	fetchURL(srv.URL)
	if gotUA != userAgent {
		t.Errorf("want User-Agent %q, got %q", userAgent, gotUA)
	}
}

// --- handleFetch tests ---

func TestHandleFetch_MethodNotAllowed(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/fetch", nil)
	w := httptest.NewRecorder()
	handleFetch(w, req)
	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("want 405, got %d", w.Code)
	}
}

func TestHandleFetch_EmptyURL(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/fetch", strings.NewReader(`{"url":""}`))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	handleFetch(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("want 400, got %d", w.Code)
	}
	var resp FetchResponse
	json.NewDecoder(w.Body).Decode(&resp)
	if resp.Error == "" {
		t.Error("expected error field in response")
	}
}

func TestHandleFetch_MalformedJSON(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/fetch", strings.NewReader(`{bad json`))
	w := httptest.NewRecorder()
	handleFetch(w, req)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("want 400, got %d", w.Code)
	}
}

func TestHandleFetch_ValidRequest(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`<html><head><title>Voile Test</title></head><body>content</body></html>`))
	}))
	defer upstream.Close()

	body := strings.NewReader(`{"url":"` + upstream.URL + `"}`)
	req := httptest.NewRequest(http.MethodPost, "/fetch", body)
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	handleFetch(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("want 200, got %d", w.Code)
	}
	var resp FetchResponse
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("decode failed: %v", err)
	}
	if resp.Title != "Voile Test" {
		t.Errorf("want title %q, got %q", "Voile Test", resp.Title)
	}
	if resp.Error != "" {
		t.Errorf("unexpected error: %s", resp.Error)
	}
	if w.Header().Get("Content-Type") != "application/json" {
		t.Error("response Content-Type should be application/json")
	}
}
