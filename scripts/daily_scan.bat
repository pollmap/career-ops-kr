@echo off
REM career-ops-kr 매일 자동 스캔 (Windows Task Scheduler용)
REM 설정: 작업 스케줄러 > 새 작업 > 트리거: 매일 09:00 > 동작: 이 배치 파일 실행

cd /d "C:\Users\lch68\Desktop\05_개발·도구\career-ops-kr"
set PYTHONIOENCODING=utf-8

REM 1. 채널 스캔 (aggregator 포함, AI 채점, 상위 30건)
python -m career_ops_kr.cli auto-pipeline --source both --ai-score --limit 30 --grade C < NUL

REM 2. 결과 로그
echo [%DATE% %TIME%] Daily scan completed >> data\scan_history.log
