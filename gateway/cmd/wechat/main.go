// XAR-9: WeChat quasi-realtime sync via WeFlow HTTP API
package main

import (
	"context"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"time"

	"github.com/redis/go-redis/v9"
)

func main() {
	weflow := flag.String("weflow", "http://127.0.0.1:5030", "WeFlow API base URL")
	interval := flag.Duration("interval", 10*time.Second, "Poll interval")
	flag.Parse()

	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))
	logger.Info("wechat sync starting", "weflow", *weflow, "interval", *interval)

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

	lastTS := time.Now().Add(-24 * time.Hour).Unix()
	ticker := time.NewTicker(*interval)
	defer ticker.Stop()

	for range ticker.C {
		url := fmt.Sprintf("%s/api/messages?since=%d", *weflow, lastTS)
		resp, err := http.Get(url)
		if err != nil {
			logger.Warn("poll failed", "err", err)
			continue
		}
		body, err := io.ReadAll(resp.Body)
		resp.Body.Close()
		if err != nil {
			logger.Warn("read body failed", "err", err)
			continue
		}
		rdb.LPush(context.Background(), "voile:raw_queue", body)
		lastTS = time.Now().Unix()
	}
}
