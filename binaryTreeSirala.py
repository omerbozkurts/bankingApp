import os

class Node:
    def __init__(self, musteriNo, musteriBilgisi):
        self.musteriNo = musteriNo
        self.musteriBilgisi = musteriBilgisi
        self.left = None
        self.right = None

root = None

def insert(root, musteriNo, musteriBilgisi):
    if root is None:
        return Node(musteriNo, musteriBilgisi) 
    if musteriNo < root.musteriNo:
        root.left = insert(root.left, musteriNo, musteriBilgisi)
    elif musteriNo > root.musteriNo:
        root.right = insert(root.right, musteriNo, musteriBilgisi)
    return root



#in-order traversal ile agacta gezerek gelen bilgileri sirasiyla dosyaya kaydeder
def dosyayaKaydet(root):
    if root:
        dosyayaKaydet(root.left)
        kullanici=root.musteriBilgisi
        with open("kullanici2.txt",'+a',encoding='utf-8') as file:
            file.write(f'{root.musteriNo} {kullanici[0]} {kullanici[1]} {kullanici[2]} {kullanici[3]} {kullanici[4]} {kullanici[5]} {kullanici[6]}\n')
        dosyayaKaydet(root.right)
       
with open("kullanici.txt", 'r', encoding='utf-8') as file:
    for kullanici in file:
        kullanici = kullanici.split()
        musteriNo = int(kullanici[0])
        musteriBilgisi = kullanici[1:]
        root = insert(root, musteriNo, musteriBilgisi)


def sirala():
    dosyayaKaydet(root)
    os.remove('kullanici.txt')
    os.rename('kullanici2.txt','kullanici.txt')
