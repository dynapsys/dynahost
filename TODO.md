# TODO – arpx

- [x] Packaging with uv + pyproject.toml (hatchling, dynamic version)
- [x] CLI entrypoint `arpx` with commands: `up`, `cert`, `dns`, `compose`
- [x] HTTPS support (self-signed, mkcert, Let's Encrypt, custom)
- [x] Logging: switch internals to `logging` with namespaced loggers
- [x] Compose bridge: alias IPs + forwarders for published TCP ports
- [x] README with badges and onboarding for DevOps and juniors
- [x] CHANGELOG.md, docs/SPEC.md
- [x] Examples for CLI, API, Docker, Podman
- [ ] Add `arpx compose down` to remove alias IPs without Ctrl+C loop
- [ ] Optional mDNS (zeroconf) for local name broadcasting
- [ ] Detect and avoid DHCP ranges more robustly (parse DHCP leases if available)
- [ ] nftables backend alternative to iptables
- [ ] Systemd units to run `arpx up`/`arpx compose` as services
- [ ] CI workflows (GitHub Actions) and badges
- [ ] More unit tests and a safe e2e harness with containers in CI (rootless?)
- [ ] Zmienić nazwę z arpx na krótszą 4-literową, znaleźć wolną nazwę robiąc request bezpośrednio do pypi, a jeśli nie znajdziesz to użyj: multip lub extip lub coś lepszego ale krótkiego
- [ ] Dodać przykładowe pliki konfiguracyjne dnsmasq/OpenWrt
- [ ] Podpiąć opcjonalnie mDNS (zeroconf) do broadcastu nazw w sieci
- [ ] Rozwinąć Makefile o targets stricte dla tego repo (usuwając stare „dynadock-…”)
- [ ] Wyjaśnić na jakiej zasadzie działa ta paczka, rozrysować strukturę i architekturę, aby było możliwe zrozumienie jak działa i jak pojawiają się nowe numery IP dostępne w lokalnej sieci
- [ ] Opisać konkretne rozwiązania jakie niesie to ze sobą, stworzyć listę 10 z konkretnymi przykładami komend
wyjasnij na jakiej zasadzie dizala ta paczka, rozrysuj strukture i architekture, aby bylo mozna zrozumiec jak dziala i jak pojawiaja sie nowe numery IP dodstepne w lokalnej sieci

opisz tez konrketne rozwizania jakie niesie to ze soba, stworz liste 10 z konrkentymi przykaldami komend

usun niepotrzebne pliki  lub zduplikowane funkcje, zrefaktoryzuj jesli jest potrzebne

wyjasnij na jakiej zasadzie dizala ta paczka, rozrysuj strukture i architekture, aby bylo mozna zrozumiec jak dziala i jak pojawiaja sie nowe numery IP dodstepne w lokalnej sieci

opisz tez konrketne rozwizania jakie niesie to ze soba, stworz liste 10 z konrkentymi przykaldami komend