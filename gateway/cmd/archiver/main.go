// XAR-11: Link fetch and metadata extraction service
package main

import (
	"encoding/json"
	"flag"
	"io"
	"log/slog"
	"net/http"
	"os"
	"regexp"
	"strings"
	"time"
)

const (
	maxBodyBytes  = 512 * 1024 // 512 KB
	maxSummaryLen = 8000
	fetchTimeout  = 15 * time.Second
	userAgent     = "Voile/0.1"
)

var (
	reTag   = regexp.MustCompile(`<[^>]+>`)
	reTitle = regexp.MustCompile(`(?i)<title[^>]*>([\s\S]*?)</title>`)
)

type FetchRequest struct {
	URL string `json:"url"`
}

type FetchResponse struct {
	URL       string `json:"url"`
	Title     string `json:"title,omitempty"`
	Summary   string `json:"summary,omitempty"`
	FetchedAt string `json:"fetched_at,omitempty"`
	Error     string `json:"error,omitempty"`
}

func fetchURL(rawURL string) FetchResponse {
	client := &http.Client{Timeout: fetchTimeout}
	req, err := http.NewRequest(http.MethodGet, rawURL, nil)
	if err != nil {
		return FetchResponse{URL: rawURL, Error: err.Error()}
	}
	req.Header.Set("User-Agent", userAgent)

	resp, err := client.Do(req)
	if err != nil {
		return FetchResponse{URL: rawURL, Error: err.Error()}
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return FetchResponse{URL: rawURL, Error: http.StatusText(resp.StatusCode)}
	}

	limited := io.LimitReader(resp.Body, maxBodyBytes)
	body, err := io.ReadAll(limited)
	if err != nil {
		return FetchResponse{URL: rawURL, Error: err.Error()}
	}

	html := string(body)

	// extract title
	var title string
	if m := reTitle.FindStringSubmatch(html); len(m) == 2 {
		title = strings.TrimSpace(m[1])
	}

	// strip tags, collapse whitespace, truncate
	text := reTag.ReplaceAllString(html, " ")
	// collapse runs of whitespace
	fields := strings.Fields(text)
	text = strings.Join(fields, " ")
	if len(text) > maxSummaryLen {
		text = text[:maxSummaryLen]
	}

	return FetchResponse{
		URL:       rawURL,
		Title:     title,
		Summary:   text,
		FetchedAt: time.Now().UTC().Format(time.RFC3339),
	}
}

func handleFetch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req FetchRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.URL == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(FetchResponse{Error: "invalid request"})
		return
	}

	result := fetchURL(req.URL)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}

func main() {
	addr := flag.String("addr", ":8888", "Listen address")
	flag.Parse()

	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))

	mux := http.NewServeMux()
	mux.HandleFunc("/fetch", handleFetch)

	logger.Info("archiver listening", "addr", *addr)
	if err := http.ListenAndServe(*addr, mux); err != nil {
		logger.Error("server error", "err", err)
		os.Exit(1)
	}
}
