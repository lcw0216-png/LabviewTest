# VI_INDEX — 128CH AI DAQ (NI 9178 x2, NI 9203 x16)

| VI | 역할 |
|---|---|
| AI_DAQ_Main.vi | 메인: 캔버스 UI 상태머신(Init/Wait/Update/Settings/Start/Stop/Save/Channel/Graph/Exit) + DAQ 엔진 병렬 실행 |
| DAQ/DAQ_Engine.vi | 큐 명령 기반 측정 엔진: 2개 섀시 태스크 연속 샘플링, 스케일, TDMS 로깅, LIVE/GRAPH 큐 송신 |
| DAQ/DAQ_Scale.vi | 4–20 mA 원시값 → Scale Min..Max 변환, 채널 평균값 |
| DAQ/TDMS_Make_Path.vi | 저장 폴더 → AI_YYYYMMDD_HHMMSS.tdms 경로 생성 |
| DAQ/TDMS_Write_Log.vi | Save=true 채널만 TDMS("AI Data" 그룹) 기록 |
| DAQ/Ch_Defaults.vi | 128채널 기본 설정(CH001..CH128, 한계 80/20, 0–100 %) |
| DAQ/Ch_Apply.vi | 채널 설정 1개 교체 또는 전체 적용(이름/값 제외) |
| DAQ/Ch_Merge_Values.vi | 측정값 배열을 채널 클러스터 Value에 병합 |
| UI/UI_Render_Main.vi | 전체 화면(헤더+타일+그래프) 그리기 |
| UI/UI_Header_Layout.vi | PPT 스타일 헤더 버튼 위치 정의 |
| UI/UI_Draw_Buttons.vi | 버튼 그리기(hover/비활성 표시) |
| UI/UI_Hit_Test.vi | 버튼 클릭 판정 |
| UI/UI_Draw_Tiles.vi | 128 타일 그리드(16열 x 8행) 그리기 |
| UI/UI_Draw_Tile.vi | 타일 1개: 값/단위, 상·하한 초과 점멸, G/S 배지 |
| UI/UI_Tile_Hit.vi | 타일 클릭 → 채널 인덱스 |
| UI/UI_Draw_Graph.vi | 선택 채널 그래프(자동 스케일, 격자, 범례) |
| UI/UI_Graph_Series.vi | 한 채널 선 그리기(최대 600점) |
| UI/UI_Status_Text.vi | 상태 표시줄 문자열 |
| UI/UI_Point_XY.vi | 마우스 좌표 → 점 클러스터 |
| Dialogs/Dlg_Settings.vi | 측정 설정 팝업(샘플링 속도, 샘플 수, 채널, 저장 폴더) |
| Dialogs/Dlg_Channel.vi | 채널 설정 팝업(상/하한, Save, Graph, 스케일, 단위, 전체 적용) |
| Dialogs/Dlg_Graph.vi | 그래프 별도 창(1300x720, 100 ms 갱신) |
| Tests/Test_Engine.vi | 엔진 단독 측정+로깅 테스트(PASSED) |
| Tests/Test_Render.vi | 화면 렌더링 PNG 테스트 |
| Typedefs/*.ctl | Channel, DAQ_Settings, UI_State, DAQ_Cmd |
