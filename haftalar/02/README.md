# 2. hafta — AUTO görevler ve uygulamalar

[Güncel ders sunumu · PDF · 93 sayfa](Hafta-02-Sunum.pdf)

Aracı ve kamerayı tanı → görevi planla → AUTO ile uçur → görüntülerden ürün çıkar → sonucu değerlendir.

| Uygulama | AUTO görevi | İncelenecek çıktı |
| --- | --- | --- |
| Araç ve kamera | Kalkış, gimbal açıları, bekleme, iniş | RGB görüntü ve telemetri |
| Tarla ilaçlama | Grid, pompa aç/kapa, iniş | İdeal geometrik kaplama |
| 2D tarla haritalama | Grid ve mesafeli camera trigger | Renk/boy çeşitliliği olan tarlanın RGB mozaiği |
| 3D ev haritalama | İki orbit, sürekli ROI, mesafeli çekim | Gaussian Splatting modeli ve hold-out render |
| Sabit kanat gözlem | Otomatik kalkış, tarama, otomatik iniş | Hareket adaylarının görüntü kayıtları |

## Başlayın

1. İlk haftanın Windows kurulumunu tamamlayın; VS Code'dan **Git: Pull** ile depoyu güncelleyin.
2. [simulasyon/Kur.cmd](simulasyon/Kur.cmd) dosyasını bir kez çalıştırın.
3. [simulasyon/Baslat.cmd](simulasyon/Baslat.cmd) ile uygulamayı seçin.
4. Mission Planner'dan **TCP → 127.0.0.1 → 5760** ile bağlanın. İlgili `.waypoints` dosyasını **Plan → Write WPs** ile araca yazın; sensörler hazırken **AUTO → ARM** uygulayın.

Kalkış, rota, görev komutları ve iniş ArduPilot tarafından yürütülür. Python görüntü kaydı/işleme yapar; uçuş rotasını değiştirmez.

- [Kısa kurulum ve kullanım rehberi](simulasyon/README.md)
- [Derste incelenecek üç Python kodu](simulasyon/ders_kodlari/README.md)
- [Hazır 2D/3D örnekleri](ornekler/README.md)
- [Resmî kaynaklar](KAYNAKLAR.md)

Uçuşlar Windows x64, Gazebo Jetty 10.5.0 ve ArduCopter/ArduPlane 4.7.2 ile denenmiştir. Bu haftanın başlatıcıları Windows içindir; Linux üzerinde aynı uygulama akışı henüz doğrulanmamıştır. Programlar resmî kaynaklardan indirilir; hazır EXE/DLL veya ZIP paketi paylaşılmaz.

RGB mozaik gerçek NDVI ölçümü değildir. Gaussian model görünüş üretir, ölçülmüş bir triangle mesh değildir. Hareket adayları insan sınıflandırması değildir; yanlış alarm verebilir.
