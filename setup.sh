#!/bin/bash

# 1️⃣ 패키지 업데이트 및 필수 패키지 설치
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose

# 2️⃣ Docker 서비스 활성화
sudo systemctl enable docker
sudo systemctl start docker

# 3️⃣ 현재 사용자를 Docker 그룹에 추가 (재부팅 필요)
sudo usermod -aG docker $cdsn

# 4️⃣ Docker Compose를 사용하여 컨테이너 빌드 및 실행
cd ~/LAPRAS
docker compose up --build -d
