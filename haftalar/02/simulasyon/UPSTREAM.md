# Kaynak ve lisanslar

Iris ve Zephyr uçuş modelleri [ArduPilot Gazebo 082a0fe](https://github.com/ArduPilot/ardupilot_gazebo/tree/082a0fe231f6e63bc8d1598f1cba461d9e2ea7f5) kaynağından dünya dosyalarına genişletilmiştir. Zephyr'e pist kalkışı için ideal teker temasları eklenmiştir. Upstream LGPL-3.0 bildirimleri [COPYING](../../../windows/COPYING) ve [COPYING.LESSER](../../../windows/COPYING.LESSER) içinde korunur. Orijinal uçuş eklentisi değiştirilmez.

Tarla, ev, kırsal çevre, bitkiler ve hareketli nesneler ders için yerel geometriyle hazırlanmıştır. Evin taş/sıva ve kiremit dokuları OpenAI imagegen ile üretilmiş malzemelerdir; ev fotoğrafı veya model render'ı yerine kullanılmaz. Sunumdaki gerçek ev görüntüleri Gazebo kamerasından, Gaussian render'lar bu RGB verisiyle eğitilmiş modelden gelir. Kamera/sahne eklentilerinin kaynakları `src/` içindedir; DLL/EXE paylaşılmaz.

ArduPlane ve Zephyr parametreleri resmî ArduPilot sunucularından indirilir; URL/SHA256 değerleri `downloads.json` içindedir. Uçuş yazılımı bu depoda yeniden dağıtılmaz.

[Brush 0.3.0](https://github.com/ArthurBrussee/brush/tree/v0.3.0) Apache-2.0 lisanslıdır. Araç ve lisansı kurulumda yerel `.local` klasörüne alınır; indirme bilgileri `gaussian-downloads.json` içindedir. Örnek Gaussian PLY dersin gerçek RGB verisinin optimizasyon çıktısıdır.
