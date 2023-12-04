from tkinter import *

class Bank:
    def __init__(self,master):
        self.master=master

        screenWidth= master.winfo_screenwidth()
        screenHeight= master.winfo_screenheight()

        canvas= Canvas(master,height=screenHeight*0.9,width=screenWidth*0.3)
        self.mainFrame=Frame(master,width=canvas.winfo_reqwidth(),height=canvas.winfo_reqheight())
        self.mainFrame.pack()

        self.karsilama(canvas)
        self.girisEkran()
        
        
        canvas.pack()

    def karsilama(self,canvas):
        self.startFrame=Frame(self.mainFrame,bg='black',width=canvas.winfo_reqwidth(),height=canvas.winfo_reqheight())
        self.startLabel=Label(self.startFrame,text="Hoş Geldiniz",fg='white',bg='black',font= 'Hemmet 32 bold italic')      
        self.startFrame.pack() 
        self.startLabel.place(x=(self.startFrame.winfo_reqwidth()*0.22),y=(self.startFrame.winfo_reqheight()*0.45))
        self.bankNameLbl=Label(self.startFrame,text="AB Bank",fg='white',bg='black',font= 'Verdana 16 bold')      
        self.bankNameLbl.place(x=(self.startFrame.winfo_reqwidth()*0.22),y=(self.startFrame.winfo_reqheight()*0.40))
        master.after(750,self.karsilamaSil)

    def karsilamaSil(self):
        self.startLabel.pack_forget()
        self.startFrame.pack_forget()
        
    def girisEkran(self):
        girisFrame1=Frame(self.mainFrame,bg="white",width=self.mainFrame.winfo_reqwidth()*0.7,height=self.mainFrame.winfo_reqheight()*0.8)
        girisFrame1.pack(pady=250)
        girisBankaAdi=Label(girisFrame1,text="AB Bank",fg="white",bg='black',font='Verdana 18')
        girisBankaAdi.place(x=17,y=20)
        girisFrame2=Frame(girisFrame1,bg="red",width=int(girisFrame1.winfo_reqwidth()*0.9),height=int(girisFrame1.winfo_reqheight()*0.08))
        girisFrame2.place(x=17,y=80)
        girisFrame3=Frame(girisFrame1,bg="blue",width=int(girisFrame1.winfo_reqwidth()*0.9),height=int(girisFrame1.winfo_reqheight()*0.08))
        girisFrame3.place(x=17,y=140)
        girisFrame4=Frame(girisFrame1,bg="green",width=int(girisFrame1.winfo_reqwidth()*0.9),height=int(girisFrame1.winfo_reqheight()*0.08))
        girisFrame4.place(x=17,y=200)
        loginButton=Button(girisFrame4,bg="yellow",text='giris yap',width=30,height=2)
        loginButton.pack()
        girisFrame5=Frame(girisFrame1,bg="purple",width=int(girisFrame1.winfo_reqwidth()*0.9),height=int(girisFrame1.winfo_reqheight()*0.08))
        girisFrame5.place(x=17,y=260)
        

if __name__ == "__main__":
    master= Tk()
    master.title("AB Bank")
    banka = Bank(master)
    master.mainloop()
