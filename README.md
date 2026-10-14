# 고령 농촌 읍면동의 버스정류장 접근성 격차 분석

AI와 함께하는 교통문제 해결을 위한 데이터 분석 공모전(숲과나눔·한겨레) 제출 분석 코드.
전국 읍면동 단위로 65세 이상 인구 비중과 버스정류장 밀도를 결합해 "이동취약 읍면동"을 식별하고 DRT 우선 도입 지역을 제안한다.

## 데이터 (모두 로그인·API 키 불필요, 00_download.py 가 내려받음)
| 데이터 | 제공기관 | URL | 기준 |
|---|---|---|---|
| 전국 버스정류장 위치정보 | 국토교통부 | https://www.data.go.kr/data/15067528/fileData.do | 2025-10-31 |
| 연령별 인구현황(읍면동, 1세 단위) | 행정안전부 | https://jumin.mois.go.kr/ageStatMonth.do | 2025-10 |
| 행정동 경계 GeoJSON | vuski/admdongkor (원자료 통계청 SGIS, CC BY 4.0) | https://github.com/vuski/admdongkor | 2025-10-01 |

원자료 파일은 용량 문제로 저장소에 포함하지 않는다.

## 실행 순서
```
pip install pandas numpy shapely scipy matplotlib python-docx
python 00_download.py data            # 원자료 다운로드
python 01_prepare.py data out         # 정류장-경계 공간결합, 인구 결합 -> out/emd_merged.csv
python 02_analysis.py data out        # 취약 읍면동 선별, 표·그림 -> out/*.csv, out/*.png, out/results.json
python 03_build_report.py out report.docx <코드 URL>   # 보고서 생성 (선택)
```
- 그림 한글 글꼴은 Malgun Gothic(Windows)을 사용한다. 다른 환경에서는 02_analysis.py 의 글꼴 설정을 바꾼다.

## 산출물 (out/)
- emd_final.csv : 분석 대상 3,042개 읍면동 (인구, 65세 이상, 정류장 수, 면적, 취약 여부)
- table_sigungu.csv, table_sido.csv, table_type.csv, table_band.csv, table_top_units.csv, table_excluded.csv
- fig1_scatter.png, fig2_type.png, fig3_map.png, fig4_sigungu.png, results.json

## 방법 요약
- 정류장 좌표를 행정동 경계에 포인트-인-폴리곤으로 배정(99.92%), 이름 정규화 후 인구표와 결합.
- 정류장 밀도 = 정류장 수 / 면적(㎢, 경위도 경계의 위도 보정 근사).
- 이동취약 = 65세 이상 비중 40% 이상 AND 정류장 밀도 < 1/(π·0.5²)=1.27개/㎢. 반경 300m·400m 민감도 포함.
- 정류장 수집 누락 의심 시군구(규칙은 02_analysis.py 상단)는 분석에서 제외.

## 한계
정류장 수는 운행 빈도를 반영하지 않으며, 읍면동 평균 밀도라서 마을 단위 보행거리는 반영하지 못한다.

## AI 활용
Anthropic Claude(Claude Code)로 데이터 수집 스크립트, 분석 코드, 보고서 초안을 작성했다. 모든 수치는 이 코드가 공개 데이터에서 계산한다.
