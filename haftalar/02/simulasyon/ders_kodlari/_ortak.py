"""Kurulum/kalibrasyon yardımcıları tools/ içinde; ders algoritmaları burada."""
from pathlib import Path
import sys

SIMULASYON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULASYON / 'tools'))

# Windows'ta NumPy/OpenCV yüklenmeden önce gerekli DLL yolu açılır.
import vision_bootstrap  # noqa: E402,F401
