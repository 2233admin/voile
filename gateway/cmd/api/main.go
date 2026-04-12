// XAR-10: Unified message API gateway (REST) for Python analysis layer
package main

import (
	"flag"
	"log/slog"
	"net/http"
	"os"
)

func main() {
	addr := flag.String("addr", ":8080", "Listen address")
	flag.Parse()

	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))

	mux := http.NewServeMux()
	mux.HandleFunc("/ingest/qq", func(w http.ResponseWriter, r *http.Request) {
		// TODO XAR-10: validate, normalize, write to DB, push URL to Redis
		w.WriteHeader(http.StatusAccepted)
	})
	mux.HandleFunc("/ingest/wechat", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusAccepted)
	})
	mux.HandleFunc("/messages/history", func(w http.ResponseWriter, r *http.Request) {
		// TODO: query DB and return JSON
		w.WriteHeader(http.StatusOK)
	})

	logger.Info("api gateway listening", "addr", *addr)
	if err := http.ListenAndServe(*addr, mux); err != nil {
		logger.Error("server error", "err", err)
		os.Exit(1)
	}
}
