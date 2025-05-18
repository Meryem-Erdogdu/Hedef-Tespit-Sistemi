import time
import random
import threading
import socket
import pickle

class Sorti:
    def __init__(self, sorti_id, ucak, hedef, host='localhost', port=5003):
        self.sorti_id = sorti_id
        self.ucak = ucak
        self.hedef = hedef
        self.vaziyet = 'planlandı'
        self.sonuc = None
        
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.merkez_port = 5001
    
    def connect_to_center(self):
        """Merkeze bağlanır"""
        try:
            self.socket.connect((self.host, self.merkez_port))
            self.connected = True
            print(f"Sorti {self.sorti_id} merkeze bağlandı")
            
            identity = {
                'type': 'registration',
                'entity': 'sorti',
                'sorti_id': self.sorti_id,
                'ucak_id': self.ucak.ucak_id,
                'hedef': self.hedef
            }
            self.socket.sendall(pickle.dumps(identity))
            
            threading.Thread(target=self.listen_to_center, daemon=True).start()
            
            return True
        except ConnectionRefusedError:
            print("Merkeze bağlanılamadı.")
            return False
    
    def listen_to_center(self):
        """Merkezden gelen komutları dinler"""
        while self.connected:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                
                command = pickle.loads(data)
                if command['type'] == 'start_sortie':
                    threading.Thread(target=self.hedefi_imha_et).start()
                
                elif command['type'] == 'cancel_sortie':
                    self.vaziyet = 'iptal edildi'
                    self.update_status()
                    print(f"Sorti {self.sorti_id} iptal edildi!")
            
            except Exception as e:
                print(f"Merkez dinleme hatası: {e}")
                self.connected = False
                break
    
    def update_status(self):
        """Merkeze durumu bildirir"""
        if self.connected:
            status = {
                'type': 'sortie_status',
                'sorti_id': self.sorti_id,
                'status': self.vaziyet,
                'ucak_id': self.ucak.ucak_id,
                'hedef': self.hedef,
                'sonuc': self.sonuc
            }
            try:
                self.socket.sendall(pickle.dumps(status))
            except:
                print("Durum bildirimi sırasında hata oluştu")
                self.connected = False
    
    def hedefi_imha_et(self):
        """Hedefe saldırı operasyonunu yürütür"""
        self.vaziyet = 'görev başladı'
        self.update_status()
        
        print(f'Sorti {self.sorti_id}: İmha için uçak havalandı, hedef {self.hedef} koordinatına doğru gidiliyor.')
        
        if self.connected:
            mission_start = {
                'type': 'mission_started',
                'sorti_id': self.sorti_id,
                'ucak_id': self.ucak.ucak_id,
                'hedef': self.hedef
            }
            self.socket.sendall(pickle.dumps(mission_start))
        
        time.sleep(2) 
        
        print('Hedefe kitlendi.....atış yapılıyor.....')
        self.vaziyet = 'bombalıyor'
        self.update_status()
        
        time.sleep(1)
        atis = random.random()
        self.ucak.koordinat = self.hedef
        
        if atis < 0.3: 
            print('Merkez: Hedef ıskalandı ..... ')
            time.sleep(1)
            print(f'Pilot {self.ucak.ucak_id}: ..Merkez tuzağa düştüm......Eşhedü.... ')
            time.sleep(1)
            print(f'Merkez: ...Tüm birimlere {self.ucak.ucak_id} nolu {self.ucak.ucak_turu} uçağımız düşürüldü')
            self.vaziyet = 'başarısız'
            self.sonuc = 0
        else:
            print('Merkez: Hedef başarıyla imha edildi.')
            self.vaziyet = 'başarılı'
            self.sonuc = 1
        
        self.update_status()
        
        return self.sonuc
    
    def close(self):
        """Bağlantıyı kapatır"""
        if self.connected:
            self.socket.close()
            self.connected = False

if __name__ == "__main__":
    from ucak import Ucak
    
    print("Sorti yönetimi başlatılıyor...")
    
    test_ucak = Ucak("T001", "F16")
    
    hedef_koord = (45, 67, 12)
    sorti = Sorti("S100", test_ucak, hedef_koord)
    
    try:
        if sorti.connect_to_center():
            print(f"Sorti {sorti.sorti_id} hazır, merkeze bağlı.")
            
            while sorti.connected:
                time.sleep(1)
        else:
            print("Merkeze bağlanılamadı. Program sonlandırılıyor.")
    
    except KeyboardInterrupt:
        print("Sorti yönetimi kapatılıyor...")
    
    finally:
        sorti.close()
