#!/usr/bin/env python3
"""
requirements.txt의 패키지 크기를 분석하는 스크립트
"""
import subprocess
import tempfile
import os
import sys

def get_package_size(package_name):
    """패키지를 임시 디렉토리에 설치하고 크기 측정"""
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # pip install을 임시 디렉토리에
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-q', '-t', tmpdir, package_name],
                capture_output=True,
                timeout=60
            )
            
            # 디렉토리 크기 측정
            result = subprocess.run(
                ['du', '-sh', tmpdir],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                size_str = result.stdout.split()[0]
                return size_str
        except Exception as e:
            return None
    return None

def size_to_mb(size_str):
    """크기 문자열을 MB로 변환"""
    if not size_str:
        return 0
    
    units = {'K': 0.001, 'M': 1, 'G': 1024}
    try:
        if size_str[-1] in units:
            return float(size_str[:-1]) * units[size_str[-1]]
        return float(size_str) / (1024 * 1024)  # bytes to MB
    except:
        return 0

# requirements.txt 파싱
packages = []
with open('requirements.txt', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            # 버전 정보 분리
            pkg_name = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
            if pkg_name:
                packages.append(pkg_name)

print("패키지 크기 분석 중...")
print("=" * 70)

results = []
for pkg in packages:
    print(f"분석 중: {pkg}...", end=' ', flush=True)
    size = get_package_size(pkg)
    if size:
        size_mb = size_to_mb(size)
        results.append((pkg, size, size_mb))
        print(f"✓ {size}")
    else:
        print("✗")

print("\n" + "=" * 70)
print("패키지 크기 순위 (큰 것부터):")
print("=" * 70)

results.sort(key=lambda x: x[2], reverse=True)

for pkg, size, size_mb in results:
    print(f"{size:>10} ({size_mb:>6.1f}MB) - {pkg}")

print("\n" + "=" * 70)
total_mb = sum(r[2] for r in results)
print(f"총 크기: {total_mb:.1f}MB")
print("=" * 70)

