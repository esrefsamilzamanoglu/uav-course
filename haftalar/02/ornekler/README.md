# Bina — Gaussian Splatting örneği

`Bina-Gaussian.ply`, dersin gerçek AUTO bina uçuşunda çekilmiş RGB görüntülerinden **Brush0.3.0** ile optimize edilen modeldir. Source bina mesh'i kopyalanmamıştır. `simulasyon/3D_Goster.cmd` dosyası modeli resmî Brush viewer'da açar.

- Girdi:108 gerçek Gazebo fotoğrafı, bilinen camera poses ve intrinsics.
- Train94 / hold-out14. Hold-out fotoğraflar sparse initialization'da da kullanılmadı.
- Sparse seed:1298 image-derived nokta; ana çıktı seed değildir.
- Training:6 000steps, max45 000Gaussians, SH degree2,640×427 RGB.
- Ölçümler: [gaussian_validation.json](../dogrulama/gaussian_validation.json).

Bu dosya XYZRGB point cloud değil; opacity, scale, rotation ve spherical harmonics içeren Gaussian PLY'dir. Gaussian viewer kullanın. Watertight mesh veya CAD modeli değildir. Uzak zeminde blur ve airframe kaynaklı floaters kalabilir; novel-view render ve serbest orbit ile inceleyin.
