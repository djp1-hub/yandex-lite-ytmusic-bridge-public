#!/bin/sh
# Run through adb shell sh < this-file. No installs, writes or IPC connections.
# Metadata only; never read cmdline/environ, configs, audio or process memory.
set -u
printf 'kernel_machine='; uname -m
for f in /bin/busybox /system/vendor/quasar/maind; do
    printf '%s ELF identification=' "$f"
    od -An -t u1 -N 5 "$f"
done
for p in /proc/[0-9]*; do
    case "$(cat "$p/comm" 2>/dev/null)" in
        maind|quasar_launcher*)
            printf '%s comm=' "$p"; cat "$p/comm"
            printf 'stdout='; readlink "$p/fd/1"
            printf 'stderr='; readlink "$p/fd/2"
            ;;
    esac
done
printf 'root mount:\n'
awk '$2 == "/" {print $1, $2, $3, $4}' /proc/mounts
printf 'known log locations:\n'
ls -ld /var/log /data/quasar/daemons_logs 2>/dev/null
# Legacy adbd may not propagate stdin EOF to the child shell.
exit 0
