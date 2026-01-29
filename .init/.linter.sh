#!/bin/bash
cd /home/kavia/workspace/code-generation/unified-marketplace-platform-312081-312092/backend_expressjs
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

