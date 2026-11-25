# 3. hafta kaynakları

Yarışma referansı: [TEKNOFEST Uluslararası İHA Yarışması](https://www.teknofest.org/tr/yarismalar/uluslararasi-insansiz-hava-araci-yarismasi/), [2026 V7 şartnamesinin resmî PDF'i](https://cdn.teknofest.org/media/upload/userFormUpload/2026_%C4%B0HA_Yar%C4%B1%C5%9Fmalar%C4%B1_%C5%9Eartnamesi_TR_VBU_aWNZu.pdf). Ders 24 Kasım 2026'da incelenen V7 sürümünü kullanır. [Yerel kopya](kaynaklar/2026-IHA-Sartnamesi-V7.pdf), SHA-256: `8fae1724091aa55bb0b2a71f490e0269c989643195e72f0427ebaa66ad479eb7`. [Sayfa referanslı kural özeti](kaynaklar/official_rules.json).

| Kavram | Birincil başvuru |
| --- | --- |
| GUIDED konum hedefleri | [ArduPilot](https://ardupilot.org/dev/docs/copter-commands-in-guided-mode.html) |
| Servo komutları | [MAV_CMD_DO_SET_SERVO](https://ardupilot.org/dev/docs/mavlink-move-servo.html) |
| İki MAVLink kanalı | [ArduPilot 4.7.2 UARTDriver.cpp](https://github.com/ArduPilot/ardupilot/blob/Copter-4.7.2/libraries/AP_HAL_SITL/UARTDriver.cpp) |
| GCS kimliği / failsafe | [ArduPilot 4.7.2 GCS.cpp](https://github.com/ArduPilot/ardupilot/blob/Copter-4.7.2/libraries/GCS_MAVLink/GCS.cpp) |
| MAVLink mesajları | [common.xml başvurusu](https://mavlink.io/en/messages/common.html) |
| HSV ve konturlar | [OpenCV eşikleme](https://docs.opencv.org/4.x/da/d97/tutorial_threshold_inRange.html), [kontur özellikleri](https://docs.opencv.org/4.x/dd/d49/tutorial_py_contour_features.html) |
| Kamera modeli | [OpenCV kalibrasyon](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html) |
| Fiziksel kavrama | [Gazebo Sim 10 Detachable Joints](https://gazebosim.org/api/sim/10/detachablejoints.html) |
| Satır izlemesi | [Python 3.12 sys.settrace](https://docs.python.org/3.12/library/sys.html#sys.settrace) |

Sunumdaki resmî Şekil 6/7 ve şartname kesitlerinin telifi yayımlayıcıya aittir. Kapak, kamera/kavrama kavram görselleri ve çim dokusu image_gen ile oluşturulmuş eğitim illüstrasyonlarıdır. Görev çalışmasının kaydı olarak değerlendirilmez. Diğer açıklayıcı şemalar kod ile çizilmiştir. Gazebo görüntüleri ilgili slaytlarda simülasyon olarak belirtilir.

[Saha geometrisi, doku ve model kökeni](gercekci/world/ASSETS.md). ArduPilot Iris dinamiğinden türetilen parçaların lisansı [UPSTREAM-LICENSE.txt](gercekci/models/competition_quad/UPSTREAM-LICENSE.txt) içindedir. Arayüzün font ve kütüphane lisansları `gercekci/gcs/frontend/public/licenses` altında ve hazır arayüzde korunur.
