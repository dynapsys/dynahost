#!/usr/bin/env python3
"""
Multi-IP Network Manager - Wersja z pełną widocznością w sieci lokalnej
Tworzy wirtualne IP widoczne dla wszystkich urządzeń w sieci LAN
"""

import os
import sys
import subprocess
import socket
import threading
import time
import json
import ipaddress
from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse
import signal
import struct

class NetworkVisibleManager:
    """Zarządza wirtualnymi IP widocznymi w całej sieci lokalnej"""
    
    def __init__(self, interface="eth0"):
        self.interface = interface
        self.virtual_ips = []
        self.servers = []
        self.arp_announced = []
        
    def check_root(self):
        """Sprawdza uprawnienia root"""
        if os.geteuid() != 0:
            print("❌ Ten skrypt wymaga uprawnień root!")
            print("Uruchom: sudo python3 {}".format(sys.argv[0]))
            sys.exit(1)
    
    def get_network_details(self):
        """Pobiera szczegółowe informacje o sieci"""
        try:
            # Pobierz interfejs
            cmd = f"ip addr show {self.interface}"
            result = subprocess.check_output(cmd, shell=True).decode()
            
            # Wyciągnij IP i maskę
            import re
            ip_pattern = r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)'
            match = re.search(ip_pattern, result)
            
            if match:
                ip = match.group(1)
                cidr = match.group(2)
                
                # Oblicz zakres sieci
                network = ipaddress.IPv4Network(f"{ip}/{cidr}", strict=False)
                
                print(f"📡 Interfejs: {self.interface}")
                print(f"📍 Aktualny IP: {ip}/{cidr}")
                print(f"🌐 Sieć: {network.network_address}")
                print(f"📡 Broadcast: {network.broadcast_address}")
                print(f"🔢 Dostępne hosty: {network.num_addresses - 2}")
                
                return str(ip), str(network.network_address), cidr, str(network.broadcast_address)
            
        except Exception as e:
            print(f"❌ Błąd pobierania informacji o sieci: {e}")
            return None, None, None, None
    
    def find_free_ips(self, base_network, cidr, num_ips=3):
        """Znajduje wolne adresy IP w sieci"""
        network = ipaddress.IPv4Network(f"{base_network}/{cidr}", strict=False)
        free_ips = []
        checked = 0
        
        print("\n🔍 Szukanie wolnych adresów IP w sieci...")
        
        # Zacznij od .100 dla bezpieczeństwa (omijamy DHCP)
        start_ip = 100
        
        for ip in network.hosts():
            if int(str(ip).split('.')[-1]) < start_ip:
                continue
                
            if checked >= 50:  # Sprawdź max 50 adresów
                break
                
            ip_str = str(ip)
            
            # Sprawdź czy IP jest wolny (ping)
            cmd = f"ping -c 1 -W 1 {ip_str}"
            result = subprocess.run(cmd, shell=True, capture_output=True)
            
            if result.returncode != 0:  # Brak odpowiedzi = wolny IP
                # Dodatkowa weryfikacja przez ARP
                arp_cmd = f"arping -c 1 -w 1 {ip_str} 2>/dev/null"
                arp_result = subprocess.run(arp_cmd, shell=True, capture_output=True)
                
                if arp_result.returncode != 0:
                    free_ips.append(ip_str)
                    print(f"   ✅ Wolny: {ip_str}")
                    
                    if len(free_ips) >= num_ips:
                        break
            
            checked += 1
        
        if len(free_ips) < num_ips:
            print(f"⚠️ Znaleziono tylko {len(free_ips)} wolnych IP")
        
        return free_ips
    
    def add_virtual_ip_with_visibility(self, ip_address, label_suffix, cidr="24"):
        """Dodaje wirtualny IP z pełną widocznością w sieci"""
        try:
            label = f"{self.interface}:{label_suffix}"
            
            # Dodaj alias IP
            cmd = f"ip addr add {ip_address}/{cidr} dev {self.interface} label {label}"
            subprocess.run(cmd, shell=True, check=True)
            
            # Włącz forwarding IP (ważne dla widoczności)
            subprocess.run("echo 1 > /proc/sys/net/ipv4/ip_forward", shell=True)
            
            # Włącz ARP proxy dla lepszej widoczności
            subprocess.run(f"echo 1 > /proc/sys/net/ipv4/conf/{self.interface}/proxy_arp", shell=True)
            
            # Ogłoś IP w sieci przez gratuitous ARP
            self.announce_arp(ip_address)
            
            # Dodaj wpis do ARP cache
            self.update_arp_cache(ip_address)
            
            print(f"✅ Dodano i ogłoszono IP: {ip_address} jako {label}")
            self.virtual_ips.append((ip_address, label))
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Błąd dodawania IP {ip_address}: {e}")
            return False
    
    def announce_arp(self, ip_address):
        """Wysyła gratuitous ARP aby ogłosić nowy IP w sieci"""
        try:
            # Metoda 1: arping
            cmd = f"arping -U -I {self.interface} -c 3 {ip_address} 2>/dev/null"
            subprocess.run(cmd, shell=True)
            
            # Metoda 2: ip neigh (dla pewności)
            mac = self.get_interface_mac()
            if mac:
                cmd2 = f"ip neigh add {ip_address} lladdr {mac} dev {self.interface} nud permanent 2>/dev/null"
                subprocess.run(cmd2, shell=True)
            
            self.arp_announced.append(ip_address)
            print(f"   📢 Ogłoszono ARP dla {ip_address}")
            
        except Exception as e:
            print(f"   ⚠️ Nie udało się ogłosić ARP dla {ip_address}: {e}")
    
    def get_interface_mac(self):
        """Pobiera adres MAC interfejsu"""
        try:
            cmd = f"ip link show {self.interface} | grep ether | awk '{{print $2}}'"
            mac = subprocess.check_output(cmd, shell=True).decode().strip()
            return mac
        except:
            return None
    
    def update_arp_cache(self, ip_address):
        """Aktualizuje lokalną tablicę ARP"""
        try:
            mac = self.get_interface_mac()
            if mac:
                cmd = f"arp -s {ip_address} {mac} 2>/dev/null"
                subprocess.run(cmd, shell=True)
        except:
            pass
    
    def configure_firewall_for_lan(self, ip_address, port):
        """Konfiguruje firewall dla dostępu z sieci lokalnej"""
        try:
            # Sprawdź czy iptables jest dostępny
            result = subprocess.run("which iptables", shell=True, capture_output=True)
            if result.returncode == 0:
                # Zezwól na ruch przychodzący na porcie
                cmd = f"iptables -A INPUT -d {ip_address} -p tcp --dport {port} -j ACCEPT"
                subprocess.run(cmd, shell=True)
                
                # Zezwól na odpowiedzi
                cmd2 = f"iptables -A OUTPUT -s {ip_address} -p tcp --sport {port} -j ACCEPT"
                subprocess.run(cmd2, shell=True)
                
                print(f"   🔥 Firewall skonfigurowany dla {ip_address}:{port}")
        except:
            pass
    
    def remove_virtual_ip(self, ip_address, cidr="24"):
        """Usuwa wirtualny IP i czyści ARP"""
        try:
            # Usuń IP
            cmd = f"ip addr del {ip_address}/{cidr} dev {self.interface}"
            subprocess.run(cmd, shell=True, check=True)
            
            # Usuń z ARP
            cmd2 = f"arp -d {ip_address} 2>/dev/null"
            subprocess.run(cmd2, shell=True)
            
            print(f"✅ Usunięto IP: {ip_address}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Błąd usuwania IP {ip_address}: {e}")
    
    def cleanup(self):
        """Czyści wszystkie zmiany"""
        print("\n🧹 Czyszczenie...")
        for ip, label in self.virtual_ips:
            self.remove_virtual_ip(ip)

class VisibleHTTPHandler(BaseHTTPRequestHandler):
    """Handler HTTP z informacjami o połączeniu"""
    
    def __init__(self, content, server_ip, *args, **kwargs):
        self.content = content
        self.server_ip = server_ip
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Obsługa GET z informacjami dla debugowania"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Pobierz IP klienta
        client_ip = self.client_address[0]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.content}</title>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0;
                    padding: 0;
                    min-height: 100vh;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .container {{
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    max-width: 500px;
                    width: 90%;
                }}
                h1 {{
                    color: #333;
                    margin: 0 0 30px 0;
                    font-size: 2.5em;
                    text-align: center;
                }}
                .info-grid {{
                    display: grid;
                    gap: 15px;
                }}
                .info-item {{
                    background: #f7f9fc;
                    padding: 15px;
                    border-radius: 10px;
                    border-left: 4px solid #667eea;
                }}
                .label {{
                    color: #666;
                    font-size: 0.9em;
                    margin-bottom: 5px;
                }}
                .value {{
                    color: #333;
                    font-weight: bold;
                    font-size: 1.1em;
                    font-family: 'Courier New', monospace;
                }}
                .status {{
                    background: #10b981;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 20px;
                    display: inline-block;
                    margin-top: 20px;
                }}
                .network-test {{
                    margin-top: 20px;
                    padding: 20px;
                    background: #eff6ff;
                    border-radius: 10px;
                }}
                .test-title {{
                    font-weight: bold;
                    margin-bottom: 10px;
                    color: #1e40af;
                }}
                code {{
                    background: #f3f4f6;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-family: monospace;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🌐 {self.content}</h1>
                
                <div class="info-grid">
                    <div class="info-item">
                        <div class="label">📡 Server IP (Wirtualny)</div>
                        <div class="value">{self.server_ip}</div>
                    </div>
                    
                    <div class="info-item">
                        <div class="label">🚪 Port</div>
                        <div class="value">{self.server.server_address[1]}</div>
                    </div>
                    
                    <div class="info-item">
                        <div class="label">👤 Twój IP (Klient)</div>
                        <div class="value">{client_ip}</div>
                    </div>
                    
                    <div class="info-item">
                        <div class="label">⏰ Czas serwera</div>
                        <div class="value">{time.strftime('%H:%M:%S')}</div>
                    </div>
                    
                    <div class="info-item">
                        <div class="label">📅 Data</div>
                        <div class="value">{time.strftime('%Y-%m-%d')}</div>
                    </div>
                </div>
                
                <center>
                    <span class="status">✅ Serwer działa i jest widoczny w sieci!</span>
                </center>
                
                <div class="network-test">
                    <div class="test-title">🧪 Test z innych komputerów:</div>
                    <p>Otwórz przeglądarkę na innym komputerze w sieci i wpisz:</p>
                    <code>http://{self.server_ip}:{self.server.server_address[1]}</code>
                    <p style="margin-top: 10px; font-size: 0.9em; color: #666;">
                        Nie potrzebujesz konfigurować DNS ani hosts - IP jest bezpośrednio dostępne!
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        self.wfile.write(html.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Własne logowanie"""
        client_ip = self.client_address[0]
        print(f"   🌐 [{time.strftime('%H:%M:%S')}] Połączenie z {client_ip} -> {self.server_ip}")

class LANWebServerManager:
    """Menedżer serwerów HTTP widocznych w LAN"""
    
    def __init__(self):
        self.servers = []
        self.threads = []
    
    def start_lan_server(self, ip_address, port, content):
        """Uruchamia serwer widoczny w całej sieci lokalnej"""
        def handler(*args, **kwargs):
            return VisibleHTTPHandler(content, ip_address, *args, **kwargs)
        
        try:
            # Bind do konkretnego IP (nie 127.0.0.1!)
            server = HTTPServer((ip_address, port), handler)
            server.timeout = 0.5  # Dla responsywności
            
            def serve_forever_with_shutdown():
                while not getattr(server, 'shutdown_requested', False):
                    server.handle_request()
            
            thread = threading.Thread(target=serve_forever_with_shutdown)
            thread.daemon = True
            thread.start()
            
            self.servers.append(server)
            self.threads.append(thread)
            
            print(f"🌐 Serwer HTTP uruchomiony i widoczny w LAN:")
            print(f"   📍 Adres: http://{ip_address}:{port}")
            print(f"   📝 Treść: {content}")
            
            return server
            
        except Exception as e:
            print(f"❌ Błąd uruchamiania serwera na {ip_address}:{port}: {e}")
            return None
    
    def test_connectivity(self, ip_address, port):
        """Testuje dostępność serwera"""
        try:
            import urllib.request
            response = urllib.request.urlopen(f"http://{ip_address}:{port}", timeout=2)
            if response.status == 200:
                print(f"   ✅ Test połączenia: Serwer {ip_address}:{port} odpowiada")
                return True
        except:
            print(f"   ❌ Test połączenia: Brak odpowiedzi z {ip_address}:{port}")
            return False
    
    def stop_all(self):
        """Zatrzymuje wszystkie serwery"""
        for server in self.servers:
            try:
                server.shutdown_requested = True
            except:
                pass

def print_summary(created_ips, base_port):
    """Wyświetla podsumowanie dla użytkownika"""
    print("\n" + "="*60)
    print("✅ SERWERY URUCHOMIONE I WIDOCZNE W SIECI LOKALNEJ")
    print("="*60)
    print("\n📋 LISTA SERWERÓW (dostępne z każdego komputera w sieci):\n")
    
    for i, ip in enumerate(created_ips):
        port = base_port + i
        print(f"   {i+1}. http://{ip}:{port}")
        print(f"      └─ Treść: Hello {i+1}")
    
    print("\n" + "="*60)
    print("🧪 JAK PRZETESTOWAĆ:")
    print("="*60)
    print("\n1. Z TEGO KOMPUTERA:")
    print(f"   curl http://{created_ips[0]}:{base_port}")
    print(f"   wget http://{created_ips[0]}:{base_port}")
    print(f"   Przeglądarka: http://{created_ips[0]}:{base_port}")
    
    print("\n2. Z INNEGO KOMPUTERA W SIECI:")
    print("   Otwórz przeglądarkę i wpisz dowolny z powyższych adresów")
    print("   NIE MUSISZ konfigurować DNS ani /etc/hosts!")
    
    print("\n3. ZE SMARTFONA/TABLETU:")
    print("   Połącz się z tą samą siecią WiFi")
    print(f"   Wpisz w przeglądarce: http://{created_ips[0]}:{base_port}")
    
    print("\n" + "="*60)
    print("⚠️  Naciśnij Ctrl+C aby zatrzymać wszystkie serwery")
    print("="*60 + "\n")

def main():
    parser = argparse.ArgumentParser(description='Multi-IP Manager - Widoczny w sieci LAN')
    parser.add_argument('-i', '--interface', help='Interfejs sieciowy (auto-detect jeśli pominięte)')
    parser.add_argument('-n', '--num-ips', type=int, default=3, help='Liczba wirtualnych IP')
    parser.add_argument('-b', '--base-ip', help='Bazowy IP (auto jeśli pominięte)')
    parser.add_argument('-p', '--base-port', type=int, default=8000, help='Bazowy port HTTP')
    parser.add_argument('--ip-start', type=int, default=100, help='Od którego numeru szukać wolnych IP')
    
    args = parser.parse_args()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║   Multi-IP Network Manager - Widoczny w sieci LAN          ║
║   Tworzy wirtualne IP dostępne z każdego komputera         ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Auto-detect interfejsu jeśli nie podano
    if not args.interface:
        try:
            # Znajdź aktywny interfejs
            cmd = "ip route | grep default | awk '{print $5}' | head -1"
            args.interface = subprocess.check_output(cmd, shell=True).decode().strip()
            if not args.interface:
                args.interface = "eth0"
            print(f"🔍 Auto-wykryto interfejs: {args.interface}")
        except:
            args.interface = "eth0"
    
    # Inicjalizacja
    net_manager = NetworkVisibleManager(args.interface)
    web_manager = LANWebServerManager()
    
    # Sprawdź root
    net_manager.check_root()
    
    # Pobierz szczegóły sieci
    current_ip, network_base, cidr, broadcast = net_manager.get_network_details()
    
    if not current_ip:
        print("❌ Nie można pobrać informacji o sieci")
        sys.exit(1)
    
    # Obsługa sygnałów
    def signal_handler(sig, frame):
        print("\n\n⚠️ Zatrzymywanie...")
        net_manager.cleanup()
        web_manager.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        created_ips = []
        
        if args.base_ip:
            # Użyj podanego bazowego IP
            base_parts = args.base_ip.split('.')
            for i in range(args.num_ips):
                base_parts[-1] = str(int(args.base_ip.split('.')[-1]) + i)
                ip = '.'.join(base_parts)
                created_ips.append(ip)
        else:
            # Znajdź wolne IP automatycznie
            print(f"\n🔍 Szukam {args.num_ips} wolnych adresów IP...")
            created_ips = net_manager.find_free_ips(network_base, cidr, args.num_ips)
            
            if not created_ips:
                print("❌ Nie znaleziono wolnych adresów IP")
                sys.exit(1)
        
        print(f"\n🚀 Konfigurowanie {len(created_ips)} wirtualnych IP...\n")
        
        # Twórz wirtualne IP i serwery
        for i, ip in enumerate(created_ips):
            print(f"📦 Konfiguracja {i+1}/{len(created_ips)}:")
            
            # Dodaj wirtualny IP z pełną widocznością
            if net_manager.add_virtual_ip_with_visibility(ip, i+1, cidr):
                # Skonfiguruj firewall
                port = args.base_port + i
                net_manager.configure_firewall_for_lan(ip, port)
                
                # Uruchom serwer HTTP
                content = f"Hello {i+1}"
                server = web_manager.start_lan_server(ip, port, content)
                
                if server:
                    # Test połączenia
                    time.sleep(0.5)  # Daj serwerowi czas na start
                    web_manager.test_connectivity(ip, port)
            
            print()  # Odstęp między serwerami
        
        # Pokaż podsumowanie
        print_summary(created_ips, args.base_port)
        
        # Poczekaj 2 sekundy i wyślij kolejne ogłoszenia ARP
        time.sleep(2)
        print("\n📢 Ponowne ogłaszanie IP w sieci...")
        for ip in created_ips:
            net_manager.announce_arp(ip)
        
        print("\n✅ System gotowy! Serwery są widoczne w całej sieci lokalnej.")
        print("   Możesz teraz otworzyć przeglądarkę na DOWOLNYM komputerze w sieci")
        print("   i wpisać adresy IP bez żadnej dodatkowej konfiguracji!\n")
        
        # Główna pętla
        while True:
            time.sleep(30)
            # Co 30 sekund odśwież ARP
            for ip in created_ips:
                net_manager.update_arp_cache(ip)
            
    except KeyboardInterrupt:
        print("\n\nZatrzymywanie...")
    finally:
        net_manager.cleanup()
        web_manager.stop_all()

if __name__ == "__main__":
    main()