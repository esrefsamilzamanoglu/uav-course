# 3. hafta — 2026 döner kanat görevleri

[Görselli sunum — PDF](Hafta-03-Sunum-Gercekci.pdf) · [Görselli ders notları — PDF](Hafta-03-Ders-Notlari-Gercekci.pdf) · [Kodlar satır satır — PDF](Hafta-03-Kodlar-Satir-Satir.pdf)

Bu uygulama, 2026 Uluslararası İHA Yarışması / Döner Kanat görevlerini gerçek Gazebo fiziği ve ArduPilot SITL üzerinde çalıştırır. Kullanılan yarışma referansı [V7 şartnamesidir](kaynaklar/2026-IHA-Sartnamesi-V7.pdf). HOME konumu ve kontrol ayarları eğitim tercihidir; gerçek yarışma kabulü anlamına gelmez.

## Kurulum ve ders

1. Yeni Windows bilgisayarda depo kökünü `C:\uav-course` olarak hazırlayın ve kökteki **Kur.cmd** dosyasını çalıştırın. [Kurulum ve sorun giderme](../../KURULUM.md).
2. Kökte **Baslat.cmd** dosyasını açın. ROTA GCS'de **Simülasyonu Başlat** seçip GPS/EKF ve kamera verisini bekleyin.
3. **G1, G2 veya G3** seçin. [Canlı ders rehberi](gercekci/CANLI_DERS.md), görev seçimini, dört kamera açısını ve renkli kod bloklarını açıklar.
4. Mission Planner'da **TCP / 127.0.0.1 / 5762** ile aynı uçuşa bağlanın. ROTA GCS, 5760 portunda açık kalır.

| Görev | Uygulama |
| --- | --- |
| G1 | Direkler çevresinde iki ardışık sekiz, HOME'a dönüş, normal iniş. |
| G2 | İki yükü RGB kamerayla bulunan mavi/kırmızı hedeflere teslim etme. |
| G3 | İki ilk teslimatın ardından ilk yükü yeniden görme, kavrama, diğer hedefe taşıma ve bırakma. |

Her bağımsız deneme için yeni simülasyon oturumu açın. G3 ilk iki teslimatı da içerir; öncesinde G2 çalıştırmayın.

[Laboratuvar kodları ve yapısı](gercekci/README.md) · [Kaynaklar ve görsel kökeni](KAYNAKLAR.md)
