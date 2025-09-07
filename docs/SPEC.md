# arpx – Specyfikacja i szczegóły implementacji

## Architektura

- `src/arpx/network.py` – Zarządzanie aliasami IP i widocznością w LAN
  - Wykorzystuje `ip addr add/del`, `arping`, `ip neigh`, `arp` (net-tools), opcjonalnie `iptables`.
  - Logowanie przez `logging` (`arpx.network`).
- `src/arpx/server.py` – Lekki serwer HTTP/HTTPS na konkretnym IP
  - Klasa `LANWebServerManager` zarządza cyklem życia serwerów.
  - Obsługuje HTTPS przez podany `ssl.SSLContext`.
  - Logowanie przez `logging` (`arpx.server`).
- `src/arpx/certs.py` – Generowanie certyfikatów
  - Self‑signed (cryptography), mkcert, Let's Encrypt (certbot standalone).
  - `build_ssl_context()` tworzy kontekst TLS.
  - Logowanie przez `logging` (`arpx.certs`).
- `src/arpx/dns.py` – Sugestie konfiguracji lokalnych domen (dnsmasq/hosts)
- `src/arpx/compose.py` – Parser `docker-compose.yml` (opcjonalna zależność `PyYAML`)
  - Wydobywa opublikowane porty TCP dla usług.
- `src/arpx/proxy.py` – Prosty TCP forwarder (alias_ip:host_port → 127.0.0.1:host_port)
- `src/arpx/terminator.py` – TLS terminator: przyjmuje HTTPS na aliasie i przekazuje HTTP do usługi
- `src/arpx/bridge.py` – "Bridge" Compose → LAN IP aliasy + forwardery + (opcjonalnie) terminator TLS
  - Dla każdej usługi z publikowanymi portami TCP:
    - Tworzy alias IP (widoczny via ARP) na interfejsie.
    - Dodaje reguły iptables (jeśli dostępne).
    - Uruchamia TCP forwarder.
- `src/arpx/cli.py` – Główny CLI
  - `arpx up` – klasyczny tryb multi‑IP z wbudowanym serwerem.
  - `arpx cert` – narzędzia certów.
  - `arpx dns` – podpowiedzi domen.
  - `arpx compose` – bridge usług (Docker/Podman Compose) do LAN.

## Przepływy

- Up (HTTP/HTTPS):
  1. Weryfikacja roota, detekcja interfejsu.
  2. Pobranie parametrów sieci (IP/CIDR, sieć, broadcast).
  3. Wybór wolnych IP (ping + arping) lub inkrementacja z `--base-ip`.
  4. Dodanie aliasów `ip addr add`, włączenie proxy_arp, ogłoszenie ARP.
  5. Konfiguracja iptables (jeśli dostępne), start serwerów HTTP/HTTPS.
  6. Test GET, re‑announce ARP, pętla odświeżania ARP.

- Certyfikaty:
  - Self‑signed: cryptography + SAN (domeny i/lub IP).
  - mkcert: wymaga `mkcert` + lokalna CA.
  - Let’s Encrypt: `certbot certonly --standalone` (wymaga wolnego 80/TCP, DNS → host).

- Compose bridge:
  1. Parsowanie `docker-compose.yml` → lista usług i portów TCP (published/host).
  2. Przydział aliasów IP (auto lub z `--base-ip`).
  3. Dla każdego host_port: iptables ACCEPT oraz forwarder alias_ip:host_port → 127.0.0.1:host_port.
  4. (Opcja) Terminator HTTPS na aliasie (domyślnie port 443) → HTTP do pierwszego opublikowanego portu.
  4. Sprzątanie: zamknięcie forwarderów, usunięcie aliasów IP.

## Bezpieczeństwo i uwagi

- Wymagany root; modyfikacje tablic routingu/ARP i iptables mogą mieć wpływ na hosta.
- Forwardery TCP nie terminują TLS – to pasywne przekazywanie strumienia.
- Let’s Encrypt wymaga poprawnych rekordów DNS i dostępu na 80/TCP.
- mkcert instaluje lokalną CA – sprawdź politykę bezpieczeństwa w środowisku.
- Zależności systemowe: `ip`, `arping` (iputils-arping), `arp` (net-tools), `iptables` (opcjonalnie).

## Rozszerzenia (backlog)

- Integracja mDNS (Zeroconf) do automatycznej publikacji nazw.
- Monitorowanie konfliktów IP / wykrywanie DHCP.
- Integracja z `nftables`.
- Tryb reverse‑proxy (HTTP) z nagłówkami X‑Forwarded‑For.
- Integracja z Caddy/Traefik jako opcja dla HTTPS.
