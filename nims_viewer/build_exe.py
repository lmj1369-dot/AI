"""단일 실행파일(EXE) 생성 스크립트"""

import subprocess
import sys
from pathlib import Path


def ensure_icon(nims_root: Path, python_executable: str) -> Path:
    icon_dir = nims_root / "assets"
    icon_dir.mkdir(exist_ok=True)
    icon_path = icon_dir / "NimsViewer.ico"
    if icon_path.exists():
        return icon_path

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        subprocess.run([python_executable, "-m", "pip", "install", "pillow"], check=True)
        from PIL import Image, ImageDraw

    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((18, 18, 238, 238), radius=36, fill=(0, 56, 118, 255))
    draw.rounded_rectangle((42, 42, 214, 214), radius=30, fill=(0, 124, 196, 255))
    draw.rounded_rectangle((88, 88, 168, 168), radius=20, fill=(153, 202, 60, 255))
    for x in range(80, 176, 16):
        draw.line((x, 76, x, 180), fill=(255, 255, 255, 255), width=8)
    image.save(icon_path, format="ICO")
    return icon_path


def build_exe() -> None:
    venv_python = sys.executable
    print("1. PyInstaller 설치 확인 중...")
    subprocess.run([venv_python, "-m", "pip", "install", "pyinstaller"], check=True)

    nims_root = Path(__file__).resolve().parent
    gui_script = nims_root / "src" / "nims_viewer" / "gui_app.py"
    icon_path = ensure_icon(nims_root, venv_python)

    print("2. NimsViewer.ico 아이콘 준비 완료")
    print("3. NimsViewer.exe 단일 파일 빌드 시작...")
    cmd = [
        venv_python,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name=NimsViewer",
        "--icon",
        str(icon_path),
        "--paths=src",
        str(gui_script),
    ]
    subprocess.run(cmd, cwd=str(nims_root), check=True)

    dist_exe = nims_root / "dist" / "NimsViewer.exe"
    if dist_exe.exists():
        print("\n========================================================")
        print("🎉 EXE 빌드 성공!")
        print(f"실행 파일 위치: {dist_exe}")
        print(f"아이콘 위치: {icon_path}")
        print("이 파일 하나만 복사해서 어느 PC에서든 바로 사용하실 수 있습니다.")
        print("========================================================")


if __name__ == "__main__":
    build_exe()
