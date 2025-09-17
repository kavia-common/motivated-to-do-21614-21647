#!/bin/bash
cd /home/kavia/workspace/code-generation/motivated-to-do-21614-21647/todo_backend_fastapi
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

