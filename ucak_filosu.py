import socket
import pickle
import threading
import time

class Ucak_Filosu:
    def __init__(self, host='localhost', port=5002):
        self.ucaklar = []
        
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.connections = {} 
        
        self.merkez_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.merkez_connected = False
        self.merkez_port = 5001
    
    def connect_to_center(self):
        """Merkez sunucuya bağlanır"""
        try:
            self.merkez_socket.connect((self.host, self.merkez_port))
            self.merkez_connected = True
            print(f"Filo merkeze bağlandı: {self.host}:{self.merkez_port}")
            
            identity = {
                'type': 'registration',
                'entity': 'filo'
            }
            self.merkez_socket.sendall(pickle.dumps(identity))
            
            threading.Thread(target=self.listen_to_center, daemon=True).start()
            
            return True
        except ConnectionRefusedError:
            print("Merkeze bağlanılamadı.")
            return False
    
    def listen_to_center(self):
        """Merkezden gelen komutları dinler"""
        while self.merkez_connected:
            try:
                data = self.merkez_socket.recv(4096)
                if not data:
                    break
                
                command = pickle.loads(data)
                if command['type'] == 'deploy':
                    ucak_id = command.get('ucak_id')
                    target = command.get('target')
                    
                    for ucak in self.ucaklar:
                        if ucak.ucak_id == ucak_id:
                            print(f"Filo merkezi: {ucak_id} ID'li uçak {target} koordinatlarına görevlendiriliyor.")
                            self.send_command_to_aircraft(ucak_id, 'move', target)
                            break
                    else:
                        print(f"Filo merkezi: {ucak_id} ID'li uçak filoda bulunamadı!")
                
                elif command['type'] == 'status_request':
                    self.request_all_status()
                
                elif command['type'] == 'attack_order':
                    ucak_id = command.get('ucak_id')
                    target = command.get('target')
                    self.send_command_to_aircraft(ucak_id, 'attack', target)
            
            except Exception as e:
                print(f"Merkez dinleme hatası: {e}")
                self.merkez_connected = False
                break
    
    def start_server(self):
        """Uçakların bağlanması için sunucuyu başlatır"""
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(10) 
            self.connected = True
            print(f"Filo sunucusu {self.host}:{self.port} adresinde dinliyor...")
            
            accept_thread = threading.Thread(target=self.accept_connections)
            accept_thread.daemon = True
            accept_thread.start()
            
            return True
        except Exception as e:
            print(f"Sunucu başlatma hatası: {e}")
            return False
    
    def accept_connections(self):
        """Uçak bağlantılarını kabul eder"""
        while self.connected:
            try:
                client_socket, address = self.socket.accept()
                print(f"Bağlantı kabul edildi: {address}")

                client_thread = threading.Thread(target=self.handle_aircraft, args=(client_socket,))
                client_thread.daemon = True
                client_thread.start()
            
            except Exception as e:
                print(f"Bağlantı kabul hatası: {e}")
                if not self.connected:
                    break
    
    def handle_aircraft(self, client_socket):
        """Uçakla haberleşmeyi yönetir"""
        ucak_id = None
        try:
            data = client_socket.recv(4096)
            if data:
                aircraft_info = pickle.loads(data)
                if aircraft_info['type'] == 'registration':
                    ucak_id = aircraft_info['ucak_id']
                    ucak_turu = aircraft_info['ucak_turu']
                    
                    from ucak import Ucak
                    new_aircraft = Ucak(ucak_id, ucak_turu)
                    self.ucaklar.append(new_aircraft)
                    self.connections[ucak_id] = client_socket
                    
                    print(f"Uçak kaydedildi: {ucak_id} ({ucak_turu})")

                    if self.merkez_connected:
                        aircraft_registered = {
                            'type': 'aircraft_registered',
                            'ucak_id': ucak_id,
                            'ucak_turu': ucak_turu
                        }
                        self.merkez_socket.sendall(pickle.dumps(aircraft_registered))

            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                message = pickle.loads(data)

                if self.merkez_connected:
                    self.merkez_socket.sendall(data)  
                
                print(f"Uçak {ucak_id}'den mesaj alındı: {message}")
        
        except Exception as e:
            print(f"Uçak haberleşme hatası: {e}")
        
        finally:
            if ucak_id and ucak_id in self.connections:
                del self.connections[ucak_id]
                self.ucaklar = [u for u in self.ucaklar if u.ucak_id != ucak_id]
                print(f"Uçak {ucak_id} ile bağlantı kesildi.")
            
            client_socket.close()
    
    def send_command_to_aircraft(self, ucak_id, command_type, data=None):
        """Belirli bir uçağa komut gönderir"""
        if ucak_id in self.connections:
            command = {
                'type': command_type
            }
            
            if command_type == 'move' or command_type == 'attack':
                command['coordinates'] = data
            
            try:
                self.connections[ucak_id].sendall(pickle.dumps(command))
                print(f"Komut {ucak_id} uçağına gönderildi: {command_type}")
                return True
            except Exception as e:
                print(f"Komut gönderme hatası: {e}")
                return False
        else:
            print(f"Uçak {ucak_id} bağlı değil!")
            return False
    
    def request_all_status(self):
        """Tüm uçakların durumunu ister"""
        status_request = {
            'type': 'status_request'
        }
        
        for ucak_id, connection in self.connections.items():
            try:
                connection.sendall(pickle.dumps(status_request))
                print(f"Durum sorgusu {ucak_id} uçağına gönderildi")
            except:
                print(f"Durum sorgusu gönderilemedi: {ucak_id}")
    
    def Ucak_Filosuna_Ekle(self, ucak):
        """Yeni bir uçağı filoya ekler"""
        self.ucaklar.append(ucak)
        print(f"{ucak.ucak_id} nolu {ucak.ucak_turu} filoya eklendi")
    
    def filo_goster(self):
        """Filodaki tüm uçakları gösterir"""
        print("\n--- FILO DURUMU ---")
        for i, ucak in enumerate(self.ucaklar, 1):
            print(f"{i}. {ucak.ucak_id} nolu {ucak.ucak_turu} {ucak.koordinat} koordinatta {ucak.durum} vaziyetinde")
        print("-------------------\n")
    
    def close(self):
        """Tüm bağlantıları kapatır"""
        self.connected = False

        if hasattr(self, 'socket'):
            self.socket.close()
        
        if self.merkez_connected:
            self.merkez_socket.close()
            self.merkez_connected = False
        
        for ucak_id, conn in self.connections.items():
            try:
                conn.close()
            except:
                pass
        
        self.connections.clear()

if __name__ == "__main__":
    filo = Ucak_Filosu()
    
    try:
        if filo.start_server():
            filo.connect_to_center()
            
            print("Filo kontrolü başlatıldı. Çıkmak için CTRL+C tuşlarına basın.")

            while True:
                filo.filo_goster()
                time.sleep(10)  # 
    
    except KeyboardInterrupt:
        print("Filo kontrolü kapatılıyor...")
    
    finally:
        filo.close()
