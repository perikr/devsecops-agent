#!/bin/sh
# Run one agent turn locally via OpenClaw (no gateway needed).
cd "$(dirname "$0")" && openclaw agent --message-file TASK.md --timeout 580  # uses the running Gateway; add --local if none
