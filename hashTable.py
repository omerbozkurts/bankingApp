from binaryTreeSirala import sirala

class HashTable:
    def __init__(self):
        self.size = 0
        self.table = [None] * self.size

    def uzunlukBul(self,dosyaKonum):
        with open(dosyaKonum,'r') as file:
            for x in file.readlines():
                self.size+=1
        self.table= [None] * self.size

    def hashFunction(self, key):
        return (key*8+5)%self.size

    def add(self, key, value):
        index = self.hashFunction(key)
        if self.table[index] is None:
            self.table[index] = [(key, value)]
        else:
            # collision
            for i in range(len(self.table[index])):
                if self.table[index][i][0] == key:
                    # var olan deger guncelle
                    self.table[index][i] = (key, value)
                    return
            self.table[index].append((key, value))

    def get(self, key):
        index = self.hashFunction(key)
        if self.table[index] is not None:
            for item in self.table[index]:
                if item[0] == key:
                    return item[1]
        raise KeyError(f"Key not found: {key}")

    
def dosyadanCek(dosyaKonum,getKey):
    table=HashTable()
    table.uzunlukBul(dosyaKonum)
    with open(dosyaKonum,'r',encoding='utf-8') as file:
        for data in file:
            key=int(data.split()[0])
            table.add(key,data)
    return table.get(getKey)

def tabloOlustur(dosyaKonum):
    table=HashTable()
    table.uzunlukBul(dosyaKonum)
    with open(dosyaKonum,'r',encoding='utf-8') as file:
        for data in file:
            key=int(data.split()[0])
            table.add(key,data)
        return table.table

def ekleDuzenle(dosyaKonum,newData):
    table=HashTable()
    table.uzunlukBul(dosyaKonum)
    with open(dosyaKonum,'r',encoding='utf-8') as file:
        for data in file.readlines():
            key=int(data.split()[0])
            newKey=newData.split()[0]
            if key!=newKey:
                table.add(key,data)
            else:
                table.add(newKey,newData)
        return table.table