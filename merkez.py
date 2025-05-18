import socket
import pickle
import threading
import time
import random

class Merkez:
    def __init__(self, host='localhost', radar_port=5000, ucak_port=5001, filo_port=5002):
        self.host = host
        self.radar_port = radar_port
        self.ucak_port = ucak_port
        self.filo_port = filo_port
        
        self.radar_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ucak_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        self.radar_connections = {}  # {radar_id: connection}
        self.ucak_connections = {}   # {ucak_id: connection}
        self.filo_connections = {}   # {filo_id: connection}
        self.sorti_connections = {}  # {sorti_id: connection}
        
        self.threats = []
        self.ongoing_missions = {}   # {ucak_id: target}
        
        self.kazanilan = 0
        self.kaybedilen = 0
        self.game_over = False
    
    def start_servers(self):
        """Tüm sunucuları başlatır"""
        # Radar sunucusu
        self.radar_server.bind((self.host, self.radar_port))
        self.radar_server.listen(5)
        radar_thread = threading.Thread(target=self.accept_radar_connections)
        radar_thread.daemon = True
        radar_thread.start()
        print(f"Radar sunucusu başlatıldı: {self.host}:{self.radar_port}")
        
        # Uçak ve filo sunucusu
        self.ucak_server.bind((self.host, self.ucak_port))
        self.ucak_server.listen(10)
        ucak_thread = threading.Thread(target=self.accept_ucak_connections)
        ucak_thread.daemon = True
        ucak_thread.start()
        print(f"Uçak ve filo sunucusu başlatıldı: {self.host}:{self.ucak_port}")
        
        # Tehdit değerlendirme ve görev atama
        mission_thread = threading.Thread(target=self.mission_assignment_loop)
        mission_thread.daemon = True
        mission_thread.start()
    
    def accept_radar_connections(self):
        """Radardan gelen bağlantıları kabul eder"""
        while not self.game_over:
            try:
                client_socket, address = self.radar_server.accept()
                print(f"Radar bağlantısı kabul edildi: {address}")
                
                client_thread = threading.Thread(target=self.handle_radar, args=(client_socket, address))
                client_thread.daemon = True
                client_thread.start()
            
            except Exception as e:
                print(f"Radar bağlantısı kabul hatası: {e}")
                if self.game_over:
                    break
    
    def accept_ucak_connections(self):
        """Uçak ve filodan gelen bağlantıları kabul eder"""
        while not self.game_over:
            try:
                client_socket, address = self.ucak_server.accept()
                print(f"Uçak/Filo bağlantısı kabul edildi: {address}")
                
                data = client_socket.recv(4096)
                if data:
                    registration = pickle.loads(data)
                    entity_type = registration.get('entity', registration.get('type'))
                    
                    if entity_type == 'registration':
                        ucak_id = registration.get('ucak_id')
                        if ucak_id:
                            self.ucak_connections[ucak_id] = client_socket
                            print(f"Uçak kaydedildi: {ucak_id}")
                            
                            ucak_thread = threading.Thread(target=self.handle_ucak, args=(client_socket, ucak_id))
                            ucak_thread.daemon = True
                            ucak_thread.start()
                    
                    elif entity_type == 'filo':

                        filo_id = registration.get('filo_id', 'default_filo')
                        self.filo_connections[filo_id] = client_socket
                        print(f"Filo kaydedildi: {filo_id}")

                        filo_thread = threading.Thread(target=self.handle_filo, args=(client_socket, filo_id))
                        filo_thread.daemon = True
                        filo_thread.start()
                    
                    elif entity_type == 'sorti':

                        sorti_id = registration.get('sorti_id')
                        self.sorti_connections[sorti_id] = client_socket
                        print(f"Sorti kaydedildi: {sorti_id}")
                        
                        sorti_thread = threading.Thread(target=self.handle_sorti, args=(client_socket, sorti_id))
                        sorti_thread.daemon = True
                        sorti_thread.start()
            
            except Exception as e:
                print(f"Uçak/Filo bağlantı hatası: {e}")
                if self.game_over:
                    break
    
    def handle_radar(self, client_socket, address):
        """Radardan gelen verileri işler"""
        radar_id = f"radar_{address[0]}_{address[1]}"
        self.radar_connections[radar_id] = client_socket
        
        try:
            while not self.game_over:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                threat_data = pickle.loads(data)
                if threat_data['type'] == 'threat':
                    coordinates = threat_data['coordinates']
                    threat_type = threat_data['threat_type']
                    
                    print(f"Yeni tehdit tespit edildi: {threat_type} - {coordinates}")
                    
                    self.threats.append({
                        'coordinates': coordinates,
                        'type': threat_type,
                        'time': time.time(),
                        'status': 'active'
                    })
        
        except Exception as e:
            print(f"Radar haberleşme hatası: {e}")
        
        finally:
            if radar_id in self.radar_connections:
                del self.radar_connections[radar_id]
            client_socket.close()
    
    def handle_ucak(self, client_socket, ucak_id):
        """Uçaktan gelen mesajları işler"""
        try:
            while not self.game_over:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                message = pickle.loads(data)
                message_type = message.get('type')
                
                if message_type == 'status_update':
                    status = message.get('status')
                    coordinates = message.get('coordinates')
                    print(f"Uçak {ucak_id} güncelleme: {status} - {coordinates}")
                
                elif message_type == 'attack_result':
                    target = message.get('target')
                    result = message.get('result')
                    
                    if result == 'success':
                        self.kazanilan += 1
                        print(f"Uçak {ucak_id} hedefi imha etti: {target}")
                    else:
                        self.kaybedilen += 1
                        print(f"Uçak {ucak_id} hedefi ıskaladı: {target}")
                
                    if ucak_id in self.ongoing_missions:
                        del self.ongoing_missions[ucak_id]
                    
                    self.check_game_status()
        
        except Exception as e:
            print(f"Uçak {ucak_id} haberleşme hatası: {e}")
        
        finally:
            if ucak_id in self.ucak_connections:
                del self.ucak_connections[ucak_id]
            client_socket.close()
    
    def handle_filo(self, client_socket, filo_id):
        """Filodan gelen mesajları işler"""
        try:
            while not self.game_over:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                message = pickle.loads(data)
                print(f"Filo {filo_id}'dan mesaj: {message}")
        
        except Exception as e:
            print(f"Filo {filo_id} haberleşme hatası: {e}")
        
        finally:
            if filo_id in self.filo_connections:
                del self.filo_connections[filo_id]
            client_socket.close()
    
    def handle_sorti(self, client_socket, sorti_id):
        """Sortiden gelen mesajları işler"""
        try:
            while not self.game_over:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                message = pickle.loads(data)
                message_type = message.get('type')
                
                if message_type == 'sortie_status':
                    status = message.get('status')
                    ucak_id = message.get('ucak_id')
                    hedef = message.get('hedef')
                    sonuc = message.get('sonuc')
                    
                    print(f"Sorti {sorti_id} güncelleme: {status}")
                    
                    if sonuc is not None:
                        if sonuc == 1:
                            self.kazanilan += 1
                            print(f"Sorti {sorti_id} başarıyla tamamlandı.")
                        else:
                            self.kaybedilen += 1
                            print(f"Sorti {sorti_id} başarısız oldu.")
                        
                        self.check_game_status()
                
                elif message_type == 'mission_started':
                    ucak_id = message.get('ucak_id')
                    hedef = message.get('hedef')
                    print(f"Sorti {sorti_id} başladı: Uçak {ucak_id} -> Hedef {hedef}")
        
        except Exception as e:
            print(f"Sorti {sorti_id} haberleşme hatası: {e}")
        
        finally:
            if sorti_id in self.sorti_connections:
                del self.sorti_connections[sorti_id]
            client_socket.close()
    
    def mission_assignment_loop(self):
        """Periyodik olarak tehditleri değerlendirir ve görev ataması yapar"""
        while not self.game_over:
            active_threats = [t for t in self.threats if t['status'] == 'active']
            available_ucaklar = [u for u in self.ucak_connections.keys() if u not in self.ongoing_missions]
            
            for threat in active_threats:
                if not available_ucaklar:
                    break  
                
                ucak_id = random.choice(available_ucaklar)

                self.assign_mission(ucak_id, threat['coordinates'])
                
                threat['status'] = 'assigned'
                
                available_ucaklar.remove(ucak_id)

            time.sleep(3)
    
    def assign_mission(self, ucak_id, target):
        """Bir uçağa görev atar"""
        if ucak_id in self.ucak_connections:
            mission = {
                'type': 'attack',
                'coordinates': target
            }
            
            try:
                self.ucak_connections[ucak_id].sendall(pickle.dumps(mission))
                self.ongoing_missions[ucak_id] = target
                print(f"Uçak {ucak_id}'e görev atandı: Hedef {target}")
                return True
            except Exception as e:
                print(f"Görev atama hatası: {e}")
                if ucak_id in self.ucak_connections:
                    del self.ucak_connections[ucak_id]
                return False
        else:
            print(f"Uçak {ucak_id} bağlı değil!")
            return False
    
    def check_game_status(self):
        """Oyunun bitip bitmediğini kontrol eder"""
        print(f"\n-----------------------------")
        print(f"Kazanılan: {self.kazanilan}     Kaybedilen: {self.kaybedilen}")
        print(f"-----------------------------\n")
        
        if self.kazanilan >= 5 or self.kaybedilen >= 5:
            if self.kazanilan >= 5:
                print("Savaş bitti - Oley!!! Savaşı Kazandık")
                print("Tebrikler Komutan GENERALliğe terfi oldun.")
            else:
                print("Savaş bitti - Maalesef Savaşı Kaybettik.")
            
            self.game_over = True
            self.broadcast_game_over()
    
    def broadcast_game_over(self):
        """Tüm bağlı istemcilere oyun sonu mesajı gönderir"""
        game_over_msg = {
            'type': 'game_over',
            'kazanilan': self.kazanilan,
            'kaybedilen': self.kaybedilen,
            'result': 'win' if self.kazanilan >= 5 else 'lose'
        }
        
        serialized_msg = pickle.dumps(game_over_msg)
        
        for radar_conn in self.radar_connections.values():
            try:
                radar_conn.sendall(serialized_msg)
            except:
                pass

        for ucak_conn in self.ucak_connections.values():
            try:
                ucak_conn.sendall(serialized_msg)
            except:
                pass

        for filo_conn in self.filo_connections.values():
            try:
                filo_conn.sendall(serialized_msg)
            except:
                pass
     
        for sorti_conn in self.sorti_connections.values():
            try:
                sorti_conn.sendall(serialized_msg)
            except:
                pass
    
    def close(self):
        """Tüm bağlantıları ve sunucuları kapatır"""
        self.game_over = True
        
        for conn in list(self.radar_connections.values()):
            try:
                conn.close()
            except:
                pass
        
        for conn in list(self.ucak_connections.values()):
            try:
                conn.close()
            except:
                pass
        
        for conn in list(self.filo_connections.values()):
            try:
                conn.close()
            except:
                pass
        
        for conn in list(self.sorti_connections.values()):
            try:
                conn.close()
            except:
                pass
        
        self.radar_server.close()
        self.ucak_server.close()
        
        print("Merkez kapatıldı.")

if __name__ == "__main__":
    merkez = Merkez()
    
    try:
        print("Haberleşme Ağı Merkezi başlatılıyor...")
        merkez.start_servers()
        
        print("Merkez aktif. Çıkmak için CTRL+C tuşlarına basın.")
        
        while not merkez.game_over:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("Merkez kapatılıyor...")
    
    finally:
        merkez.close()
