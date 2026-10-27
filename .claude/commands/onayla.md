---
description: Son görevi onayla; değişiklikleri commit'leyip GitHub'a (origin/main) pushla
argument-hint: "[isteğe bağlı commit notu]"
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*), Bash(git log:*)
---
Kullanıcı son görevi onayladı. Şu adımları uygula:

1. `git status --short` ve `git diff --stat` ile değişiklikleri incele.
2. Yalnızca bu görevde yapılan değişiklikleri stage'le (`git add <dosyalar>`). `__pycache__/`, `*.pyc`,
   geçici dosyalar ve görevle ilgisiz değişiklikleri ekleme.
3. İngilizce, kısa ve açıklayıcı bir commit mesajı yaz; kullanıcı not verdiyse dikkate al: $ARGUMENTS
   Mesajın sonuna oturumdaki attribution satırını ekle.
4. `git push origin main` ile pushla.
5. Kullanıcıya commit hash'ini ve neyin pushlandığını tek satırda Türkçe bildir.

Commit edilecek değişiklik yoksa bunu söyle ve dur. Push başarısız olursa hatayı göster, zorla push (`--force`) yapma.
