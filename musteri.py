from kullanici import Kullanici
from binaryTreeSirala import sirala
import os
from hashTable import dosyadanCek
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
        self.hesaplar=[]
        sirala()
           
    def musteriGetir(self,musteriNo):
        dosya='kullanici.txt'
        kullanici=dosyadanCek(dosya,musteriNo)
        temp=kullanici
        kullanici=kullanici.split()
        self.musteriNo=int(kullanici[0])
        self.musteriTc=kullanici[1]
        self.musteriAd=kullanici[2].replace('*',' ')
        self.musteriSoyad=kullanici[3]
        self.musteriDogumTarihi=kullanici[4]
        self.musteriSifre=kullanici[5]
        self.role=kullanici[6]
        self.MusterikayitTarihi=kullanici[7]

    def musteriHesapAc(self):
        konum='musteriHesaplar/' + str(self.musteriNo) + ".txt"
        if not os.path.isfile(konum):
            self.hesapNumarasi=1
            with  open(konum,'w') as file:
                file.write(f'{self.hesapNumarasi} {self.bakiye} {self.hesapHareketleri}\n')
        else:
            with open(konum,"r+") as file:
                for line in file.readlines():
                    self.hesapNumarasi=int(line.split()[0])
                self.hesapNumarasi+=1
                file.write(f'{self.hesapNumarasi} {self.bakiye} {self.hesapHareketleri}\n')
            
    def sonHareketler(self,hareket):
        hesapHareketiSayisi=len(self.hesapHareketleri)
        if hesapHareketiSayisi<9:
            self.hesapHareketleri[10-hesapHareketiSayisi]=hareket
        else:
            for i in range(10):
                self.hesapHareketleri[9-i]=self.hesapHareketleri[9-i-1]
            self.hesapHareketleri[0]=hareket


musteri=Musteri()
musteri.musteriGetir(877291198)
print(musteri.musteriAd)
musteri.musteriHesapAc()
musteri.musteriHesapAc()