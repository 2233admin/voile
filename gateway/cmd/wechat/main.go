// XAR-9: WeChat quasi-realtime sync via WeFlow HTTP API
package main

import (
	"flag"
	"log/slog"
	"os"
	"time"
)

func main() {
	weflow := flag.String("weflow", "http://127.0.0.1:5030", "WeFlow API base URL")
	interval := flag.Duration("interval", 10*time.Second, "Poll interval")
	flag.Parse()

	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))
	logger.Info("wechat sync starting", "weflow", *weflow, "interval", *interval)

	// TODO XAR-9: implement WeFlow polling + last_sync_at checkpoint
	_ = weflow
	_ = interval
}
