import time
import random
import os

class Kullanici:
    def __init__(self):
        self.musteriNo=0
        self.tcNo=0
        self.ad="no info"
        self.soyad='no info'
        self.dogumTarihi="0"
        self.sifre=0
        

    def kayitOl(self,tcNo,ad,soyad,dogumTarihi,sifre):
        isTcTrue=self.checkTc(tcNo)
        if isTcTrue:
            self.tcNo=tcNo
            self.ad=ad
            self.soyad=soyad
            self.dogumTarihi=dogumTarihi
            if self.checkSifre(sifre):
                self.sifre=sifre
                self.dokumanaKaydet()
                print("kayit basarili")
            else:
                return "hatali sifre girildi kayit olusturulamadi"
        else:
            return "hatali tc girildi kayit olusturulamadi"
            

    def checkTc(self,tcNo):
        if isinstance(tcNo,int) and 10**10<=tcNo<10**11:
            toplam=0
            tcTemp=tcNo
            for i in range(10):
                toplam+= tcTemp//(10**(10-i))
                tcTemp=tcTemp%(10**(10-i))
            if toplam%10==tcTemp:
                return True
            else:
                return False
        else:
            return False
        
    def checkSifre(self,sifre):
        if isinstance(sifre,int) and 10**5<=sifre<10**6:
            return True
        else:
            return False
        
    def dokumanaKaydet(self):
        kayitTarihi=time.ctime()
        musteriN=self.musteriNoAta()
        with open('kullanici.txt',"a+",encoding='utf-8') as file:
            self.ad=self.ad.replace(' ','*')
            file.write(f'{musteriN} {self.tcNo} {self.ad} {self.soyad} {self.dogumTarihi} {self.sifre} {kayitTarihi}\n')
    
    def musteriNoAta(self):
        chckNo=int(random.random()*(10**9))
        src=self.search(chckNo,'musteriNo')
        if src:
            return chckNo
        else:
            return self.musteriNoAta()
    
    def search(self,searchInfo,searchType):
        if not os.path.isfile("kullanici.txt"):
            return 'bu isimde bir dosya olmadigi icin kontrol saglanamadi'
        with open("kullanici.txt",'r',encoding='utf-8') as file:
            for kullanici in file:
                musteri=kullanici.split()
                musteriN=musteri[0]
                musteriTc=musteri[1]
                musteriAd=musteri[2].split('*')
                musteriSoyad=musteri[4]
                musteriDogum=musteri[5]
                musteriSifre=musteri[6]
                musteriKayit=musteri[7] + ' ' + musteri[8] + ' ' + musteri[9] + ' ' + musteri[10] + ' ' + musteri[11]
                if searchType=='musteriNo' and searchInfo==musteriN:
                    return True
                elif searchType=='musteriTc' and searchInfo==musteriTc:
                    return True
                elif searchType=='musteriAd' and searchInfo==musteriAd:
                    return True
                elif searchType=='musteriSoyad' and searchInfo==musteriSoyad:
                    return True
                elif searchType=='musteriDogum' and searchInfo==musteriDogum:
                    return True
                elif searchType=='musteriSifre' and searchInfo==musteriSifre:
                    return True
                elif searchType=='musteriKayit' and searchInfo==musteriKayit:
                    return True

kisi1= Kullanici()
tc=15284679002
kisiAd="omer can"
kisiSoyad="bozkurt"
kisiDogum="15/08/2002"
kisiSifre=106018
print(kisi1.kayitOl(tc,kisiAd,kisiSoyad,kisiDogum,kisiSifre))
            
    