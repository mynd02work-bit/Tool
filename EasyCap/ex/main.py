"""
Myshot AI - Intelligent Screen Capture & AI Vision Copilot
Entry Point
"""
import sys
import os

# Thêm thư mục mã nguồn src/ vào sys.path
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from src.main import main

if __name__ == "__main__":
    main()
