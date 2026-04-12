// XAR-8: QQ realtime message gateway via NapCatQQ OneBot v11 WebSocket
package main

import (
	"encoding/json"
	"flag"
	"log/slog"
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
	napcat := flag.String("napcat", "ws://127.0.0.1:3001", "NapCatQQ OneBot v11 WS endpoint")
	downstream := flag.String("downstream", "http://127.0.0.1:8080/ingest/qq", "Python ingest API")
	flag.Parse()

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

		// TODO: forward to Python ingest API (downstream)
		// forward(downstream, evt, raw)
		logger.Debug("received", "type", evt.MessageType, "user", evt.UserID, "msg", evt.RawMessage)
		_ = downstream
	}
}
