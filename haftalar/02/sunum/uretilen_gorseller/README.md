# Açıklayıcı görseller — 2. hafta v3

Sunumda yalnız metin, tablo, işlem adımları, formül veya sayısal kart içeren **40 sayfanın tamamı** için ayrı, konuya özel çizimler üretildi. Kullanılan yöntem: **built-in image_gen**. API/CLI fallback kullanılmadı.

`slide-XX.png` özgün görseldir. Aynı çözünürlükteki `slide-XX.jpg` kopyası sunuma gömülür; JPEG kodlama yalnız dosya boyutunu azaltır. Tablolar, komutlar ve açıklamalar PowerPoint'te düzenlenebilir metin olarak kalır. Sunum 93 sayfadır.

- [Üretim promptlarının tamamı ve sayfa eşlemesi](prompts.json)
- [Görsel kontrol ve düzeltme promptları](generation-record.json)
- [Dosya SHA256 değerleri ve kökenleri](provenance.json)
- [PDF/PowerPoint görsel kapsam kontrolü](../../dogrulama/illustration_check.json)

Çizimler **kavramsal öğretim görselleridir**. Rota geometrisi ve araçlar şematiktir; sayısal test sonucu, gerçek simülasyon ekranı veya elde edilen gerçek reconstruction olarak değerlendirilmez. Her ilgili sayfada “Kavramsal çizim · AI” etiketi ve konuşmacı notunda açıklaması bulunur. Kesin ölçüler native tabloda; gerçek uçuş grafikleri, kamera kayıtları ve Gaussian render'lar kendi sayfalarındadır.

Gimbal yönelimi, NAV/DO/CONDITION, pompa çıkışı, spray swath, grid/overlap, mesafeli trigger, event–RGB eşleştirme, mosaic, Gaussian training, phase gating, yanlış alarm ve teslim kanıtları görsel olarak açıklanır. Yerleşik İngilizce terimler editable metinde korunur.
