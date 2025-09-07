# Przykłady użycia HTTPS i TLS z arpx

Ten katalog demonstruje, jak używać `arpx` do serwowania treści przez HTTPS przy użyciu różnych metod zarządzania certyfikatami.

## Wymagania wstępne

- Linux z uprawnieniami `sudo`.
- `arpx` zainstalowany i poprawnie skonfigurowany dla `sudo`. Jeśli nie, uruchom `make install` z głównego katalogu repozytorium.
- `mkcert` zainstalowany dla przykładu z `mkcert`.

---

## 1. Serwery HTTPS z `arpx up`

Ta komenda tworzy wirtualne adresy IP i uruchamia na nich serwery HTTPS.

### a) Certyfikat samopodpisany (Self-Signed)

Najszybszy sposób na uruchomienie HTTPS do testów lokalnych. Przeglądarka wyświetli ostrzeżenie o bezpieczeństwie.

```bash
# Uruchom 2 serwery HTTPS z certyfikatem samopodpisanym
# Certyfikat będzie ważny dla 'myapp.lan' i automatycznie przydzielonych adresów IP.
sudo arpx up -n 2 --https self-signed --domains myapp.lan
```

### b) Użycie `mkcert` (zalecane do developmentu)

Jeśli `mkcert` jest zainstalowany, a jego główny certyfikat (CA) jest zaufany w systemie, przeglądarka nie wyświetli ostrzeżeń.

```bash
# Uruchom 2 serwery HTTPS z certyfikatem od mkcert
sudo arpx up -n 2 --https mkcert --domains dev.app.lan
```

### c) Użycie własnego certyfikatu

Jeśli posiadasz własne pliki certyfikatu i klucza.

```bash
# Uruchom serwer HTTPS, podając ścieżki do własnych plików
sudo arpx up -n 1 --https custom --cert-file /sciezka/do/cert.pem --key-file /sciezka/do/key.pem
```

---

## 2. Terminacja TLS dla usług w kontenerach (`arpx compose`)

Ta funkcja uruchamia proxy z terminacją TLS przed Twoimi kontenerami. `arpx` obsługuje ruch HTTPS z sieci LAN i przekazuje go jako zwykły ruch HTTP do Twoich usług.

```bash
# 1. Uruchom swoje kontenery
docker compose -f examples/docker/docker-compose.yml up -d

# 2. Uruchom mostkowanie z terminacją TLS na porcie 443
# Ruch na https://<alias_ip>:443 zostanie odszyfrowany i przekierowany do kontenera.
sudo arpx compose -f examples/docker/docker-compose.yml \
  --https self-signed \
  --domains myapp.lan \
  --https-port 443
```

Możesz również użyć `--https mkcert` zamiast `self-signed`.
