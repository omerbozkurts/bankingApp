from kullanici import Kullanici
from binaryTreeSirala import sirala
import os

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
        self.vadesizHesapAdi='Vadesi Tl Hesabi'
        self.vadeliHesapAdi='Vadeli Tl Hesabi'
        self.krediHesapAdi='Kredi Hesabi'
        self.hesapNumarasi=0
        self.hesapHareketleri=[0,0,0,0,0,0,0,0,0,0]
        sirala()
        
        
    
    def musteriGetir(self,tc):
        with open("kullanici.txt",'r',encoding='utf-8') as file:
            for kullanici in file:
                if kullanici.split()[1]==Kullanici.hashing(self,tc):
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

    def musteriHesap(self):
        konum='musteriHesaplar/' + str(self.musteriNo) + ".txt"
        geciciKonum='musteriHesaplar/' + str(self.musteriNo) + "2.txt"
        if not os.path.isfile(konum):
            with  open(konum,'w') as file:
                file.write(f'{self.hesapNumarasi} {self.bakiye} {self.hesapHareketleri}\n')
        else:
            with open(geciciKonum,"a+") as file:
                file.write(f'{self.hesapNumarasi} {self.bakiye} {self.hesapHareketleri}\n')
            os.remove(konum)
            os.rename(geciciKonum,konum)

    def sonHareketler(self,hareket):
        hesapHareketiSayisi=len(self.hesapHareketleri)
        if hesapHareketiSayisi<9:
            self.hesapHareketleri[10-hesapHareketiSayisi]=hareket
        else:
            for i in range(10):
                self.hesapHareketleri[9-i]=self.hesapHareketleri[9-i-1]
            self.hesapHareketleri[0]=hareket

