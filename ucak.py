import socket
import pickle
import time
import threading

class Ucak:
    def __init__(self, ucak_id, ucak_turu, host='localhost', merkez_port=5001):
        self.ucak_id = ucak_id
        self.ucak_turu = ucak_turu
        self.durum = 'bekleme'
        self.koordinat = (0, 0, 0)

        self.host = host
        self.merkez_port = merkez_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        
        self.command_thread = None
    
    def connect_to_center(self):
        """Merkeze bağlanır ve komutları dinlemeye başlar"""
        try:
            self.socket.connect((self.host, self.merkez_port))
            self.connected = True
            print(f"{self.ucak_id} nolu {self.ucak_turu} merkeze bağlandı")
            
            identity = {
                'type': 'registration',
                'ucak_id': self.ucak_id,
                'ucak_turu': self.ucak_turu
            }
            self.socket.sendall(pickle.dumps(identity))

            self.command_thread = threading.Thread(target=self.listen_for_commands, daemon=True)
            self.command_thread.start()
            
            return True
        except ConnectionRefusedError:
            print(f"{self.ucak_id} nolu {self.ucak_turu} merkeze bağlanamadı.")
            return False
    
    def listen_for_commands(self):
        """Merkezden gelen komutları dinler"""
        while self.connected:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                
                command = pickle.loads(data)
                if command['type'] == 'move':
                    x, y, z = command['coordinates']
                    self.koordinata_git(x, y, z)
                    
                elif command['type'] == 'attack':
                    print(f"{self.ucak_id} nolu {self.ucak_turu} saldırı komutu aldı.")
                    hedef = command['coordinates']
                    self.saldiri_yap(hedef)
                    
                elif command['type'] == 'status_request':
                    self.durum_bildir()
            
            except Exception as e:
                print(f"Komut dinleme hatası: {e}")
                self.connected = False
                break
    
    def koordinata_git(self, x, y, z):
        """Verilen koordinata gider"""
        print(f"{self.ucak_id} nolu {self.ucak_turu} ({self.koordinat}) konumundan ({x},{y},{z}) konumuna gidiyor.")
        self.durum = 'hareket halinde'
   
        time.sleep(2) 
        
        self.koordinat = (x, y, z)
        self.durum = 'hedefte'
        print(f"{self.ucak_id} nolu {self.ucak_turu} ({x},{y},{z}) konumuna ulaştı.")

        if self.connected:
            status = {
                'type': 'status_update',
                'ucak_id': self.ucak_id,
                'status': 'arrived',
                'coordinates': self.koordinat
            }
            self.socket.sendall(pickle.dumps(status))
    
    def saldiri_yap(self, hedef):
        """Hedefe saldırı yapar"""
        self.durum = 'saldırıyor'
        print(f"{self.ucak_id} nolu {self.ucak_turu} {hedef} koordinatına saldırıyor...")
        
        time.sleep(2)
        
        import random
        success = random.random() > 0.3 
        
        if success:
            print(f"{self.ucak_id} nolu {self.ucak_turu}: Hedef başarıyla imha edildi!")
            result = 'success'
        else:
            print(f"{self.ucak_id} nolu {self.ucak_turu}: Hedef ıskalandı!")
            result = 'failed'
        
        self.durum = 'görev tamamlandı'

        if self.connected:
            attack_result = {
                'type': 'attack_result',
                'ucak_id': self.ucak_id,
                'target': hedef,
                'result': result
            }
            self.socket.sendall(pickle.dumps(attack_result))
    
    def durum_bildir(self):
        """Mevcut durumu merkeze bildirir"""
        if self.connected:
            status = {
                'type': 'status',
                'ucak_id': self.ucak_id,
                'status': self.durum,
                'coordinates': self.koordinat
            }
            self.socket.sendall(pickle.dumps(status))
    
    def ucak_bilgisi(self):
        """Uçak bilgisini ekrana yazdırır"""
        print(f'{self.ucak_id} nolu {self.ucak_turu} {self.koordinat} koordinatta {self.durum} vaziyetindedir')
    
    def close(self):
        """Bağlantıyı kapatır"""
        if self.connected:
            self.socket.close()
            self.connected = False

if __name__ == "__main__":
    ucak_id = input("Uçak ID girin: ")
    ucak_turu = input("Uçak türü girin (F16/F22/siha): ")
    
    ucak = Ucak(ucak_id, ucak_turu)
    
    try:
        if ucak.connect_to_center():
            print(f"{ucak_id} nolu {ucak_turu} hazır beklemede...")

            while ucak.connected:
                time.sleep(1)
        else:
            print("Merkeze bağlanılamadı. Program sonlandırılıyor.")
    except KeyboardInterrupt:
        print("Uçak kapatılıyor...")
    finally:
        ucak.close()
