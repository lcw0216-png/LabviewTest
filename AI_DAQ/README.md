# 128CH AI DAQ 모니터 (LabVIEW)

NI cDAQ-9178 x2 + NI 9203 x16 (4–20 mA) 128채널 측정·가시화.

- 실행: `AI_DAQ.lvproj` → `AI_DAQ_Main.vi` (NI MAX 장치명 cDAQ1, cDAQ2)
- 버튼: 설정 / 측정 시작 / 측정 정지 / 데이터 저장(TDMS, Save 채널만) / 그래프 창 / 종료
- 타일 클릭: 채널별 상·하한, 저장, 그래프 표시, 스케일 설정 (한계 초과 시 점멸)
- `src/`: VI 생성용 AIXML, `Data/`: TDMS 저장 폴더
- VI 목록: VI_INDEX.md
