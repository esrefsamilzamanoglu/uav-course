# Windows: Gazebo + ArduPilot

Önce [ana rehberdeki](../README.md) Pixi ve **Visual C++ Build Tools 2022** kurulumunu tamamlayın. Build Tools içinde **MSVC v143 x64/x86** ile **Windows 11 SDK 10.0.26100** seçili olmalı. Repo `C:\uav-course` gibi boşluksuz, Türkçe karakter içermeyen bir klasörde bulunmalı.

1. **Kur.cmd** dosyasına çift tıklayın. İndirme ve derleme tamamlanana kadar bekleyin. Bu adım bir kez yapılır; yarıda kalırsa yeniden açabilirsiniz.
2. **Baslat.cmd** dosyasına çift tıklayın; Gazebo açılır. Bu terminal penceresi açık kalsın.
3. Mission Planner'da **TCP → CONNECT → 127.0.0.1 → 5760** seçin. Parametreler yüklendiğinde simülasyona bağlandınız.

Bitirince Gazebo'yu kapatın veya terminalde `Ctrl+C` kullanın. Mission Planner bağlantısını kesmek de SITL oturumunu sonlandırabilir; tekrar bağlanmak için **Baslat.cmd** dosyasını açın.

Kurulum, Gazebo Jetty **10.5.0**, ArduCopter **4.7.2** ve bu bilgisayarda çalıştırılmış Windows eklenti uyarlamasını kullanır. Programlar resmî kaynaklardan indirilir; eklenti kendi bilgisayarınızda derlenir. Kurulum çıktıları `.local` ve `.pixi` klasörlerinde kalır. Kurucu ve başlatıcı uçuş komutu göndermez.

`ardupilot_gazebo` için resmî bir Windows kurucusu bulunmadığından [belirli kaynak sürümüne](https://github.com/ArduPilot/ardupilot_gazebo/tree/082a0fe231f6e63bc8d1598f1cba461d9e2ea7f5) küçük bir Windows yaması uygulanır. Ayrıntı ve lisanslar: [SOURCES.txt](SOURCES.txt), [COPYING.LESSER](COPYING.LESSER), [COPYING](COPYING). Resmî SITL dosyalarının sürümü değişip doğrulama durursa manifestin ders sorumlusu tarafından güncellenmesi gerekir.

21 Ekim 2026'da bu yardımcılarla ayrı bir klasörde yeni Gazebo ortamı oluşturuldu; eklenti derlendi ve kurulumun yeniden çalıştırılması denendi. Gazebo'da Iris görüntüsü, JSON bağlantısı ve TCP üzerinden disarmed durumunda heartbeat, tutum ve konum telemetrisi doğrulandı. Bu kontrolde uçuş komutu gönderilmedi; temiz bilgisayar testi yapılmadı.
