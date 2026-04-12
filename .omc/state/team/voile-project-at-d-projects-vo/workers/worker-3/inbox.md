## REQUIRED: Task Lifecycle Commands
You MUST run these commands. Do NOT skip any step.

1. Claim your task:
   omc team api claim-task --input '{"team_name":"voile-project-at-d-projects-vo","task_id":"3","worker":"worker-3"}' --json
   Save the claim_token from the response.
2. Do the work described below.
3. On completion (use claim_token from step 1):
   omc team api transition-task-status --input '{"team_name":"voile-project-at-d-projects-vo","task_id":"3","from":"in_progress","to":"completed","claim_token":"<claim_token>"}' --json
4. On failure (use claim_token from step 1):
   omc team api transition-task-status --input '{"team_name":"voile-project-at-d-projects-vo","task_id":"3","from":"in_progress","to":"failed","claim_token":"<claim_token>"}' --json
5. ACK/progress replies are not a stop signal. Keep executing your assigned or next feasible work until the task is actually complete or failed, then transition and exit.

## Task Assignment
Task ID: 3
Worker: worker-3
Subject: confirm all pass before finishing. All workers: cd D:/projects/voile first. Run 

confirm all pass before finishing. All workers: cd D:/projects/voile first. Run pytest tests/ -q at the end

REMINDER: You MUST run transition-task-status before exiting. Do NOT write done.json or edit task files directly.