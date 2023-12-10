class Node:
    def __init__(self, musteri_no, musteri_bilgisi):
        self.musteri_no = musteri_no
        self.musteri_bilgisi = musteri_bilgisi
        self.left = None
        self.right = None

def insert(root, musteri_no, musteri_bilgisi):
    if root is None:
        return Node(musteri_no, musteri_bilgisi)
    
    if musteri_no < root.musteri_no:
        root.left = insert(root.left, musteri_no, musteri_bilgisi)
    elif musteri_no > root.musteri_no:
        root.right = insert(root.right, musteri_no, musteri_bilgisi)
    
    return root

def inorder_traversal(root):
    if root:
        inorder_traversal(root.left)
        kullanici=root.musteri_bilgisi
        with open("musteri_bilgileri.txt",'+a',encoding='utf-8') as file:
            file.write(f'{root.musteri_no} {kullanici[0]} {kullanici[1]} {kullanici[2]} {kullanici[3]} {kullanici[4]} {kullanici[5]} {kullanici[6]}\n')
        #print(root.musteri_no, root.musteri_bilgisi)
        inorder_traversal(root.right)

# Başlangıçta root'u belirle
root = None

with open("kullanici.txt", 'r', encoding='utf-8') as file:
    for kullanici in file:
        kullanici = kullanici.split()
        musteri_no = int(kullanici[0])
        musteri_bilgisi = kullanici[1:]
        
        # Ağaca düğüm ekle
        root = insert(root, musteri_no, musteri_bilgisi)

# Ağacı inorder olarak dolaş ve yazdır
inorder_traversal(root)
