#!/bin/bash
# Apply iptables rules to block specific IPs
iptables-legacy -A OUTPUT -d 150.229.22.40 -j REJECT
iptables-legacy -A OUTPUT -d 202.9.9.2 -j REJECT

# Start the main process (whatever the container needs to run)
exec "$@"