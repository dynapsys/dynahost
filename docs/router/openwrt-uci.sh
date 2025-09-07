#!/bin/sh
# Example OpenWrt UCI script to add a local DNS A record via dnsmasq
# Usage: sh openwrt-uci.sh myapp.lan 192.168.1.200

DOMAIN="$1"
IP="$2"

if [ -z "$DOMAIN" ] || [ -z "$IP" ]; then
  echo "Usage: $0 <domain> <ip>"
  exit 1
fi

# Add or update host-record entry
uci add dhcp domain >/dev/null 2>&1 || true
INDEX=$(uci show dhcp | grep '=domain' | tail -n1 | cut -d. -f2)
uci set dhcp.@domain[$INDEX].name="$DOMAIN"
uci set dhcp.@domain[$INDEX].ip="$IP"
uci commit dhcp

/etc/init.d/dnsmasq restart

echo "Added dnsmasq host-record: $DOMAIN -> $IP"
