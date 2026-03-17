#!/bin/bash
mkdir -p /app/ephe

echo "ephe 파일 다운로드 중..."
wget -q "https://github.com/aloistr/swisseph/raw/master/ephe/seas_18.se1" -O /app/ephe/seas_18.se1 && echo "✅ seas_18.se1" || echo "❌ seas_18.se1 실패"
wget -q "https://github.com/aloistr/swisseph/raw/master/ephe/semo_18.se1" -O /app/ephe/semo_18.se1 && echo "✅ semo_18.se1" || echo "❌ semo_18.se1 실패"
wget -q "https://github.com/aloistr/swisseph/raw/master/ephe/sepl_18.se1" -O /app/ephe/sepl_18.se1 && echo "✅ sepl_18.se1" || echo "❌ sepl_18.se1 실패"

echo "다운로드 완료 - 파일 확인:"
ls -la /app/ephe/

uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}

