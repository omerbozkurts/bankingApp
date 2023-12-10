from kullanici import Kullanici

class Musteri(Kullanici):
    def __init__(self):
        self.role='customer'
        self.krediNotu=1500
        self.bakiye=0
        self.kredi=0
        self.musteriTc=0
        self.musteriNo=0
        self.musteriAd='no info'
        self.musteriSoyad='no info'
        self.musteriDogumTarihi='no info'
        self.musteriSifre=0
        self.musteriKayitTarihi='no info'
        self.musteriGetir()
    
    def musteriGetir(self):
        with open("kullanici.txt",'r',encoding='utf-8') as file:
            for kullanici in file:
                temp=kullanici
                kullanici=kullanici.split()
                self.musteriNo=int(kullanici[0])
                self.musteriTc=kullanici[1]
                self.musteriAd=kullanici[2].split('*')
                self.musteriSoyad=kullanici[3]
                self.musteriDogumTarihi=kullanici[4]
                self.musteriSifre=kullanici[5]
                self.role=kullanici[6]
                self.MusterikayitTarihi=kullanici[7]

    def musteriSirala(self):
        print()