import customtkinter as ctk 
import tkinter.messagebox as tkmb
from kullanici import Kullanici 




# Selecting GUI theme - dark, light , system (for system default) 
ctk.set_appearance_mode("dark") 

# Selecting color theme - blue, green, dark-blue 
ctk.set_default_color_theme("blue") 

app = ctk.CTk() 
app.geometry("400x800") 
app.title("AB Bank")
kullanici=Kullanici()

label = ctk.CTkLabel(app,text="AB Bank") 

label.pack(pady=20) 



def girisEkrani():

    def girisYap():
        if kullanici.girisYap(int(kullaniciAdi.get()),int(parola.get())):
            uygulamaEkrani=ctk.CTkToplevel(app)
            uygulamaEkrani.title('AB Bank')
            uygulamaEkrani.geometry('400x800')
            uygulamaEkrani.pack()
        else:
            print('hatali kullanici adi veya sifre')

    def kayit():
        frame.destroy()
        kayitSayfasi=ctk.CTkFrame(app) 
        kayitSayfasi.pack(pady=20,padx=40,fill='both',expand=True) 
        ctk.CTkLabel(kayitSayfasi,text="Kayıt Ol").pack()
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


girisEkrani()

app.mainloop()