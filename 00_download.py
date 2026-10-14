# -*- coding: utf-8 -*-
"""원자료 내려받기(로그인·API키 불필요). 사용: python 00_download.py data
 1) 국토교통부 전국 버스정류장 위치정보  (공공데이터포털 파일데이터 15067528, 2025.10.31 수집분)
 2) 행정안전부 주민등록 연령별 인구현황(읍면동, 1세 단위, 2025년 10월)  (jumin.mois.go.kr)
 3) 행정동 경계 GeoJSON 2025.10.01 (vuski/admdongkor, 원자료 통계청 SGIS, CC BY 4.0)
"""
import sys, os, urllib.request, urllib.parse, http.cookiejar
out = sys.argv[1] if len(sys.argv) > 1 else 'data'
os.makedirs(out, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0'}
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def get(url, path, data=None, ref=None):
    h = dict(UA)
    if ref: h['Referer'] = ref
    req = urllib.request.Request(url, data=data, headers=h)
    with op.open(req, timeout=300) as r, open(path, 'wb') as f:
        f.write(r.read())
    print('저장', path, os.path.getsize(path))

get('https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003558143&fileDetailSn=1&insertDataPrcus=N',
    f'{out}/stops.csv', ref='https://www.data.go.kr/data/15067528/fileData.do')

op.open(urllib.request.Request('https://jumin.mois.go.kr/ageStatMonth.do', headers=UA)).read()   # 세션 쿠키 확보
form = dict(sltOrgType='1', sltOrgLvl1='A', sltOrgLvl2='', gender='gender', sum='sum', sltUndefType='',
            searchYearStart='2025', searchMonthStart='10', searchYearEnd='2025', searchMonthEnd='10',
            sltOrderType='1', sltOrderValue='ASC', sltArgTypes='1', sltArgTypeA='0', sltArgTypeB='120',
            category='month', state='3')           # state=3: 전체 읍면동 현황
get('https://jumin.mois.go.kr/downloadCsvAge.do?searchYearMonth=month&xlsStats=3', f'{out}/pop_emd1.csv',
    data=urllib.parse.urlencode(form).encode())

get('https://raw.githubusercontent.com/vuski/admdongkor/master/ver20251001/HangJeongDong_ver20251001.geojson',
    f'{out}/hjd.geojson')
