# ROTA GCS ile canlı görev ve Python dersi

Bu derste aynı uçuşu üç yerden okuyacağız: sahadaki gerçek Gazebo görüntüsü, aracın ölçülen durumu ve o anda yürütülen Python kaynağı. **Canlı Kod** paneli, çalışan görev iş parçacığının gerçek `sys.settrace` olaylarını gösterir. Görev aşamasına göre hazırlanmış bir satır animasyonu kullanılmaz.

## Derse başlayın

1. [Baslat.cmd](Baslat.cmd) ile yerel servisi açın; arayüzden **Simülasyonu Başlat** seçin. Telemetri, kamera ve GPS/EKF hazır olana kadar bekleyin.
2. **Görev seçimi** kartından G1, G2 veya G3 seçin. Başlatmadan önce kart, seçtiğiniz planın adımlarını gösterir. **G1/G2/G3 Görevini Başlat** düğmesi yalnız seçilen görevi çalıştırır.
3. Görev başladığında kartta **Çalışan görev** ve gerçek aşama görünür. Görev sürerken veya motorlar ARM iken görev seçimi kilitlidir; bekletme başka bir göreve geçiş yapmaz.
4. Sol menüden veya görev kartındaki bağlantıdan **Canlı Kod** panelini açın. **Görev** hattında varsayılan **Blok görünümü** ile başlayın; **Canlı Bloğu İzle** düğmesi çalışan görev bölümünü takip eder.

| Seçim | Öğrencinin izleyeceği akış |
| --- | --- |
| **G1 · Sekiz uçuşu** | Yüksüz kalkış, Direk 2 dışından giriş, direkler çevresinde iki ardışık sekiz, dış çıkış, HOME dönüşü ve iniş. |
| **G2 · Hedef ve yük** | İki yükle kalkış, araç kamerasından hedef arama, kırmızı yükü mavi altıgene ve mavi yükü kırmızı üçgene bırakma, dönüş ve iniş. |
| **G3 · Geri al ve taşı** | G2’deki iki ilk teslimatı da yapar; ardından ilk bırakılan yükü RGB’de yeniden bulur, fiziksel olarak kavrar, diğer hedefe taşır ve bırakır. |

**G3, G2’nin ilk teslimatlarını kendi içinde içerir.** G3 denemesi için önce aynı oturumda G2 çalıştırmanız gerekmez. Her bağımsız yarışma denemesini yeni simülasyon oturumuyla başlatın; iki yük başlangıç düzeninde yeniden hazırlanır.

## Uçuşu dışarıdan ve araçtan izleyin

**Canlı görüntüler** bölümündeki **Birlikte**, **Araç** ve **3. kişi** seçenekleri ekran yerleşimini değiştirir. Araç kamerası hedef algılamasında kullanılan aşağı bakan gerçek RGB sensörüdür. Üçüncü şahıs görüntüsü ayrı bir Gazebo sensöründen gelir; görev algılamasının girdisi değildir.

| Üçüncü şahıs modu | Derste kullanım |
| --- | --- |
| **Takip** | Aracın arkasından hareketi ve saha içindeki ilerleyişi izleyin. |
| **Yörünge** | Araç çevresinde dönen bakışla gövdeyi, askıları ve yükleri inceleyin. |
| **Yandan** | İvmelenirken yük salınımını, yaklaşma yüksekliğini ve bırakılan yükün düşüşünü gözleyin. |
| **Üstten** | Araçla birlikte hareket eden üst bakışla yönü ve rota şeklini takip edin. Sabit saha haritası ayrı görüntüdür. |

Bir modu seçtiğinizde istek gönderilir. Seçili modun doğrulanması, Gazebo’dan gelen gerçek kare ve native kamera geri bildirimiyle yapılır; geçiş sırasında “geri bildirim bekleniyor” yazısını görebilirsiniz. Bu düğmeler kamerayı hareket ettirir; uçuş hedefini veya tutucuları değiştirmez.

Üçüncü şahıs sensörü **640×360 ve simülasyon zamanında 8 Hz** olarak ayarlıdır. Bu bilgisayarda gözlenen akış yaklaşık **3,6 kare/saniye duvar zamanı** düzeyindedir; render yükü ve bilgisayar donanımı bunu değiştirir. Araç RGB sensörünün ayarı ise **960×720, 8 Hz**’dir. Güncel kare gelmediğinde arayüz görüntünün eskidiğini belirtir.

## Canlı Kod panelini okuyun

**Görev** hattı `control.py` içindeki gerçek görev iş parçacığını; **Görüntü işleme** hattı kamera iş parçacığında açıkça sarılmış `Camera.update()` ve onun çağırdığı `vision.py` fonksiyonlarını izler. Kamera hattı, görev hattının konumunu değiştirmez. İzleme diğer Python iş parçacıklarına topluca açılmaz.

### Renkli bloklarla başlayın

**Blok görünümü** kodu iki veya üç kelimelik başlıklarla ayırır. Üst kartta izlenen blok ve kısa açıklaması; kodun içinde aynı renkte bölüm başlığı, kenar şeridi ve satır aralığı görünür. İsimler de yazıldığından takip yalnız renge bağlı değildir.

| Renk | Örnek bloklar | İzlenen iş |
| --- | --- | --- |
| Sarı | **Uçuş Hazırlığı** | Ön kontroller, yüklerin hazırlanması ve kalkış. |
| Mavi | **Alan Geçişi**, **Sekiz Uçuşu**, **HOME Dönüşü** | Uçuş ve konum hedefleri. |
| Mor | **Hedef Arama**, **Görsel Kilit** | Gerçek görüntüden tespit ve konum çıkarma. |
| Turuncu | **Yük Bırakma**, **Boşluk Seçimi** | Hedefte yer seçimi ve teslimat. |
| Turkuaz | **Yük Kavrama**, **Hedefe Taşıma** | Yüke hizalanma, gerçek bağlanma ve taşıma. |
| Pembe | **İniş Kontrolü** | Normal LAND ve DISARM doğrulaması. |
| Gri | **Koşul Bekleme**, **Görev Kaydı** | Yardımcı kontroller ve sonuç kaydı. |

Ana görev içindeki `goto`, `vehicle` veya `wait` gibi alt çağrılar arasında ekran sürekli atlamaz. Görev hattında gerçek çağrı yığınındaki `run_mission` çağrı noktasında kalır; görüntü işleme hattında `Camera.update` bölümü izlenir. Kodda işaretlenen **Üst çağrı**, alttaki fonksiyonu çağıran satırdır. Gerçekte yürütülen alt fonksiyon ve satır ayrıca gösterilir; bu iki konum aynı şey değildir.

**Bloklara git** şeridindeki bir ada tıklayarak o bölümü açın. Şerit kod bölümlerinin listesidir; her bloğun her uçuşta çalışacağını veya tamamlandığını göstermez. Bu işlem otomatik kaydırmayı bırakır, uçuşu değiştirmez. **Canlı Bloğu İzle** ile güncel bölüme dönün. Ayrıntılı işlem için **Satır ayrıntısı** seçin; bu modda **Canlı Satırı İzle**, gerçekten yürütülen alt satırı takip eder. **Ekranı Dondur**, iki görünümde de yalnız ekrandaki kaydı sabitler.

Blokların satır aralıkları, ekranda gösterilen SHA ile eşleşen önbellek kaynak metninden çıkarılır. Görev aşamasından hareketle yapay bir çalışan satır üretilmez. Bağlantı koptuğunda veya kaynak sürümü uyuşmadığında canlı blok vurgusu yapılmaz; geçmiş olayda çağrı yığını yoksa üst çağrı uydurulmaz. **Yalnız kaynak** dosyalarındaki renkler ise gezinme içindir.

| Olay | Anlamı |
| --- | --- |
| **Satır · `line`** | Python bu satırı çalıştırmak üzeredir. Olay, satır çalıştırılmadan hemen önce oluşur. |
| **Çağrı · `call`** | İzin verilen kaynak dosyalarındaki bir Python fonksiyonuna girilmiştir. |
| **Dönüş · `return`** | Fonksiyondan dönüş olayı alınmıştır. Dönüş değeri aktarılmaz. |
| **İstisna · `exception`** | Gerçek Python istisnası oluşmuştur. Panel istisnanın türünü gösterir; hata mesajı ve yerel değişkenler aktarılmaz. İstisna sonraki kod tarafından yakalanabilir. |

Bir komut satırının vurgulanması, aracın o işi tamamladığı anlamına gelmez. Örneğin `self.goto(...)` satırını gördükten sonra konuma varışı, `goto()` içindeki ölçülen konum/hız koşulları belirler. OpenCV ve NumPy gibi kütüphanelerin C/C++ içindeki satırları bu panelde izlenmez. Python dışındaki işlem veya uyku sürerken en son gerçek Python konumu ve kayıt yaşı gösterilir.

**Çağrı yığını** üst düzey kararı ve alttaki işlemi birlikte okumayı sağlar:

```text
Controller.run_mission   → görevde hangi adım çağrıldı?
  Controller.goto        → hangi konum/hedef koşulu denetleniyor?
    Controller.vehicle   → ölçülen telemetri nasıl okunuyor?
```

Başka bir anda `run_mission → takeoff → wait` veya `run_mission → release → servo → command` zincirini görebilirsiniz. Yığındaki bir satıra tıklayarak çağrı noktasına gidin; ardından görünümünüze göre **Canlı Bloğu İzle** veya **Canlı Satırı İzle** ile anlık konuma dönün. Tarihî bir olaya tıklamak onun gerçek dosya ve satırını açar; her tarihî olay için ayrı yığın kaydedilmez.

**A− / A+** düğmeleri kod yazısını **12–22 px** aralığında değiştirir; başlangıç **14 px**’dir. Sınıf projeksiyonunda 18–22 px kullanıp işlev listesinden ilgili fonksiyona geçebilirsiniz.

### “Şimdi ne oluyor?” ve bekleme koşulları

Bekleme kartı gerçekten çalışan `goto`, `wait` veya MAVLink komut beklemesini açıklar. Alanlar ilgili işlemde veri olduğunda görünür:

| Alan | Nasıl yorumlanır? |
| --- | --- |
| **Hedef E/N/U** | Dünya ENU çerçevesindeki doğu, kuzey ve yükseklik hedefi; metre. U değeri dünya yüksekliğidir. |
| **Hedefe yatay** | Ölçülen araç konumunun hedefe yatay uzaklığı; üç boyutlu toplam mesafe değildir. |
| **İrtifa hatası** | Hedef U eksi ölçülen U. Pozitif değer hedefin araçtan yukarıda olduğunu belirtir. |
| **Hız** | Ölçülen hız vektörünün büyüklüğü; konuma yaklaşmanın yanında durulma koşulunu anlamaya yardım eder. |
| **Bekleme süresi / sınır** | Bu işlemin duvar zamanındaki bekleme süresi ve yazılımdaki zaman aşımı. |
| **ArduPilot COMMAND_ACK** | Gönderilen MAVLink komutunun yanıtı beklenir. ACK almak, fiziksel yükün kavrandığını veya yere düştüğünü tek başına kanıtlamaz. |

Ekrandaki veri, izin verilen sınırlı bağlam alanlarından gelir. Çerçeve yerel değişkenleri, keyfî nesne içerikleri ve dönüş değerleri toplanmaz.

### Ekranı dondurmak ve görevi bekletmek

**Ekranı Dondur**, yalnız kod panelinin gösterdiği iz ve geçmiş görünümünü sabitler. Python yürütmesi, uçuş, kamera ve arka plandaki iz alımı devam eder. Öğrenciyle bir bölümü tartışmak için kullanın; sonra **Ekranı Sürdür** ve canlı takip düğmesiyle devam edin.

Görev kartındaki **Beklet / Devam Et** ayrı bir uçuş kontrolüdür: görevi BRAKE ile bekletir, GUIDED ile sürdürür. **İniş** gerçek LAND komutudur. Kod ekranını açmak, yazı boyutunu değiştirmek veya geçmişe bakmak bu komutları göndermez.

### Geçmiş ve kaynak sürümü

Backend belleğinde en fazla **4096 gerçek olay** tutulur. Kod paneli yaklaşık **250 ms** aralıkla güncellenir ve sınırlı bir son olay listesini gösterir. Hızlı döngülerin her milisaniyesini ekranda tek tek okuyamazsınız; **Örneklenmiş iz** işareti yanıt sınırı veya tampon dışına çıkan olaylar olduğunu açıklar. Görülen her olay gerçek yürütmeden gelir; atlanan olayların yerine satır üretilmez.

Kaynak metni ve **SHA256**, izleyici oluşturulurken belleğe alınır. `source_changed` uyarısı, diskteki dosyanın bu kaynak sürümünden farklı olduğunu söyler; o uçuşta gösterilen satırlar önbellekteki sürümde kalır. Öğretim sırasında kaynak düzenlediyseniz önce uçuşu tamamlayıp iniş/disarm yapın, ardından **Python backend başlatıcısını kapatıp yeniden açın**. Tarayıcıyı yenilemek veya yalnız Gazebo oturumunu yeniden oluşturmak, Python’ın daha önce içe aktardığı modülleri yeniden yüklemez.

## Kaynak dosyaları arasında gezinme

Canlı Kod kataloğunda dört uygulama dosyası bulunur. **Yalnız kaynak** etiketi olan dosyada canlı satır yürütme iddiası yoktur.

| Dosya | Derste bakılacak bölüm | Canlı iz |
| --- | --- | --- |
| [backend/control.py](backend/control.py) | `run_mission`, `goto`, `pickup`, `gripper_pair`, `visual_pickup_lock`, `release`, `servo`; görev ve telemetri koşulları. | Görev iş parçacığı |
| [backend/vision.py](backend/vision.py) | `Camera.update`, `read_frame`, `detect`, `project`, `rotation`; görüntüden konuma gidiş. | Görüntü işleme iş parçacığı |
| [backend/server.py](backend/server.py) | Yerel HTTP uçları, durum sunumu ve arayüz komutlarının yönlendirilmesi. | Yalnız kaynak |
| [backend/native_runtime.py](backend/native_runtime.py) | Gazebo/SITL süreçlerini başlatma ve çalışma dizini/provenans kayıtları. | Yalnız kaynak |

İzleyicinin kendi uygulanışı [backend/execution_trace.py](backend/execution_trace.py), üçüncü şahıs kamera okuma ve mod geri bildirimi [backend/follow_camera.py](backend/follow_camera.py) içindedir. Bu iki yardımcı dosya dört dosyalı canlı kaynak kataloğunun parçası değildir. Fiziksel kavrama/bırakma için [plugin/PayloadMechanics.cc](plugin/PayloadMechanics.cc) kaynağını ayrıca inceleyin.

## Örnek sınıf akışı

### G1: döngü, çağrı ve ölçülen varış

1. Yeni simülasyonda **G1** seçin. Araç ve üçüncü şahıs görüntülerini birlikte açın; haritadaki planlanan rota ile gerçek uçuş izini karşılaştırın.
2. Canlı Kod’da **Görev → control.py → Controller.run_mission** bölümünü açın. `for index, theta ...` döngüsünü ve her noktada `self.goto(...)` çağrısını bulun.
3. Çağrı yığınında üstteki `run_mission` satırı ile alttaki `goto` satırının farklı soruları yanıtladığını gösterin: “Hangi rota noktası istendi?” ve “Araç bu noktaya hangi koşulla varmış sayılacak?”
4. Hedef uzaklığı, irtifa hatası ve hızın değişimini gözleyin. G1 eğrisindeki **8 m**, ardışık GUIDED hedefleri arasında geçiş için uygulamanın kullandığı kabul uzaklığıdır; ArduPilot `WP_RADIUS` parametresi değildir.
5. Bir geçişi **Ekranı Dondur** ile inceleyin. Uçuşun diğer panellerde devam ettiğini gözleyip ekranı sürdürün. Gerçek uçuşu bekletmek isterseniz görev kartındaki ayrı **Beklet** düğmesini kullanın.

### G3: görüntü, yeniden kavrama ve fiziksel kanıt

1. Yeni simülasyonda **G3** seçin. Önce iki ilk teslimatı izleyin; ayrıca G2 başlatmayın.
2. **Görüntü işleme → vision.py** hattında `read_frame → detect → project` zincirini inceleyin. İlk yükün yeniden bulunmasında aşağı bakan gerçek RGB, güncel kamera pozu ve piksel izdüşümü kullanılır.
3. **Görev** hattına dönün. `run_mission` içinde güncel yük görüntüsünü bekleyen koşulu, alçalan yaklaşmayı ve `self.servo(..., 1900)` çağrısını takip edin.
4. `servo → command` sırasında ACK beklemesini okuyun. Sonra görev kodunun ayrıca gerçek `attached` geri bildirimini beklediğini gösterin: komutun kabulü ile yükün fiziksel bağlanması ayrı kanıtlardır.
5. Kavrayıcı noktası ile yük uygun yakınlık ve bağıl hızda olduğunda fizik eklentisi bağlantıyı kurar. **Yandan** bakışta yükün sarkaç hareketini ve GCS’deki salınım değerini birlikte gözleyin. Bu modelin kapıları **0,16 m yakınlık**, **0,60 m/s bağıl hız** ve kapalı çenedir; kapama isteği tek başına bağlantı oluşturmaz.
6. Son bırakmada `1100 µs` komutunu, bağlantının ayrılmasını ve yükün gerçekten aşağı düşüp hedefte durmasını ayrı ayrı kontrol edin. Yalnız `attached=false` etiketi fiziksel düşüşün yerine geçmez.

### G3: dolu hedefte boş yer seçimi

Diğer hedefe dönüldüğünde orada ikinci yük hâlâ durur. Aynı merkez noktasına bırakmak iki yükü çarpıştırabilir. G3 bu nedenle küçük üçgendeki ilk teslimatta kenardan içeride bir bölge seçer; son aktarımda da güncel RGB görüntüsünden hedef çokgenini ve yerdeki diğer yükü yeniden ölçer. Çokgen içinde, kenarlardan ve mevcut yükten uzak bir bırakma noktası aranır. Sahnenin hazır yük koordinatları bu karara verilmez.

Canlı Kod'da çokgen seçimini, güncel görüntüyü bekleyen koşulu ve `release()` yaklaşmasını birlikte inceleyin. Geometrik olarak uygun nokta bulunamaması bir hata koşuludur; kod, kapalı bir hedefe körlemesine bırakmak yerine görevi durdurur. Son yaklaşmada tutucu konumu ile gövde arasındaki ölçülen fark düzeltilir; salınım ve yatay yük hızı azaldıktan sonra servo açılır. Bu adımlar, görüntüden bir hedef bulmanın tek başına güvenilir teslimat anlamına gelmediğini gösterir.

### G3: aynı andaki ölçümleri karşılaştırma

`gripper_pair()` gövdeyi ve tutucuyu aynı fizik mesajından okur. Hareket sırasında ayrı zamanlarda gelen MAVLink gövde konumu ile Gazebo tutucu konumunu birbirinden çıkarmak, gerçek askı ofsetinden farklı bir sonuç verebilir. Yaklaşma bu nedenle hem ölçümlerin güncelliğini hem yüksekliği, gövde konumlarının uyumunu, hızı ve salınımı bekler; son alımda yeniden hizalar.

1,2 m gövde yüksekliğinde üç farklı, güncel ve tutarlı RGB karesinden yerdeki yükün konumu kilitlenir. Son alçalmada yük kamera görüşünün kenarında kalabileceğinden, yerdeki yükün kısa süre sabit kaldığı varsayımıyla bu görsel kilit en fazla **15 saniye** kullanılır. Kilit süresi veya hizalama koşulu sağlanmazsa servo kapatılmaz. Bu, alçak görüntüde olmayan bir tespiti varmış gibi göstermeden gerçek kavrama koşuluna yaklaşmayı sağlar.

## Zamanları birbirine karıştırmayın

GCS görev sayacı, kod izindeki süreler ve bekleme zaman aşımı **PC’nin duvar zamanını** kullanır. Yarışma süre değerlendirmesi ise kaydedilen gerçek fizik **simülasyon saatine** göre yapılır: G1 için 300 s, G2/G3 için 600 s sınırı ayrı denetlenir. Render nedeniyle simülasyon gerçek zamandan yavaş çalıştığında duvar zamanında daha uzun izlediğiniz bir uçuşun fizik süresi daha kısa olabilir.

G1 eğitim değerlendirmesinde süre, kalkışı da içeren başlangıçtan HOME'un 2 m güneyindeki tanımlı eğitim bitiş çizgisinin son dönüş geçişine kadar ölçülür; iniş ve disarm ayrıca aranır. Bu eğitim çizgisi resmî sahada ölçülmüş kronometre çizgisi değildir. Kendi uçuşunuzu `.local/runs` altındaki telemetri, görev olayları ve mekanik kayıtlarıyla değerlendirin. Ekrandaki tamamlanma mesajı tek başına yarışma kabul raporu değildir.

## Mission Planner ile birlikte izleyin

ROTA simülasyonu başlattıktan sonra Mission Planner'da **TCP → 127.0.0.1 → 5762** seçin. ROTA'nın 5760 bağlantısı açık kalır. Telemetri ve servo değerlerini Mission Planner'da; görev aşamasını, gerçek kameraları ve canlı Python bloklarını ROTA'da karşılaştırın. Görevler Python'dan GUIDED komutlarıyla yürütülür; Mission Planner'ın AUTO görev listesi bu adımları göstermez. [Kurulum ve bağlantı denetimi](../../../KURULUM.md).
