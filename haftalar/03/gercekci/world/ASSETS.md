# Gerçekçi dünya ve model kaynakları

`build_world.py` dünya ile tüm yeni STL/OBJ şekillerini tekrar üretir. Koordinat sistemi ENU'dur: X doğu, Y kuzey, Z yukarı. `scene.json` Gazebo ve GCS haritasının ortak yerleşim kaynağıdır.

HOME, sahanın ortasından 24 m batıya alınmıştır; her iki direğe eşit uzaklıktadır. Şartname nihai HOME koordinatı vermediğinden bu konum eğitim tercihidir. Direkler kuzey ±75 m'dedir; planlanan 150 m açıklık korunur. Mavi altıgenin kenarı 2 m, kırmızı eşkenar üçgenin kenarı 1 m'dir.

Yeni beyaz kompozit gövde, karbon kollar, turuncu motor halkaları, gimbal kamera ve hareketli çene; ders kapağındaki quadcopter görselini kaynak alır. Uçuşun motor ve IMU yapısı, çalışan ArduPilot Gazebo Iris modelinden alınır. Motor bağlantıları, itki/drag ayarları ve IMU dönüşümleri korunmuştur. Drone gövdesine iki gerçek iki eksenli sarkaç, 0,55 m askı, hareketli çene ve fiziksel 0,30 kg yük eklenir.

25 Kasım modelinde dört sabit karbon iniş strutu native gövde ankrajlarından dışa açılır; yuvarlak ayakların X/Y konumları ±0,48 m, tabanı gövdeden 0,845 m aşağıdadır. Yatay travers bulunmaz. Dar kalkış rafının sekiz modeli kaldırılmıştır; araç düz HOME pedinde kendi ayaklarıyla oturur. Yeni ayaklar mevcut gövdenin toplu kütle temsilinin parçasıdır; ayrı dinamik link/kütle eklenmez, native gövde ataleti ve motorlar korunur. İki yük dâhil rijit link kütlesi yine 2,486 kg'dır.

Gerçek doğal temas deneyinde yüklü gövde Z=0,8724995 m'de dik oturmuş, küpler ile ped arasında en az 4,926 mm boşluk kalmıştır. Yüksüz model çıplak zemine doğal bırakıldığında Z=0,8449994 m'de dik oturmuştur. Sabit .89 m alım deneyinde ayak–mat boşluğu 23 mm iken gerçek çene/kavrama kapısı yükü bağlamıştır. Bu temas/alım testlerinin 26 kontrolü ve güncel tam-model bırakma regresyonunun 13 kontrolü geçmiştir; bunlar ArduPilot LAND/disarm veya tam görev sonucu değildir. Başlangıç yüksekliği ArduPilot'un sıfır relatif irtifasıyla karıştırılmaz; kalibrasyon gerçek başlangıç pozunu okumalıdır.

Dünyada 246 model ve 209 harita nesnesi bulunur: ağaçlar, dallar, yaprak kümeleri, gerçek boyutlu yollar, kaldırım, otopark çizgileri, camlı/tekerlekli araçlar, iki katlı çatı/gutter/pencere ayrıntılı binalar, çadırlar, masa, ekipman kasaları, banklar, çöp kutuları, koniler, işaret levhaları, metal çitler ve uzaktaki tepeler. Model/harita sayısındaki azalma dar rafın kaldırılmasındandır; çevre dekoru korunur. Gerekli çevre çarpışmaları statiktir.

Çim albedo dokusu built-in `image_gen` ile üretilmiş fotoğraf benzeri bir malzeme haritasıdır. Tam istem `grass_prompt.json` içindedir. Doku `../models/competition_assets/textures/grass_albedo.png` dosyasındadır. Bu bir malzeme dokusudur; uçuş veya gerçek dünya fotoğraf kaydı değildir. Yeni geometri dosyaları kod tarafından üretilir; dışarıdan indirilmiş dekoratif 3D varlık yoktur.

Üstten bakan sabit gözlem kamerası 1400×1400, 1 Hz'dir; dünya ±190 m kapsamıyla GCS harita arka planını gerçek Gazebo render'ından sağlar. Bu kamera görev algılamasına verilmez. Görev kamerası drone üzerinde tek 960×720, yatay 90°, 8 Hz RGB sensörüdür.

Ek `follow_observer` modelinde bağımsız 640×360, yatay 70°, 8 Hz üçüncü şahıs sensörü vardır. Takip/yörünge/yan/üst modlarında yalnız bu gözlem modelinin pozu değiştirilir. Onboard algı, sabit harita ve hava aracı pozları bu kameranın komutlarından etkilenmez.

ArduPilot Iris dinamiğinin kaynağı: [ArduPilot/ardupilot_gazebo](https://github.com/ArduPilot/ardupilot_gazebo). Üst kaynağın LGPL-3.0 lisansı kurulumdan sonra `windows/.local/ardupilot_gazebo/LICENSE.md` içindedir. Modelin üst kaynak bölümleri ve yeni görsel/geometri ekleri, `build_world.py` dosyasında açıkça ayrılır. İlgili lisans [UPSTREAM-LICENSE.txt](../models/competition_quad/UPSTREAM-LICENSE.txt) içinde korunur.
