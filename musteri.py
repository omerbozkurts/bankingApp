from kullanici import Kullanici
import re
import ast
import os
from hashTable import dosyadanCek
from binaryTreeSirala import sirala
import random

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
        self.hesapTur='no info'
        self.hesapAdi='no info'
        self.hesapNumarasi=0
        self.hesapHareketleri=[0,0,0,0,0,0,0,0,0,0]
        self.hesaplar=[]
        sirala()
        
    def tcNoMusteriNo(self,kTc):
        with open('kullanici.txt') as file:
            for line in file.readlines():
                if Kullanici.hashing(self,kTc)==line.split()[1]:
                    return int(line.split()[0])

           
    def musteriGetir(self,kTc):
        musteriNo=self.tcNoMusteriNo(kTc)
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

    def hesaplariGetir(self):
        konum='musteriHesaplar/' + str(self.musteriNo) + ".txt"
        with open(konum,'r',encoding='utf-8') as file:
            self.hesaplar=[]
            for line in file.readlines():
                self.hesaplar.append(line)


    def musteriHesapAc(self):
        konum='musteriHesaplar/' + str(self.musteriNo) + ".txt"
        if not os.path.isfile(konum):
            self.hesapNumarasi=1
            with  open(konum,'w') as file:
                file.write(f'{self.hesapNumarasi} {self.bakiye} {self.hesapHareketleri} {self.hesapAdi} {self.hesapTur} {self.kredi} {self.krediNotu}\n')
        else:
            with open(konum,"r+") as file:
                for line in file.readlines():
                    self.hesapNumarasi=int(line.split()[0])
                self.hesapNumarasi+=1
                file.write(f'{self.hesapNumarasi} {self.bakiye} {self.hesapHareketleri} {self.hesapAdi} {self.hesapTur} {self.kredi} {self.krediNotu}\n')

    
    def vadesizHesapAc(self,hesapAd):
        self.hesapTur="Vadesiz*Tl*Hesabi"
        self.bakiye=random.randint(1000,5000)
        if hesapAd=='':
            self.hesapAdi="Vadesiz*Tl*Hesabi"
        else:
            self.hesapAdi=str(hesapAd.replace(' ','*'))
        self.musteriHesapAc()

    def vadeliHesapAc(self,hesapAd):
        self.hesapTur="Vadeli*Tl*Hesabi"
        if hesapAd=='':
            self.hesapAdi="Vadeli*Tl*Hesabi"
        else:
            self.hesapAdi=str(hesapAd.replace(' ','*'))
        self.musteriHesapAc()

    def krediHesapAc(self,hesapAd):
        self.hesapTur="Kredi*Hesabi"
        if hesapAd=='':
            self.hesapAdi="Kredi*Hesabi"
        else:
            self.hesapAdi=str(hesapAd.replace(' ','*'))
        self.musteriHesapAc()

    def paraGonder(self,gonderenTc,aliciTc,aliciMusteriNo,gonderenHesap,miktar,yontem):
            #self.musteriGetir(gonderenTc)
            gonderenDosya='musteriHesaplar/' + str(self.musteriNo) + ".txt"
            gonderenHesap=dosyadanCek(gonderenDosya,1)
            if yontem=='kendi':
                alanDosya=gonderenDosya
                aliciHesap=gonderenHesap
                self.paraAktar(gonderenDosya,alanDosya,miktar,gonderenHesap,aliciHesap)
            elif yontem=='hesapNo':
                alanDosya='musteriHesaplar/' + str(aliciMusteriNo) + ".txt"
                aliciHesap=dosyadanCek(alanDosya,1)
                self.paraAktar(gonderenDosya,alanDosya,miktar,gonderenHesap,aliciHesap)
            elif yontem=='tcNo':
                alici= Musteri()
                alici.musteriGetir(aliciTc)
                alanDosya='musteriHesaplar/' + str(alici.musteriNo) + ".txt"
                aliciHesap=dosyadanCek(alanDosya,1)
                self.paraAktar(gonderenDosya,alanDosya,miktar,gonderenHesap,aliciHesap)


    def paraAktar(self,gonderenDosya,alanDosya,miktar,gonderenHesap,alanHesap):
        
        with open(gonderenDosya,'r',encoding='utf-8') as file:
            for line in file.readlines():
                with open('musteriHesaplar/temp.txt','a+',encoding='utf-8') as tempFile:
                    if gonderenHesap[0]!=line.split()[0]:
                        tempFile.write(str(line))
                    else:
                        bakiye=int(gonderenHesap.split()[1])
                        bakiye-=miktar
                        self.sonHareketler(f'{miktar} Tl gonderildi',gonderenHesap)
                        sonKisim=' '.join(gonderenHesap.split()[-4:])
                        gonderenHesap=gonderenHesap[0]+ ' ' + str(bakiye) + ' ' + str(self.hesapHareketleri) + ' ' + sonKisim + "\n"
                        tempFile.write(str(gonderenHesap))
        os.remove(gonderenDosya)
        os.rename('musteriHesaplar/temp.txt',gonderenDosya)

        with open(alanDosya,'r',encoding='utf-8') as file:
            for line in file.readlines():
                with open('musteriHesaplar/temp.txt','a+',encoding='utf-8') as tempFile:
                    if alanHesap[0]!=line.split()[0]:
                        tempFile.write(str(line))
                    else:
                        bakiye=int(alanHesap.split()[1])
                        bakiye+=miktar
                        self.sonHareketler(f'{miktar} Tl geldi',alanHesap)
                        sonKisim=' '.join(alanHesap.split()[-4:])                   
                        alanHesap=alanHesap[0]+ ' ' + str(bakiye) + ' ' + str(self.hesapHareketleri) + ' ' + sonKisim + "\n"
                        tempFile.write(str(alanHesap))
        os.remove(alanDosya)
        os.rename('musteriHesaplar/temp.txt',alanDosya)

    def sonHareketler(self,hareket,hesap):
        hareketler=re.search(r'\[.*\]',hesap)
        hareketler=ast.literal_eval(hareketler.group())
        hesapHareketiSayisi=0
        self.hesapHareketleri=hareketler
        for i in range(10):
            if hareketler[i]!=0:
                hesapHareketiSayisi+=1
        if hesapHareketiSayisi<9:
            for i in range(hesapHareketiSayisi):
                self.hesapHareketleri[hesapHareketiSayisi-i]=self.hesapHareketleri[hesapHareketiSayisi-i-1]
            self.hesapHareketleri[0]=hareket
            
        else:
            for i in range(10):
                self.hesapHareketleri[9-i]=self.hesapHareketleri[9-i-1]
            self.hesapHareketleri[0]=hareket

    def hareketleriGetir(self,hesap):
        hesapNo=int(hesap.split()[0])
        hesap=self.hesaplar[hesapNo-1]
        hareketler=re.search(r'\[.*\]',hesap)
        hareketler=ast.literal_eval(hareketler.group())
        self.hesapHareketleri=hareketler

# musteri=Musteri()
# musteri.musteriGetir()
# musteri.vadesizHesapAc('yatirim')
# print(musteri.musteriAd)
# musteri.vadesizHesapAc('hesabim')
# musteri.vadesizHesapAc('')
# musteri.vadeliHesapAc('vadeli1')
# musteri.krediHesapAc('kredi1')
# musteri.hesaplariGetir()
# print(musteri.hesaplar[0])