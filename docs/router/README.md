# Router DNS (dnsmasq/OpenWrt) samples for ARPx

This directory contains ready-to-use snippets for configuring local domains on routers
running dnsmasq (e.g., OpenWrt) so that your ARPx alias IPs resolve for all devices in the LAN.

Files:

- `dnsmasq.conf.example` – minimal dnsmasq configuration lines to map a domain to an IP.
- `hosts.example` – an `/etc/hosts` style entry for quick local testing on a client.
- `openwrt-uci.sh` – an example OpenWrt UCI script to add host-record mappings.

## Quick start (OpenWrt LuCI)

1. SSH to the router or use the LuCI web UI.
2. Go to Network → DHCP and DNS → "Additional settings" / "Add".
3. Insert lines from `dnsmasq.conf.example` and apply settings.
4. Restart dnsmasq or reboot the router.

## Quick start (UCI on OpenWrt)

Copy and modify `openwrt-uci.sh` with your domain and IP, then run:

```sh
sh openwrt-uci.sh
/etc/init.d/dnsmasq restart
```

Ensure your clients use the router as DNS (default in most LANs). Then `https://myapp.lan/`
should resolve to your ARPx alias IP.
