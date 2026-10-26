#!/bin/sh
# Bounded known regular files only. Print counters, never log lines or ASR text.
set -u
for f in /var/log/messages /data/quasar/daemons_logs/maind.log /data/quasar/daemons_logs/yiod.log /data/quasar/daemons_logs/mediad.log; do
    if [ -f "$f" ] && [ ! -L "$f" ]; then
        printf '%s bytes=' "$f"; wc -c < "$f"
        printf 'asr_like_lines_last_64KiB='
        tail -c 65536 "$f" | grep -icE 'recogniz|recognis|transcript|asr|utterance' || :
        printf 'final_like_lines_last_64KiB='
        tail -c 65536 "$f" | grep -icE 'final.*(recogn|asr|text)|(recogn|asr).*final' || :
    fi
done
# Legacy adbd may not propagate stdin EOF to the child shell.
exit 0
