#!/bin/bash

# Skrypt instalacyjny dla Multi-IP Network Manager
# Autor: System Configuration Tool
# Data: 2025

set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║   Instalator Multi-IP Network Manager               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Sprawdź czy skrypt jest uruchomiony jako root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Ten skrypt musi być uruchomiony jako root"
    echo "Użyj: sudo bash $0"
    exit 1
fi

# Funkcja sprawdzająca dystrybucję
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si)
        VER=$(lsb_release -sr)
    else
        OS=$(uname -s)
        VER=$(uname -r)
    fi
    echo "🔍 Wykryto system: $OS $VER"
}

# Funkcja instalująca wymagane pakiety
install_packages() {
    echo "📦 Instalowanie wymaganych pakietów..."
    
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y python3 python3-pip iproute2 net-tools
    elif command -v yum &> /dev/null; then
        yum install -y python3 python3-pip iproute net-tools
    elif command -v dnf &> /dev/null; then
        dnf install -y python3 python3-pip iproute net-tools
    elif command -v pacman &> /dev/null; then
        pacman -Sy --noconfirm python python-pip iproute2 net-tools
    else
        echo "⚠️ Nieobsługiwany menedżer pakietów. Zainstaluj ręcznie:"
        echo "   - Python 3"
        echo "   - iproute2"
        echo "   - net-tools"
        return 1
    fi
    
    echo "✅ Pakiety zainstalowane"
}

# Funkcja instalująca Docker (opcjonalnie)
install_docker() {
    read -p "🐳 Czy chcesz zainstalować Docker? (t/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Tt]$ ]]; then
        echo "📦 Instalowanie Docker..."
        
        # Usuń stare wersje
        apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
        
        # Instaluj wymagane pakiety
        apt-get update
        apt-get install -y \
            ca-certificates \
            curl \
            gnupg \
            lsb-release
        
        # Dodaj klucz GPG Docker
        mkdir -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        
        # Dodaj repozytorium
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        # Instaluj Docker
        apt-get update
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        
        # Uruchom i włącz Docker
        systemctl start docker
        systemctl enable docker
        
        echo "✅ Docker zainstalowany"
    fi
}

# Funkcja tworząca skrypt systemowy
create_systemd_service() {
    echo "🔧 Tworzenie usługi systemowej..."
    
    cat > /etc/systemd/system/multi-ip-manager.service << EOF
[Unit]
Description=Multi-IP Network Manager
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/multi-ip-manager.py -i eth0 -n 3 --docker
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Skopiuj skrypt główny
    cp multi-ip-manager.py /usr/local/bin/
    chmod +x /usr/local/bin/multi-ip-manager.py
    
    # Przeładuj systemd
    systemctl daemon-reload
    
    echo "✅ Usługa systemowa utworzona"
    echo ""
    echo "📝 Użycie usługi:"
    echo "   Uruchom:    systemctl start multi-ip-manager"
    echo "   Zatrzymaj:  systemctl stop multi-ip-manager"
    echo "   Status:     systemctl status multi-ip-manager"
    echo "   Autostart:  systemctl enable multi-ip-manager"
}

# Funkcja konfigurująca firewall
configure_firewall() {
    read -p "🔥 Czy skonfigurować firewall (ufw)? (t/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Tt]$ ]]; then
        if ! command -v ufw &> /dev/null; then
            apt-get install -y ufw
        fi
        
        # Konfiguruj porty
        for port in {8000..8010}; do
            ufw allow $port/tcp comment "Multi-IP HTTP Server"
        done
        
        # Docker
        ufw allow 2375/tcp comment "Docker"
        ufw allow 2376/tcp comment "Docker TLS"
        
        echo "✅ Firewall skonfigurowany"
    fi
}

# Funkcja wyświetlająca interfejsy sieciowe
show_interfaces() {
    echo ""
    echo "📡 Dostępne interfejsy sieciowe:"
    echo "================================"
    ip -brief link show | awk '{print "   " $1 " - " $2}'
    echo ""
    
    # Pokaż aktywny interfejs
    ACTIVE_IF=$(ip route | grep default | awk '{print $5}' | head -1)
    echo "🌐 Aktywny interfejs: $ACTIVE_IF"
    
    # Pokaż aktualny IP
    CURRENT_IP=$(ip addr show $ACTIVE_IF | grep "inet " | awk '{print $2}' | cut -d/ -f1 | head -1)
    echo "📍 Aktualny IP: $CURRENT_IP"
}

# Funkcja tworząca przykładową konfigurację
create_example_config() {
    echo "📝 Tworzenie przykładowej konfiguracji..."
    
    cat > /etc/multi-ip-config.json << EOF
{
    "interface": "eth0",
    "virtual_ips": [
        {
            "ip": "192.168.1.100",
            "port": 8000,
            "content": "Hello Server 1"
        },
        {
            "ip": "192.168.1.101",
            "port": 8001,
            "content": "Hello Server 2"
        },
        {
            "ip": "192.168.1.102",
            "port": 8002,
            "content": "Hello Server 3"
        }
    ],
    "docker": {
        "enabled": true,
        "network": "multiip-network",
        "subnet": "192.168.100.0/24",
        "containers": [
            {
                "name": "web1",
                "ip": "192.168.100.10",
                "image": "nginx:alpine"
            },
            {
                "name": "web2",
                "ip": "192.168.100.11",
                "image": "nginx:alpine"
            },
            {
                "name": "web3",
                "ip": "192.168.100.12",
                "image": "nginx:alpine"
            }
        ]
    }
}
EOF
    
    echo "✅ Konfiguracja zapisana w /etc/multi-ip-config.json"
}

# Funkcja tworząca skrypt pomocniczy
create_helper_scripts() {
    echo "🛠️ Tworzenie skryptów pomocniczych..."
    
    # Skrypt do szybkiego testu
    cat > /usr/local/bin/test-multi-ip << 'EOF'
#!/bin/bash
echo "🧪 Testowanie wirtualnych IP..."
BASE_IP="192.168.1.100"
BASE_PORT=8000

for i in {0..2}; do
    IP_LAST=$((${BASE_IP##*.} + $i))
    IP="${BASE_IP%.*}.$IP_LAST"
    PORT=$((BASE_PORT + i))
    
    echo -n "Testing $IP:$PORT ... "
    if curl -s -o /dev/null -w "%{http_code}" http://$IP:$PORT | grep -q "200"; then
        echo "✅ OK"
    else
        echo "❌ FAIL"
    fi
done
EOF
    chmod +x /usr/local/bin/test-multi-ip
    
    # Skrypt do czyszczenia
    cat > /usr/local/bin/cleanup-multi-ip << 'EOF'
#!/bin/bash
echo "🧹 Czyszczenie wirtualnych IP i kontenerów..."

# Zatrzymaj usługę
systemctl stop multi-ip-manager 2>/dev/null || true

# Usuń wirtualne IP
for i in {0..9}; do
    ip addr del 192.168.1.10$i/24 dev eth0 2>/dev/null || true
done

# Zatrzymaj i usuń kontenery Docker
docker ps -a | grep "web-container-" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

# Usuń sieć Docker
docker network rm multiip-network 2>/dev/null || true

echo "✅ Czyszczenie zakończone"
EOF
    chmod +x /usr/local/bin/cleanup-multi-ip
    
    echo "✅ Skrypty pomocnicze utworzone"
}

# Główna funkcja instalacyjna
main() {
    detect_distro
    install_packages
    install_docker
    show_interfaces
    create_example_config
    create_systemd_service
    configure_firewall
    create_helper_scripts
    
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║   ✅ Instalacja zakończona pomyślnie!               ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""
    echo "📚 Instrukcja użycia:"
    echo ""
    echo "1. Uruchomienie ręczne:"
    echo "   sudo python3 multi-ip-manager.py -i eth0 -n 3"
    echo ""
    echo "2. Uruchomienie z Dockerem:"
    echo "   sudo python3 multi-ip-manager.py -i eth0 -n 3 --docker"
    echo ""
    echo "3. Uruchomienie jako usługa:"
    echo "   sudo systemctl start multi-ip-manager"
    echo ""
    echo "4. Testowanie:"
    echo "   sudo test-multi-ip"
    echo ""
    echo "5. Czyszczenie:"
    echo "   sudo cleanup-multi-ip"
    echo ""
    echo "📝 Konfiguracja: /etc/multi-ip-config.json"
    echo "📁 Skrypt główny: /usr/local/bin/multi-ip-manager.py"
    echo ""
}

# Uruchom instalator
main