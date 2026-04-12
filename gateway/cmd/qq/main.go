// XAR-8: QQ realtime message gateway via NapCatQQ OneBot v11 WebSocket
package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"log/slog"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"time"

	"github.com/gorilla/websocket"
)

type OneBotEvent struct {
	PostType    string          `json:"post_type"`
	MessageType string          `json:"message_type"`
	GroupID     int64           `json:"group_id"`
	UserID      int64           `json:"user_id"`
	MessageID   int64           `json:"message_id"`
	Message     json.RawMessage `json:"message"`
	RawMessage  string          `json:"raw_message"`
	Time        int64           `json:"time"`
}

func main() {
	napcat := flag.String("onebot-ws", "ws://127.0.0.1:3001", "OneBot v11 WS endpoint (NapCat/Lagrange)")
	downstream := flag.String("downstream", "http://127.0.0.1:8080/ingest/qq", "Ingest API endpoint")
	flag.Parse()

	if v := os.Getenv("ONEBOT_WS"); v != "" {
		*napcat = v
	}
	if v := os.Getenv("DOWNSTREAM"); v != "" {
		*downstream = v
	}

	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))

	u, _ := url.Parse(*napcat)
	logger.Info("connecting", "endpoint", u.String())

	for {
		if err := connect(u.String(), *downstream, logger); err != nil {
			logger.Error("disconnected", "err", err, "retry_in", "5s")
			time.Sleep(5 * time.Second)
		}
	}
}

func forward(downstream string, body []byte, logger *slog.Logger) {
	resp, err := http.Post(downstream, "application/json", bytes.NewReader(body))
	if err != nil {
		logger.Warn("forward failed", "err", err)
		return
	}
	resp.Body.Close()
}

func connect(endpoint, downstream string, logger *slog.Logger) error {
	conn, _, err := websocket.DefaultDialer.Dial(endpoint, nil)
	if err != nil {
		return err
	}
	defer conn.Close()

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt)

	logger.Info("connected to NapCatQQ")

	for {
		select {
		case <-sig:
			return nil
		default:
		}

		_, raw, err := conn.ReadMessage()
		if err != nil {
			return err
		}

		var evt OneBotEvent
		if err := json.Unmarshal(raw, &evt); err != nil {
			logger.Warn("parse error", "err", err)
			continue
		}

		if evt.PostType != "message" {
			continue
		}

		logger.Debug("received", "type", evt.MessageType, "user", evt.UserID, "msg", evt.RawMessage)
		forward(downstream, raw, logger)
	}
}
