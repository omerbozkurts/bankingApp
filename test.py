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



    
def anasayfa(kTc):
    musteri.musteriGetir(kTc)
    musteri.hesaplariGetir()
    anaHesap=musteri.hesaplar[0]
    anaHesapTur=anaHesap.split()[-3].replace("*"," ")
    anaHesapAd=anaHesap.split()[-4].replace('*',' ')
    anaHesapBakiye=anaHesap.split()[1]
    anasayfa=ctk.CTkLabel(app,text=f'Iyi gunler, {musteri.musteriAd} {musteri.musteriSoyad}',font=('text',16))
    anasayfa.pack(pady=5,padx=5)

    tabview = ctk.CTkTabview(app,fg_color='transparent',width=360)
    tabview.place(x=20,y=50)
    tabview.add("Anasayfa") 
    tabview.add("Hesaplar")
    tabview.add("Para Gonder")  
    tabview.add('YZ Bot')
    tabview.set("Anasayfa")  

    hesapBilgi=ctk.CTkFrame(tabview.tab("Anasayfa"))
    hesapBilgi.pack(pady=20,padx=5,fill='both')
    hesapTurLbl=ctk.CTkLabel(hesapBilgi,text=f'{anaHesapTur}',font=('text',18))
    hesapTurLbl.place(y=5,x=10)
    hesapAdLbl=ctk.CTkLabel(hesapBilgi,text=f'{anaHesapAd}',font=('text',14))
    hesapAdLbl.place(y=50,x=10)
    hesapBakiyeLbl=ctk.CTkLabel(hesapBilgi,text=f'Bakiye: ',font=('text',18))
    hesapBakiyeLbl.place(x=80,y=160)
    hesapBakiyeMiktarLbl=ctk.CTkLabel(hesapBilgi,text=f'{anaHesapBakiye}',font=('text',36))
    hesapBakiyeMiktarLbl.place(x=180,y=149)
    tlYazisiLbl=ctk.CTkLabel(hesapBilgi,text='.00 TL',font=('text',18))
    tlYazisiLbl.place(x=260,y=160)
    kartBilgi=ctk.CTkFrame(tabview.tab("Anasayfa"))
    kartBilgi.pack(pady=20,padx=5,fill='both')
    bankaIsim=ctk.CTkLabel(master=kartBilgi,text='T.C. AB Bank',font=('text',16))
    bankaIsim.place(x=10,y=5)
    kartTur=ctk.CTkLabel(master=kartBilgi,text="TL Kart",font=('Brush Script MT',20))
    kartTur.place(x=260,y=5)
    kartNo=ctk.CTkLabel(master=kartBilgi,text='1234 5678 9012 3456',font=('text',24))
    kartNo.place(x=40,y=110)
    mNoLbl=ctk.CTkLabel(master=kartBilgi,text=f'{musteri.musteriNo}')
    mNoLbl.place(x=10,y=150)
    mNameLbl=ctk.CTkLabel(master=kartBilgi,text=f'{musteri.musteriAd} {musteri.musteriSoyad}')
    mNameLbl.place(x=10,y=170)

    
anasayfa(15284679002)


app.mainloop()