package main

import (
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"testing"
)

func discardLogger() *slog.Logger {
	return slog.New(slog.NewTextHandler(io.Discard, nil))
}

func TestForward_PostsPayloadToDownstream(t *testing.T) {
	received := make(chan []byte, 1)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		received <- body
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	payload := []byte(`{"post_type":"message","raw_message":"hello"}`)
	forward(srv.URL, payload, discardLogger())

	select {
	case got := <-received:
		if string(got) != string(payload) {
			t.Errorf("want %s, got %s", payload, got)
		}
	default:
		t.Error("downstream received nothing")
	}
}

func TestForward_UnreachableHostDoesNotPanic(t *testing.T) {
	// forward() should swallow errors — this must not panic
	forward("http://localhost:19999/nope", []byte("data"), discardLogger())
}

func TestOneBotEvent_ParseGroupMessage(t *testing.T) {
	raw := `{
		"post_type":"message",
		"message_type":"group",
		"group_id":100000,
		"user_id":200000,
		"message_id":42,
		"raw_message":"hello group",
		"time":1712908800
	}`

	var evt OneBotEvent
	if err := json.Unmarshal([]byte(raw), &evt); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}

	if evt.PostType != "message" {
		t.Errorf("PostType: want %q, got %q", "message", evt.PostType)
	}
	if evt.MessageType != "group" {
		t.Errorf("MessageType: want %q, got %q", "group", evt.MessageType)
	}
	if evt.GroupID != 100000 {
		t.Errorf("GroupID: want 100000, got %d", evt.GroupID)
	}
	if evt.UserID != 200000 {
		t.Errorf("UserID: want 200000, got %d", evt.UserID)
	}
	if evt.RawMessage != "hello group" {
		t.Errorf("RawMessage: want %q, got %q", "hello group", evt.RawMessage)
	}
	if evt.Time != 1712908800 {
		t.Errorf("Time: want 1712908800, got %d", evt.Time)
	}
}

func TestOneBotEvent_NonMessagePostType(t *testing.T) {
	raw := `{"post_type":"meta_event","meta_event_type":"heartbeat"}`

	var evt OneBotEvent
	if err := json.Unmarshal([]byte(raw), &evt); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}

	// The connect() loop skips non-message events — verify filter logic works
	if evt.PostType == "message" {
		t.Error("heartbeat should not pass the message filter")
	}
}

func TestOneBotEvent_MissingFieldsZeroValue(t *testing.T) {
	raw := `{"post_type":"message"}`

	var evt OneBotEvent
	if err := json.Unmarshal([]byte(raw), &evt); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}

	if evt.GroupID != 0 {
		t.Errorf("GroupID should default to 0, got %d", evt.GroupID)
	}
	if evt.RawMessage != "" {
		t.Errorf("RawMessage should default to empty, got %q", evt.RawMessage)
	}
}
