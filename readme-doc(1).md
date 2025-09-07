# Multi-IP Network Manager dla Linux

## 📋 Opis

Skrypt Python umożliwiający tworzenie wielu wirtualnych adresów IP na jednej fizycznej karcie sieciowej (LAN/WLAN) w systemie Linux. Każdy wirtualny IP może hostować własny serwer HTTP oraz służyć jako endpoint dla kontenerów Docker.

## ✨ Funkcjonalności

- **Wirtualne adresy IP**: Tworzenie aliasów IP na jednej karcie sieciowej
- **Serwery HTTP**: Automatyczne uruchamianie serwerów HTTP na każdym wirtualnym IP
- **Integracja z Docker**: Tworzenie sieci macvlan i uruchamianie kontenerów z dedykowanymi IP
- **Zarządzanie**: Automatyczne czyszczenie przy zakończeniu
- **Monitoring**: Podgląd statusu wszystkich komponentów

## 🔧 Wymagania

### System
- Linux (Ubuntu, Debian, CentOS, Fedora, Arch)
- Python 3.6+
- Uprawnienia root

### Pakiety
```bash
# Debian/Ubuntu
sudo apt-get install python3 python3-pip iproute2 net-tools

# RHEL/CentOS/Fedora
sudo yum install python3 python3-pip iproute net-tools

# Arch
sudo pacman -S python python-pip iproute2 net-tools
```

### Docker (opcjonalnie)
```bash
# Instalacja Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

## 🚀 Szybki start

### 1. Instalacja automatyczna
```bash
# Pobierz i uruchom skrypt instalacyjny
sudo bash setup.sh
```

### 2. Instalacja ręczna
```bash
# Nadaj uprawnienia wykonywania
chmod +x multi-ip-manager.py

# Uruchom skrypt
sudo python3 multi-ip-manager.py -i eth0 -n 3
```

## 📖 Użycie

### Podstawowe użycie
```bash
# Utworzenie 3 wirtualnych IP na interfejsie eth0
sudo python3 multi-ip-manager.py -i eth0 -n 3

# Określenie bazowego IP
sudo python3 multi-ip-manager.py -i eth0 -n 5 -b 192.168.1.100

# Z integracją Docker
sudo python3 multi-ip-manager.py -i eth0 -n 3 --docker
```

### Parametry
- `-i, --interface` - Interfejs sieciowy (domyślnie: eth0)
- `-n, --num-ips` - Liczba wirtualnych IP do utworzenia (domyślnie: 3)
- `-b, --base-ip` - Bazowy adres IP dla wirtualnych interfejsów
- `-p, --base-port` - Bazowy port dla serwerów HTTP (domyślnie: 8000)
- `--docker` - Włącz integrację z Docker
- `--docker-subnet` - Podsieć dla sieci Docker (domyślnie: 192.168.100.0/24)

## 🌐 Przykłady użycia

### Przykład 1: Proste serwery HTTP
```bash
sudo python3 multi-ip-manager.py -i wlan0 -n 3 -b 192.168.1.200
```
Utworzy:
- http://192.168.1.200:8000 - Hello 1
- http://192.168.1.201:8001 - Hello 2
- http://192.168.1.202:8002 - Hello 3

### Przykład 2: Integracja z Docker
```bash
sudo python3 multi-ip-manager.py -i eth0 -n 3 --docker --docker-subnet 172.20.0.0/24
```
Utworzy wirtualne IP oraz kontenery Docker z dedykowanymi adresami.

### Przykład 3: Jako usługa systemowa
```bash
# Włącz autostart
sudo systemctl enable multi-ip-manager

# Uruchom usługę
sudo systemctl start multi-ip-manager

# Sprawdź status
sudo systemctl status multi-ip-manager
```

## 🐳 Praca z Docker

### Tworzenie sieci macvlan
```bash
docker network create -d macvlan \
  --subnet=192.168.100.0/24 \
  --gateway=192.168.100.1 \
  -o parent=eth0 \
  multiip-network
```

### Uruchamianie kontenerów z określonym IP
```bash
docker run -d \
  --name web1 \
  --network multiip-network \
  --ip 192.168.100.10 \
  nginx:alpine
```

### Przykład docker-compose.yml
```yaml
version: '3.8'

services:
  web1:
    image: nginx:alpine
    networks:
      multiip:
        ipv4_address: 192.168.100.10
    ports:
      - "192.168.100.10:80:80"

  web2:
    image: nginx:alpine
    networks:
      multiip:
        ipv4_address: 192.168.100.11
    ports:
      - "192.168.100.11:80:80"

  web3:
    image: nginx:alpine
    networks:
      multiip:
        ipv4_address: 192.168.100.12
    ports:
      - "192.168.100.12:80:80"

networks:
  multiip:
    driver: macvlan
    driver_opts:
      parent: eth0
    ipam:
      config:
        - subnet: 192.168.100.0/24
          gateway: 192.168.100.1
```

## 🔍 Testowanie

### Test połączenia
```bash
# Ping do wirtualnych IP
ping 192.168.1.100
ping 192.168.1.101
ping 192.168.1.102

# Test HTTP
curl http://192.168.1.100:8000
curl http://192.168.1.101:8001
curl http://192.168.1.102:8002

# Użyj skryptu testowego
sudo test-multi-ip
```

### Sprawdzenie konfiguracji
```bash
# Lista wszystkich adresów IP
ip addr show

# Lista tylko wirtualnych interfejsów
ip addr show | grep "eth0:"

# Status kontenerów Docker
docker ps

# Inspekcja sieci Docker
docker network inspect multiip-network
```

## 🛠️ Rozwiązywanie problemów

### Problem: "Permission denied"
```bash
# Upewnij się, że uruchamiasz jako root
sudo python3 multi-ip-manager.py
```

### Problem: "Address already in use"
```bash
# Wyczyść stare konfiguracje
sudo cleanup-multi-ip

# Lub ręcznie usuń IP
sudo ip addr del 192.168.1.100/24 dev eth0
```

### Problem: "Interface not found"
```bash
# Sprawdź dostępne interfejsy
ip link show

# Użyj właściwej nazwy interfejsu
sudo python3 multi-ip-manager.py -i enp0s3 -n 3
```

### Problem: Docker network conflict
```bash
# Usuń starą sieć
docker network rm multiip-network

# Zatrzymaj kontenery
docker stop $(docker ps -q)
docker rm $(docker ps -aq)
```

## 📁 Struktura plików

```
/usr/local/bin/
├── multi-ip-manager.py      # Główny skrypt
├── test-multi-ip            # Skrypt testowy
└── cleanup-multi-ip         # Skrypt czyszczący

/etc/
├── multi-ip-config.json     # Konfiguracja
└── systemd/system/
    └── multi-ip-manager.service  # Usługa systemowa
```

## ⚙️ Konfiguracja zaawansowana

### Plik konfiguracyjny JSON
```json
{
    "interface": "eth0",
    "virtual_ips": [
        {
            "ip": "192.168.1.100",
            "port": 8000,
            "content": "Custom Server 1",
            "docker": {
                "enabled": true,
                "container": "nginx",
                "port_mapping": "80:80"
            }
        }
    ],
    "docker": {
        "enabled": true,
        "network": "multiip-network",
        "subnet": "192.168.100.0/24"
    }
}
```

### Integracja z iptables
```bash
# Przekierowanie ruchu
sudo iptables -t nat -A PREROUTING -d 192.168.1.100 -j DNAT --to-destination 192.168.1.100

# MASQUERADE dla Docker
sudo iptables -t nat -A POSTROUTING -s 192.168.100.0/24 -j MASQUERADE
```

### Monitoring z Prometheus
```yaml
# docker-compose dla monitoringu
services:
  prometheus:
    image: prom/prometheus
    networks:
      multiip:
        ipv4_address: 192.168.100.50
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

## 🔒 Bezpieczeństwo

### Firewall (UFW)
```bash
# Zezwól na porty HTTP
sudo ufw allow 8000:8010/tcp

# Zezwól na Docker
sudo ufw allow 2375/tcp
sudo ufw allow 2376/tcp

# Włącz firewall
sudo ufw enable
```

### SELinux (CentOS/RHEL)
```bash
# Sprawdź kontekst
ls -Z /usr/local/bin/multi-ip-manager.py

# Ustaw kontekst
sudo chcon -t bin_t /usr/local/bin/multi-ip-manager.py
```

## 📊 Monitoring i logi

### Logi systemowe
```bash
# Podgląd logów usługi
sudo journalctl -u multi-ip-manager -f

# Logi Docker
docker logs container_name
```

### Monitoring sieci
```bash
# Statystyki interfejsu
ip -s link show eth0

# Monitoring ruchu
sudo tcpdump -i eth0 port 8000

# Netstat
sudo netstat -tulpn | grep 8000
```

## 🔄 Backup i restore

### Backup konfiguracji
```bash
# Backup
sudo tar -czf multi-ip-backup.tar.gz \
  /etc/multi-ip-config.json \
  /usr/local/bin/multi-ip-manager.py \
  /etc/systemd/system/multi-ip-manager.service

# Restore
sudo tar -xzf multi-ip-backup.tar.gz -C /
sudo systemctl daemon-reload
```

## 📝 Licencja

MIT License - możesz swobodnie używać, modyfikować i dystrybuować ten kod.

## 🤝 Wsparcie

W razie problemów:
1. Sprawdź sekcję "Rozwiązywanie problemów"
2. Sprawdź logi systemowe
3. Upewnij się, że masz najnowszą wersję
4. Zgłoś issue z dokładnym opisem problemu

## 🚦 Status projektu

✅ Gotowy do użytku produkcyjnego
- Wirtualne IP: ✅ Stabilne
- Serwery HTTP: ✅ Stabilne
- Integracja Docker: ✅ Stabilne
- Usługa systemowa: ✅ Stabilne

## 📚 Dodatkowe zasoby

- [Linux IP Command Tutorial](https://www.cyberciti.biz/faq/linux-ip-command-examples-usage-syntax/)
- [Docker Macvlan Networks](https://docs.docker.com/network/macvlan/)
- [Python HTTP Server](https://docs.python.org/3/library/http.server.html)
- [Systemd Services](https://www.freedesktop.org/software/systemd/man/systemd.service.html)