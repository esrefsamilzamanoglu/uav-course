# 2. hafta — kaynaklar

28 Ekim 2026 revizyonu. Teknik davranışlar için resmî kaynaklar; sayısal sonuçlar için gerçek Gazebo/SITL kayıtlarımız kullanıldı.

- [Copter AUTO](https://ardupilot.org/copter/docs/auto-mode.html)
- [ArduPilot + Gazebo](https://ardupilot.org/dev/docs/sitl-with-gazebo.html)
- [Gazebo native Windows](https://gazebosim.org/docs/jetty/install_windows/)
- [MAVLink mission commands](https://ardupilot.org/copter/docs/common-mavlink-mission-command-messages-mav_cmd.html)
- [Mission Planner Survey(Grid) ve camera trigger](https://ardupilot.org/planner/docs/common-camera-control-and-auto-missions-in-mission-planner.html)
- [Mission Planner görev planlama](https://docs.ardupilot.org/planner/docs/mission-planner-flight-plan.html)
- [Servo gimbal](https://ardupilot.org/copter/docs/common-camera-gimbal.html)
- [Mount ROI targeting](https://ardupilot.org/copter/docs/common-mount-targeting.html)
- [Sprayer](https://ardupilot.org/copter/docs/common-sprayer.html)
- [Plane automatic takeoff](https://ardupilot.org/plane/docs/automatic-takeoff.html)
- [Plane automatic landing](https://ardupilot.org/plane/docs/automatic-landing.html)
- [DO_LAND_START](https://ardupilot.org/plane/docs/common-do-land-start.html)
- [OpenCV ORB](https://docs.opencv.org/4.x/d1/d89/tutorial_py_orb.html)
- [OpenCV feature matching ve homography](https://docs.opencv.org/4.x/d1/de0/tutorial_py_feature_homography.html)
- [OpenCV camera geometry / triangulation](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)
- [COLMAP: SfM ve dense reconstruction](https://colmap.github.io/tutorial.html)
- [Ders deposu](https://github.com/esrefsamilzamanoglu/uav-course/tree/main/haftalar/02)
- [Kerbl ve diğerleri: 3D Gaussian Splatting (SIGGRAPH2023)](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/)
- [Brush0.3.0: training ve native viewer](https://github.com/ArthurBrussee/brush/tree/v0.3.0)

## Gerçek deney ve görsel kökenleri

[Uçuş doğrulama özeti](dogrulama/final_summary.json) · [Gaussian hold-out metrikleri](dogrulama/gaussian_validation.json) · [Temel simülasyon görselleri](sunum/gorseller/provenance.json) · [Gaussian render kökenleri](sunum/gorseller/gaussian-provenance.json) · [Çalışma şemaları](sunum/gorseller/explainers-provenance.json).

Şemalar kodla çizildi; PNG görsellerin düzenlenebilir SVG kaynakları `sunum/semalar` içindedir. Gerçek sensör kaydı, gerçek model render’ı ve kavramsal şema birbirinden ayrılır. PSNR/SSIM görünüş ölçüsüdür; geometric accuracy iddiası değildir.

ArduPilot Gazebo kaynak sürümü `082a0fe231f6e63bc8d1598f1cba461d9e2ea7f5`; SITL4.7.2 kaynak sürümü `fbd0a3160c90a557c24ce4c38c16975532652536`. Resmî Brush0.3.0 release URL ve hash değeri `simulasyon/gaussian-downloads.json` içinde. [Model / araç kökenleri](simulasyon/UPSTREAM.md).
