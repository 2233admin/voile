## REQUIRED: Task Lifecycle Commands
You MUST run these commands. Do NOT skip any step.

1. Claim your task:
   omc team api claim-task --input '{"team_name":"voile-project-at-d-projects-vo","task_id":"2","worker":"worker-2"}' --json
   Save the claim_token from the response.
2. Do the work described below.
3. On completion (use claim_token from step 1):
   omc team api transition-task-status --input '{"team_name":"voile-project-at-d-projects-vo","task_id":"2","from":"in_progress","to":"completed","claim_token":"<claim_token>"}' --json
4. On failure (use claim_token from step 1):
   omc team api transition-task-status --input '{"team_name":"voile-project-at-d-projects-vo","task_id":"2","from":"in_progress","to":"failed","claim_token":"<claim_token>"}' --json
5. ACK/progress replies are not a stop signal. Keep executing your assigned or next feasible work until the task is actually complete or failed, then transition and exit.

## Task Assignment
Task ID: 2
Worker: worker-2
Subject: does not touch the others' files. Coordinate via mailbox to avoid overlap. TASK-

does not touch the others' files. Coordinate via mailbox to avoid overlap. TASK-1 (core/ingest/consumer.py): Add WeChat/WeFlow format parsing. WeFlow pushes JSON arrays of messages. Each message has fields: id, from_user, to_user, content, create_time, msg_type (text/image/voice/video/link). Add _parse_wechat(event, cleaner_fn) -> Message|None alongside _parse_onebot. Handle the WeFlow array batch in _handle(). Add tests in tests/test_consumer.py. TASK-2 (core/health.py + run.py): Add a lightweight HTTP health endpoint. Create core/health.py that starts a plain http.server on port 8765 (env VOILE_HEALTH_PORT). Returns JSON: {status: ok, workers: {consumer: bool, sentiment: bool, topic: bool, links: bool}, uptime_s: float}. Wire into run.py as a 5th daemon thread. Add tests in tests/test_health.py. TASK-3 (tests/test_query.py): Write pytest unit tests for every function in core/query.py (recent_messages, topic_summary, sentiment_summary, archived_links, find_decisions, channel_stats, list_channels). Use in-memory SQLite (sqlite:///:memory:). Seed test data directly via SQLAlchemy. Target: 90%+ coverage of core/query.py. Run pytest tests/test_query.py

REMINDER: You MUST run transition-task-status before exiting. Do NOT write done.json or edit task files directly.