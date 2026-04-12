// XAR-10: Unified message API gateway (REST) for Python analysis layer
package main

import (
	"flag"
	"io"
	"log/slog"
	"net/http"
	"os"

	"github.com/redis/go-redis/v9"
)

func makeIngestHandler(rdb *redis.Client, platform string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			w.WriteHeader(500)
			return
		}
		ctx := r.Context()
		rdb.LPush(ctx, "voile:raw_queue", body)
		w.WriteHeader(202)
	}
}

func main() {
	addr := flag.String("addr", ":8080", "Listen address")
	flag.Parse()

	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))

	redisURL := os.Getenv("VOILE_REDIS_URL")
	if redisURL == "" {
		redisURL = "redis://localhost:6379/0"
	}
	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		logger.Error("invalid redis URL", "err", err)
		os.Exit(1)
	}
	rdb := redis.NewClient(opt)

	mux := http.NewServeMux()
	mux.HandleFunc("/ingest/qq", makeIngestHandler(rdb, "qq"))
	mux.HandleFunc("/ingest/wechat", makeIngestHandler(rdb, "wechat"))
	mux.HandleFunc("/messages/history", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("[]"))
	})

	logger.Info("api gateway listening", "addr", *addr)
	if err := http.ListenAndServe(*addr, mux); err != nil {
		logger.Error("server error", "err", err)
		os.Exit(1)
	}
}
