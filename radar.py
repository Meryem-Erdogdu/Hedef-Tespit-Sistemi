import random
import time
import socket
import pickle
import threading

class Radar:
    def __init__(self, host='localhost', port=5000):
        self.koordinat = (0, 0, 0)
        self.asker = 0
        self.tank = 0
        self.ucak = 0
        self.hedef = (0, 0, 0)
        
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        
    def connect_to_center(self):
        try:
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"Radar merkeze bağlandı: {self.host}:{self.port}")
            
            # Sürekli tarama yapma ve merkeze gönderme
            threading.Thread(target=self.continuous_scan, daemon=True).start()
            
        except ConnectionRefusedError:
            print("Bağlantı reddedildi. Merkez çalışıyor mu?")
            self.connected = False
    
    def ucak_goruldu(self):
        self.ucak += 1
        
    def ucak_imha_edildi(self):
        self.ucak -= 1
        
    def tank_goruldu(self):
        self.tank += 1
        
    def tank_imha_edildi(self):
        self.tank -= 1
        
    def asker_goruldu(self):
        self.asker += 1
        
    def asker_imha_edildi(self):
        self.asker -= 1
        
    def koordinat_tarama(self):
        cisim = random.randint(1, 9)
        koord = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 20))

        if cisim < 6 and cisim > 3:
            print('')
            print('!!!! DİKKAT DİKKAT DİKKAT !!!!')
            print(f' {koord} koordinatta düşman UÇAĞI tespit edildi')
            print('!!!! ------- DİKKAT DİKKAT DİKKAT -------!!!!')
            print('')
            self.ucak_goruldu()
            self.hedef = koord
        elif cisim < 3 and cisim > 1:
            print('')
            print('!!!! DİKKAT DİKKAT DİKKAT !!!!')
            print(f' {koord} koordinatta düşman TANKI tespit edildi')
            print('!!!! ------- DİKKAT DİKKAT DİKKAT -------!!!!')
            print('')
            self.tank_goruldu()
            self.hedef = koord
        elif cisim < 7 and cisim > 5:
            print('')
            print('!!!! DİKKAT DİKKAT DİKKAT !!!!')
            print(f' {koord} koordinatta düşman ASKERİ tespit edildi')
            print('!!!! ------- DİKKAT DİKKAT DİKKAT -------!!!!')
            print('')
            self.asker_goruldu()
            self.hedef = koord
        else:
            print(f'{koord} temiz')
            return 0

        if self.connected and cisim != 0:
            threat_data = {
                'type': 'threat',
                'coordinates': koord,
                'threat_type': 'ucak' if 3 < cisim < 6 else 'tank' if 1 < cisim < 3 else 'asker'
            }
            try:
                self.socket.sendall(pickle.dumps(threat_data))
                print("Tehdit bilgisi merkeze gönderildi.")
            except:
                print("Merkeze veri gönderimi sırasında hata oluştu.")
                self.connected = False
            
        return cisim
    
    def continuous_scan(self):
        """Sürekli tarama yapan ve sonuçları merkeze ileten metod"""
        while self.connected:
            self.koordinat_tarama()
            time.sleep(3)  # Her 3 saniyede bir tarama yap
            
    def close(self):
        """Bağlantıyı kapatır"""
        if self.connected:
            self.socket.close()
            self.connected = False
            
if __name__ == "__main__":
    radar = Radar(port=5000)
    try:
        radar.connect_to_center()
        
        if radar.connected:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("Radar kapatılıyor...")
    finally:
        radar.close()
