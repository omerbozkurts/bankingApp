import customtkinter as ctk 
import tkinter.messagebox as tkmb

import tkinter as tk
from musteri import Musteri


# Selecting GUI theme - dark, light , system (for system default) 
ctk.set_appearance_mode("dark") 

# Selecting color theme - blue, green, dark-blue 
ctk.set_default_color_theme("blue") 

app = ctk.CTk() 
app.geometry("400x800") 
app.title("AB Bank")

musteri=Musteri()


def karsilama():
    karsilama=ctk.CTkFrame(master=app,fg_color='transparent')
    karsilama.pack(fill='both',expand=True,pady=330)
    karsilamaBankaIsimLbl=ctk.CTkLabel(karsilama,text='AB Bank',font=('text',16))
    karsilamaBankaIsimLbl.pack(pady=5)
    karsilamaLbl=ctk.CTkLabel(karsilama,text='Hos Geldiniz',font=('Brush Script MT',32))
    karsilamaLbl.pack(pady=5,padx=10)
    #karsilama.after(1000,bankaIsimGoster)
    karsilama.after(1000,girisEkrani)
    karsilama.after(1000,lambda:karsilama.destroy())


def bankaIsimGoster():
    label = ctk.CTkLabel(app,text="AB Bank") 
    label.pack(pady=20)
    

def girisEkrani():

 
    def girisYap():
        if musteri.girisYap(int(kullaniciAdi.get()),int(parola.get())):
            frame.destroy()
            label.destroy() 
            girisLbl=ctk.CTkLabel(app,text='Giris Basarili',font=('text',16))
            girisLbl.pack(pady=150)
            girisLbl.after(1000,anasayfa)
            girisLbl.after(1000,lambda:girisLbl.destroy())    
        else:
            girisHataLbl=ctk.CTkLabel(frame,text='Hatali Kullanici Adi Veya Sifre')
            girisHataLbl.pack(pady=12,padx=10)
            girisHataLbl.after(1000,lambda:girisHataLbl.destroy())

    def kayit():
        frame.destroy()
        kayitSayfasi=ctk.CTkFrame(app) 
        kayitSayfasi.pack(pady=20,padx=40,fill='both',expand=True) 
        kayitSayfasiLbl=ctk.CTkLabel(kayitSayfasi,text="Kayıt Ol")
        kayitSayfasiLbl.pack(pady=12,padx=10)

        kullaniciTc= ctk.CTkEntry(kayitSayfasi,placeholder_text="Tc Kimlik No") 
        kullaniciTc.pack(pady=12,padx=10)

        kullaniciAd= ctk.CTkEntry(kayitSayfasi,placeholder_text="Isim") 
        kullaniciAd.pack(pady=12,padx=10)

        kullaniciSoyad= ctk.CTkEntry(kayitSayfasi,placeholder_text="Soyisim") 
        kullaniciSoyad.pack(pady=12,padx=10)

        kullaniciDogum= ctk.CTkEntry(kayitSayfasi,placeholder_text="Dogum Tarihi") 
        kullaniciDogum.pack(pady=12,padx=10)

        kullaniciSifre= ctk.CTkEntry(kayitSayfasi,placeholder_text="Sifre",show="*") 
        kullaniciSifre.pack(pady=12,padx=10)

        def kayitDurum():
            deger=musteri.kayitOl(int(kullaniciTc.get()),
                              str(kullaniciAd.get()),
                              str(kullaniciSoyad.get()),
                              str(kullaniciDogum.get()),
                              int(kullaniciSifre.get()))
            kayitDurumlbl=ctk.CTkLabel(kayitSayfasi,text=deger)
            kayitDurumlbl.pack(pady=12,padx=10)
            kayitDurumlbl.after(1500,lambda:kayitDurumlbl.destroy())
            def kayitBasarili():
                kayitBasariliLbl=ctk.CTkLabel(app,text='Kayit Basarili \n\n\n\nYonlendiriliyorsunuz',font=('text',16))
                kayitBasariliLbl.after(1000,lambda:kayitBasariliLbl.pack(pady=150))
                kayitBasariliLbl.after(1000,lambda:kayitSayfasi.destroy())
                kayitBasariliLbl.after(3000,girisEkrani)
                kayitBasariliLbl.after(3000,lambda:kayitBasariliLbl.destroy())
                #kayitDurumlbl.after(1000,lambda:kayitDurumlbl.destroy())
            if deger=="Kayit Basarili":
                kayitBasarili()
        kayitOlB = ctk.CTkButton(kayitSayfasi,text='Kayıt Ol',command=kayitDurum)
        kayitOlB.pack(pady=12,padx=10)

        

        geriDonB = ctk.CTkButton(master=kayitSayfasi,text='Geri Dön',command= lambda:kayitSayfaKapat(kayitSayfasi)) 
        geriDonB.pack(pady=12,padx=10)
    
    def kayitSayfaKapat(ks):
        ks.destroy()
        girisEkrani()
            
    frame = ctk.CTkFrame(master=app) 
    frame.pack(pady=20,padx=40,fill='both',expand=True)    

    label = ctk.CTkLabel(frame,text='Giriş Sayfası') 
    label.pack(pady=12,padx=10) 


    kullaniciAdi= ctk.CTkEntry(frame,placeholder_text="Tc Kimlik No") 
    kullaniciAdi.pack(pady=12,padx=10) 

    parola= ctk.CTkEntry(frame,placeholder_text="Mobil Bankacılık Şifresi",show="*") 
    parola.pack(pady=12,padx=10) 


    girisYapB = ctk.CTkButton(frame,text='Giriş Yap',command=girisYap) 
    girisYapB.pack(pady=12,padx=10)

    kayitOlB = ctk.CTkButton(frame,text='Kayıt Ol',command=kayit)
    kayitOlB.pack(pady=12,padx=10)


def anasayfa():
    anasayfa=ctk.CTkLabel(app,text='anasayfa')
    anasayfa.pack(pady=12,padx=10)


karsilama()


app.mainloop()