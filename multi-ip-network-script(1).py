#!/usr/bin/env python3
"""
Skrypt do tworzenia wielu adresów IP na jednej karcie sieciowej
oraz uruchamiania serwerów HTTP i integracji z Dockerem
"""

import os
import sys
import subprocess
import socket
import threading
import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse
import signal

class NetworkManager:
    """Klasa do zarządzania wirtualnymi interfejsami sieciowymi"""
    
    def __init__(self, interface="eth0"):
        self.interface = interface
        self.virtual_ips = []
        self.servers = []
        
    def check_root(self):
        """Sprawdza czy skrypt jest uruchomiony z uprawnieniami root"""
        if os.geteuid() != 0:
            print("❌ Ten skrypt wymaga uprawnień root!")
            print("Uruchom: sudo python3 {}".format(sys.argv[0]))
            sys.exit(1)
    
    def get_network_info(self):
        """Pobiera informacje o sieci"""
        try:
            # Pobierz aktualny adres IP
            cmd = f"ip addr show {self.interface} | grep 'inet ' | awk '{{print $2}}' | cut -d/ -f1 | head -1"
            result = subprocess.check_output(cmd, shell=True).decode().strip()
            
            # Pobierz maskę podsieci
            cmd_mask = f"ip addr show {self.interface} | grep 'inet ' | awk '{{print $2}}' | head -1"
            mask_result = subprocess.check_output(cmd_mask, shell=True).decode().strip()
            
            return result, mask_result
        except Exception as e:
            print(f"❌ Błąd pobierania informacji o sieci: {e}")
            return None, None
    
    def add_virtual_ip(self, ip_address, label_suffix):
        """Dodaje wirtualny adres IP do interfejsu"""
        try:
            label = f"{self.interface}:{label_suffix}"
            cmd = f"ip addr add {ip_address}/24 dev {self.interface} label {label}"
            subprocess.run(cmd, shell=True, check=True)
            print(f"✅ Dodano wirtualny IP: {ip_address} jako {label}")
            self.virtual_ips.append((ip_address, label))
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Błąd dodawania IP {ip_address}: {e}")
            return False
    
    def remove_virtual_ip(self, ip_address):
        """Usuwa wirtualny adres IP"""
        try:
            cmd = f"ip addr del {ip_address}/24 dev {self.interface}"
            subprocess.run(cmd, shell=True, check=True)
            print(f"✅ Usunięto wirtualny IP: {ip_address}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Błąd usuwania IP {ip_address}: {e}")
    
    def cleanup(self):
        """Czyści wszystkie dodane wirtualne IP"""
        print("\n🧹 Czyszczenie wirtualnych adresów IP...")
        for ip, label in self.virtual_ips:
            self.remove_virtual_ip(ip)
        
        # Zatrzymaj serwery
        for server in self.servers:
            try:
                server.shutdown()
            except:
                pass

class SimpleHTTPHandler(BaseHTTPRequestHandler):
    """Prosty handler HTTP"""
    
    def __init__(self, content, *args, **kwargs):
        self.content = content
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Obsługa żądań GET"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.content}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    text-align: center;
                    padding: 40px;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 20px;
                }}
                .info {{
                    color: #666;
                    margin: 10px 0;
                }}
                .ip {{
                    color: #764ba2;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{self.content}</h1>
                <p class="info">Serwer IP: <span class="ip">{self.server.server_address[0]}</span></p>
                <p class="info">Port: <span class="ip">{self.server.server_address[1]}</span></p>
                <p class="info">Czas: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        """Wycisza logi"""
        pass

class WebServerManager:
    """Zarządza serwerami HTTP"""
    
    def __init__(self):
        self.servers = []
        self.threads = []
    
    def start_server(self, ip_address, port, content):
        """Uruchamia serwer HTTP na określonym IP i porcie"""
        def handler(*args, **kwargs):
            return SimpleHTTPHandler(content, *args, **kwargs)
        
        try:
            server = HTTPServer((ip_address, port), handler)
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()
            
            self.servers.append(server)
            self.threads.append(thread)
            
            print(f"🌐 Serwer HTTP uruchomiony na http://{ip_address}:{port} - {content}")
            return server
        except Exception as e:
            print(f"❌ Błąd uruchamiania serwera na {ip_address}:{port}: {e}")
            return None
    
    def stop_all(self):
        """Zatrzymuje wszystkie serwery"""
        for server in self.servers:
            try:
                server.shutdown()
            except:
                pass

class DockerNetworkManager:
    """Zarządza integracją z Dockerem"""
    
    def __init__(self):
        self.networks = []
    
    def check_docker(self):
        """Sprawdza czy Docker jest zainstalowany"""
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True)
            return True
        except:
            print("⚠️ Docker nie jest zainstalowany lub niedostępny")
            return False
    
    def create_macvlan_network(self, network_name, interface, subnet, gateway, ip_range):
        """Tworzy sieć macvlan dla Dockera"""
        try:
            cmd = f"""docker network create -d macvlan \
                --subnet={subnet} \
                --gateway={gateway} \
                --ip-range={ip_range} \
                -o parent={interface} \
                {network_name}"""
            
            subprocess.run(cmd, shell=True, check=True)
            self.networks.append(network_name)
            print(f"✅ Utworzono sieć Docker macvlan: {network_name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Błąd tworzenia sieci Docker: {e}")
            return False
    
    def run_container(self, network_name, container_name, ip_address, port=80):
        """Uruchamia kontener Docker z określonym IP"""
        try:
            # Przykładowy kontener nginx
            cmd = f"""docker run -d \
                --name {container_name} \
                --network {network_name} \
                --ip {ip_address} \
                -p {ip_address}:{port}:80 \
                nginx:alpine"""
            
            subprocess.run(cmd, shell=True, check=True)
            print(f"✅ Uruchomiono kontener: {container_name} z IP: {ip_address}")
            
            # Modyfikuj domyślną stronę nginx
            modify_cmd = f"""docker exec {container_name} sh -c "echo '<h1>Container {container_name}</h1><p>IP: {ip_address}</p>' > /usr/share/nginx/html/index.html" """
            subprocess.run(modify_cmd, shell=True, check=True)
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Błąd uruchamiania kontenera: {e}")
            return False
    
    def cleanup(self):
        """Czyści utworzone sieci Docker"""
        for network in self.networks:
            try:
                subprocess.run(f"docker network rm {network}", shell=True, check=True)
                print(f"✅ Usunięto sieć Docker: {network}")
            except:
                pass

def main():
    parser = argparse.ArgumentParser(description='Zarządzanie wirtualnymi IP i serwerami')
    parser.add_argument('-i', '--interface', default='eth0', help='Interfejs sieciowy (domyślnie: eth0)')
    parser.add_argument('-n', '--num-ips', type=int, default=3, help='Liczba wirtualnych IP (domyślnie: 3)')
    parser.add_argument('-b', '--base-ip', help='Bazowy adres IP (np. 192.168.1.100)')
    parser.add_argument('-p', '--base-port', type=int, default=8000, help='Bazowy port HTTP (domyślnie: 8000)')
    parser.add_argument('--docker', action='store_true', help='Włącz integrację z Dockerem')
    parser.add_argument('--docker-subnet', default='192.168.100.0/24', help='Podsieć dla Dockera')
    
    args = parser.parse_args()
    
    # Inicjalizacja
    net_manager = NetworkManager(args.interface)
    web_manager = WebServerManager()
    docker_manager = DockerNetworkManager() if args.docker else None
    
    # Sprawdź uprawnienia root
    net_manager.check_root()
    
    print(f"""
╔══════════════════════════════════════════════════════╗
║     Multi-IP Network Manager dla Linux              ║
╚══════════════════════════════════════════════════════╝
    
📡 Interfejs: {args.interface}
🔢 Liczba wirtualnych IP: {args.num_ips}
🌐 Bazowy port HTTP: {args.base_port}
🐳 Docker: {'Włączony' if args.docker else 'Wyłączony'}
    """)
    
    # Pobierz informacje o sieci
    current_ip, current_mask = net_manager.get_network_info()
    if not current_ip:
        print("❌ Nie można pobrać informacji o sieci")
        sys.exit(1)
    
    print(f"📍 Aktualny IP: {current_ip}")
    print(f"📍 Maska: {current_mask}\n")
    
    # Określ bazowy IP
    if args.base_ip:
        base_ip = args.base_ip
    else:
        # Użyj aktualnego IP i zwiększ ostatni oktet
        ip_parts = current_ip.split('.')
        ip_parts[-1] = str(int(ip_parts[-1]) + 10)
        base_ip = '.'.join(ip_parts)
    
    print(f"🔧 Bazowy IP dla wirtualnych interfejsów: {base_ip}\n")
    
    # Obsługa sygnału do czyszczenia
    def signal_handler(sig, frame):
        print("\n\n⚠️ Otrzymano sygnał zakończenia...")
        net_manager.cleanup()
        web_manager.stop_all()
        if docker_manager:
            docker_manager.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Tworzenie wirtualnych IP
        ip_parts = base_ip.split('.')
        created_ips = []
        
        for i in range(args.num_ips):
            # Generuj kolejne IP
            ip_parts[-1] = str(int(base_ip.split('.')[-1]) + i)
            virtual_ip = '.'.join(ip_parts)
            
            # Dodaj wirtualny IP
            if net_manager.add_virtual_ip(virtual_ip, i+1):
                created_ips.append(virtual_ip)
                
                # Uruchom serwer HTTP
                port = args.base_port + i
                content = f"Hello {i+1}"
                web_manager.start_server(virtual_ip, port, content)
        
        print(f"\n✅ Utworzono {len(created_ips)} wirtualnych adresów IP")
        print("\n📋 Lista aktywnych serwerów:")
        for i, ip in enumerate(created_ips):
            print(f"   http://{ip}:{args.base_port + i} - Hello {i+1}")
        
        # Integracja z Dockerem
        if docker_manager and docker_manager.check_docker():
            print("\n🐳 Konfiguracja Docker...")
            
            # Twórz sieć macvlan
            subnet = args.docker_subnet
            gateway = subnet.split('/')[0].rsplit('.', 1)[0] + '.1'
            ip_range = subnet.split('/')[0].rsplit('.', 1)[0] + '.128/25'
            
            if docker_manager.create_macvlan_network("multiip-network", args.interface, subnet, gateway, ip_range):
                # Uruchom kontenery
                docker_base = subnet.split('/')[0].rsplit('.', 1)[0] + '.130'
                docker_parts = docker_base.split('.')
                
                for i in range(min(3, args.num_ips)):  # Maksymalnie 3 kontenery dla przykładu
                    docker_parts[-1] = str(int(docker_base.split('.')[-1]) + i)
                    container_ip = '.'.join(docker_parts)
                    container_name = f"web-container-{i+1}"
                    
                    docker_manager.run_container("multiip-network", container_name, container_ip)
                
                print("\n📋 Kontenery Docker:")
                print(f"   Użyj: docker ps")
                print(f"   Sieć: docker network inspect multiip-network")
        
        print("""
╔══════════════════════════════════════════════════════╗
║  ✅ System gotowy!                                   ║
║  Naciśnij Ctrl+C aby zatrzymać i wyczyścić          ║
╚══════════════════════════════════════════════════════╝
        """)
        
        # Utrzymuj skrypt działający
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Zatrzymywanie...")
    finally:
        net_manager.cleanup()
        web_manager.stop_all()
        if docker_manager:
            docker_manager.cleanup()

if __name__ == "__main__":
    main()