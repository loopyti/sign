#!/bin/bash
mkdir -p /app/ephe

echo "ephe 파일 다운로드 중..."
curl -L "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/seas_18.se1" -o /app/ephe/seas_18.se1 && echo "✅ seas_18.se1" || echo "❌ 실패"
curl -L "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/semo_18.se1" -o /app/ephe/semo_18.se1 && echo "✅ semo_18.se1" || echo "❌ 실패"
curl -L "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/sepl_18.se1" -o /app/ephe/sepl_18.se1 && echo "✅ sepl_18.se1" || echo "❌ 실패"

echo "파일 목록:"
ls -la /app/ephe/

uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
