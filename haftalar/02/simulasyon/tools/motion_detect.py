"""Eski komutlar için uyumluluk; gerçek algoritma ders_kodlari/ içindedir."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ders_kodlari.hareketli_unsur_tespiti import Detector, run_detector, evaluate_bbox, main

if __name__ == '__main__':
    main()
