# Kaynak ve model kökenleri

Iris ve Zephyr uçuş modelleri, ArduPilot Gazebo deposunun ilk haftada kullanılan `082a0fe231f6e63bc8d1598f1cba461d9e2ea7f5` sürümünden genişletilerek dünya dosyalarına alınmıştır:

https://github.com/ArduPilot/ardupilot_gazebo/tree/082a0fe231f6e63bc8d1598f1cba461d9e2ea7f5

Upstream paket LGPL-3.0 olarak tanımlıdır. Orijinal bildirimler ve lisans metinleri ilk haftanın [COPYING](../../../windows/COPYING) ve [COPYING.LESSER](../../../windows/COPYING.LESSER) dosyalarında korunur. Dünya üreticisi `tools/build_worlds.py`, model kopyalarını ilk hafta kaynağından genişletir; orijinal kaynak veya uçuş eklentisi değiştirilmez. Zephyr'e bu derste pist kalkışını mümkün kılan ideal teker temasları eklenmiştir.

Tarla, bina, kırsal çevre, bitkiler, insanlar ve dokular dersin `build_worlds.py` üreticisinde yerel geometriden hazırlanır; dışarıdan hazır sahne paketi indirilmez. Kamera ve sahne eklentilerinin C++ kaynakları `src/` içindedir. Derlenmiş DLL/EXE dağıtılmaz.

ArduPlane ve varsayılan Zephyr parametreleri resmî ArduPilot kaynaklarından kurulum sırasında alınır. URL ve doğrulanan SHA256 değerleri `downloads.json` dosyasındadır. ArduPilot uçuş yazılımları bu depoda yeniden dağıtılmaz.

3D Gaussian Splatting için [Brush0.3.0](https://github.com/ArthurBrussee/brush/tree/v0.3.0) resmî release'i kullanılır (Apache-2.0). Araç ve kendi LICENSE dosyası kurulumda yerel `.local` klasörüne alınır; EXE veya dağıtım arşivi ders deposunda yeniden paylaşılmaz. URL/SHA256 `gaussian-downloads.json` içindedir. Paylaşılan Gaussian PLY, gerçek ders RGB verisinin optimizasyon çıktısıdır.
