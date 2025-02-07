# 1️⃣ Base Image: Python 환경 설정
FROM python:3.9-slim

# 2️⃣ 작업 디렉토리 설정
WORKDIR /app

# 3️⃣ 필수 패키지 설치 (Python 환경에 맞게 조정)
RUN apt-get update && apt-get install -y \
    libusb-dev bash \
    && rm -rf /var/lib/apt/lists/*

# 4️⃣ requirements 파일 복사
COPY requirements /app/requirements

# 5️⃣ 라이브러리 설치 (각 requirements 파일에서 자동 설치)
RUN pip install --no-cache-dir -r /app/requirements/base.txt

# 6️⃣ 환경 변수 설정
ENV LAPRAS_HOME="/app"
ENV LAPRAS_LOG_LEVEL="INFO"
ENV CONFIG_URL="http://lapras.kaist.ac.kr/conf/default.conf"

# 7️⃣ LAPRAS 프로젝트 코드 복사
COPY middleware /app/middleware
COPY agents /app/agents
COPY utils /app/utils

# 8️⃣ 포트 설정
EXPOSE 8080

# 9️⃣ 실행 명령 설정 (Python 메인 실행 파일 설정)
#ENTRYPOINT ["python", "-m", "middleware.core.agent"]   # 아직 미구현
