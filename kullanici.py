import random
import os
import hashlib
import datetime

class Kullanici:
    def __init__(self):
        self.musteriNo=0
        self.tcNo=0
        self.ad="no info"
        self.soyad='no info'
        self.dogumTarihi="0"
        self.sifre=0
        self.role='customer'
        

    def kayitOl(self,tcNo,ad,soyad,dogumTarihi,sifre):
        isTcTrue=self.checkTc(tcNo)
        if isTcTrue:
            self.tcNo=tcNo
            self.ad=ad
            self.soyad=soyad
            if self.yasKontrol(dogumTarihi):
                self.dogumTarihi=dogumTarihi
                if self.checkSifre(sifre):
                    self.sifre=sifre
                    self.dokumanaKaydet()
                else:
                     print("hatali sifre girildi kayit olusturulamadi")
                     return self.kayitOl()
            else:
                print("yas 18'den kucuk olamaz")
                return self.kayitOl()
        else:
            print("hatali tc girildi kayit olusturulamadi")
            return self.kayitOl()
            

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
        if not os.path.isfile("kullanici.txt") or self.search(self.tcNo,'musteriTc')== False:
            kayitTarihi=datetime.date.today()
            musteriN=self.musteriNoAta()
            with open('kullanici.txt',"a+",encoding='utf-8') as file:
                self.ad=self.ad.replace(' ','*')
                file.write(f'{musteriN} {self.tcNo} {self.ad} {self.soyad} {self.dogumTarihi} {self.sifre} {self.role} {kayitTarihi}\n')
                print("kayit basarili")
        else:
            print(f"{self.tcNo} tc numarali {self.ad} {self.soyad} zaten kayitlidir")        
    
    def musteriNoAta(self):
        chckNo=int(random.random()*(10**9))
        src=self.search(chckNo,'musteriNo')
        if not os.path.isfile("kullanici.txt"):
            return chckNo
        elif src is False:
            return chckNo
        else:
            return self.musteriNoAta()
    
    def search(self,searchInfo,searchType):
        flag=0
        if not os.path.isfile("kullanici.txt"):
            print('bu isimde bir dosya olmadigi icin kontrol saglanamadi')
            return False
        with open("kullanici.txt",'r',encoding='utf-8') as file:
            for kullanici in file:
                musteri=kullanici.split()
                musteriN=int(musteri[0])
                musteriTc=int(musteri[1])
                musteriAd=musteri[2].split('*')
                musteriSoyad=musteri[3]
                musteriDogum=musteri[4]
                musteriSifre=int(musteri[5])
                musteriRol=musteri[6]
                musteriKayit=musteri[7]
                if searchType=='musteriNo' and searchInfo==musteriN:
                    flag=1
                    return True
                elif searchType=='musteriTc' and searchInfo==musteriTc:
                    flag=1
                    return True
                elif searchType=='musteriAd' and searchInfo==musteriAd:
                    flag=1
                    return True
                elif searchType=='musteriSoyad' and searchInfo==musteriSoyad:
                    flag=1
                    return True
                elif searchType=='musteriDogum' and searchInfo==musteriDogum:
                    flag=1
                    return True
                elif searchType=='musteriSifre' and searchInfo==musteriSifre:
                    flag=1
                    return True
                elif searchType=='musteriKayit' and searchInfo==musteriKayit:
                    flag=1
                    return True
            if flag==0:
                return False
    def girisYap(self,girisTc,girisSifre):
        print(girisTc)
        print(girisSifre)
        if self.search(girisTc,"musteriTc") and self.search(girisSifre,'musteriSifre'):
            print('giris basarili')
            return True
        else:
            print('giris yapilamadi')
            return False
        
    def hashing(txt):
        sha256_hash = hashlib.sha256()
        sha256_hash.update(txt.encode('utf-8'))
        return sha256_hash.hexdigest()
    
    def yasKontrol(self,dogumTarih):
        dogumTarih=dogumTarih.split("/")
        dogumGun=int(dogumTarih[0])
        dogumAy=int(dogumTarih[1])        
        dogumYil=int(dogumTarih[2])
        bugunTarih=str(datetime.date.today())
        bugunTarih=bugunTarih.split('-')
        bugunGun=int(bugunTarih[2])
        bugunAy=int(bugunTarih[1])
        bugunYil=int(bugunTarih[0])
        dgm=dogumGun+dogumAy*30+dogumYil*365
        bgn=bugunGun+bugunAy*30+bugunYil*365
        if bgn-dgm<18*365:
            return False
        else:
            return True


            
    