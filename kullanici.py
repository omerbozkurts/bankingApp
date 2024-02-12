import random
import os
import hashlib
import datetime

class Kullanici:
    def __init__(self):
        self.kullaniciNo=0
        self.tcNo=0
        self.ad="no info"
        self.soyad='no info'
        self.dogumTarihi="0"
        self.sifre=0
        self.role='customer'
        

    def kayitOl(self,tcNo,ad,soyad,dogumTarihi,sifre):
        isTcTrue=self.checkTc(tcNo)
        if isTcTrue:
            self.tcNo=self.hashing(tcNo)
            self.ad=ad
            self.soyad=soyad
            if self.yasKontrol(dogumTarihi):
                self.dogumTarihi=dogumTarihi
                if self.checkSifre(sifre):
                    self.sifre=self.hashing(sifre)
                    return self.dokumanaKaydet(tcNo)
                else:
                     return("Hatali Sifre Girildi Kayit Olusturulamadi")
            else:
               return "Yas 18'den Kucuk Olamaz"
        else:
            return "Hatali Tc Girildi Kayit Olusturulamadi"
            

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
        
    def dokumanaKaydet(self,tcNo):
        if not os.path.isfile("kullanici.txt") or self.search(self.tcNo,'kullaniciTc')== False:
            kayitTarihi=datetime.date.today()
            kullaniciN=self.kullaniciNoAta()
            with open('kullanici.txt',"a+",encoding='utf-8') as file:
                self.ad=self.ad.replace(' ','*')
                file.write(f'{kullaniciN} {self.tcNo} {self.ad} {self.soyad} {self.dogumTarihi} {self.sifre} {self.role} {kayitTarihi}\n')
                return ("Kayit Basarili")
        else:
            return (f"{tcNo} Tc numarali {self.ad} {self.soyad} Zaten Kayitlidir")
                    
    
    def kullaniciNoAta(self):
        chckNo=random.randint(10**8,10**9)
        src=self.search(chckNo,'kullaniciNo')
        if not os.path.isfile("kullanici.txt"):
            return chckNo
        elif src is False:
            return chckNo
        else:
            return self.kullaniciNoAta()
    
    def search(self,searchInfo,searchType):
        flag=0
        if not os.path.isfile("kullanici.txt"):
            #print('bu isimde bir dosya olmadigi icin kontrol saglanamadi')
            return False
        with open("kullanici.txt",'r',encoding='utf-8') as file:
            for kullanici in file:
                kullanici=kullanici.split()
                kullaniciN=int(kullanici[0])
                kullaniciTc=kullanici[1]
                kullaniciAd=kullanici[2].split('*')
                kullaniciSoyad=kullanici[3]
                kullaniciDogum=kullanici[4]
                kullaniciSifre=kullanici[5]
                kullaniciRol=kullanici[6]
                kullaniciKayit=kullanici[7]
                if searchType=='kullaniciNo' and searchInfo==kullaniciN:
                    flag=1
                    return True
                elif searchType=='kullaniciTc' and searchInfo==kullaniciTc:
                    flag=1
                    return True
                elif searchType=='kullaniciAd' and searchInfo==kullaniciAd:
                    flag=1
                    return True
                elif searchType=='kullaniciSoyad' and searchInfo==kullaniciSoyad:
                    flag=1
                    return True
                elif searchType=='kullaniciDogum' and searchInfo==kullaniciDogum:
                    flag=1
                    return True
                elif searchType=='kullaniciRol' and searchInfo==kullaniciRol:
                    flag=1
                    return True
                elif searchType=='kullaniciSifre' and searchInfo==kullaniciSifre:
                    flag=1
                    return True
                elif searchType=='kullaniciKayit' and searchInfo==kullaniciKayit:
                    flag=1
                    return True
            if flag==0:
                return False
    def girisYap(self,girisTc,girisSifre):
        if self.search(self.hashing(girisTc),"kullaniciTc") and self.search(self.hashing(girisSifre),'kullaniciSifre'):
            return True
        else:
            return False
        
    def hashing(self,txt):
        txt=str(txt)
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

# kullanici=Kullanici()
# print(kullanici.tcNo)
# print(kullanici.sifre)
# print(kullanici.role)
    