# -*- coding: utf-8 -*-
"""읍면동 단위 데이터셋 구축: 정류장(국토부) + 주민등록 연령별 인구(행안부) + 행정동 경계(vuski/admdongkor)"""
import sys, re, json, math
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np, pandas as pd
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
D = sys.argv[1] if len(sys.argv) > 1 else 'data'   # 원자료 폴더
import os; os.makedirs(sys.argv[2] if len(sys.argv) > 2 else 'out', exist_ok=True)
OUT = sys.argv[2] if len(sys.argv) > 2 else 'out'

# 1) 인구 (읍면동, 1세 단위)
p = pd.read_csv(f'{D}/pop_emd1.csv', encoding='cp949', low_memory=False)
c0 = p.columns[0]
p['name'] = p[c0].str.replace(r'\s*\(\d{10}\)', '', regex=True).str.strip()
p['code'] = p[c0].str.extract(r'\((\d{10})\)')[0]
p = p[p['code'].str[5:] != '00000'].copy()          # 읍면동 행만
def num(s): return pd.to_numeric(s.astype(str).str.replace(',', ''), errors='coerce').fillna(0)
tot = num(p[[c for c in p.columns if c.endswith('계_총인구수')][0]])
old = sum(num(p[c]) for c in p.columns
          if re.search(r'계_(\d+)세', c) and int(re.search(r'계_(\d+)세', c).group(1)) >= 65)
old = old + sum(num(p[c]) for c in p.columns if c.endswith('계_100세 이상'))
p['pop'] = tot.values; p['old65'] = old.values
p = p[['name', 'code', 'pop', 'old65']]

# 2) 경계
g = json.load(open(f'{D}/hjd.geojson', encoding='utf-8'))
rows, geoms = [], []
for f in g['features']:
    pr = f['properties']; geom = shape(f['geometry'])
    lat0 = geom.centroid.y; kx = 111.32 * math.cos(math.radians(lat0)); ky = 110.57
    # 위도 보정 근사 면적(km2) : 경위도 좌표의 부호 면적에 위도별 환산계수 적용
    area = abs(geom.area) * kx * ky
    rows.append(dict(adm_nm=pr['adm_nm'], sidonm=pr['sidonm'], sggnm=pr['sggnm'], area=area)); geoms.append(geom)
b = pd.DataFrame(rows)

# 3) 정류장 -> 경계 공간결합
s = pd.read_csv(f'{D}/stops.csv', encoding='cp949').dropna(subset=['위도', '경도'])
s = s[(s['위도'].between(33, 39)) & (s['경도'].between(124, 132))]
tree = STRtree(geoms)
pts = [Point(x, y) for x, y in zip(s['경도'], s['위도'])]
idx = tree.query(pts, predicate='within')           # (pt_idx, geom_idx)
cnt = np.zeros(len(geoms), int)
hit = np.zeros(len(pts), bool)
for pi, gi in zip(*idx):
    if not hit[pi]: cnt[gi] += 1; hit[pi] = True
b['stops'] = cnt
print('정류장 전체', len(s), '경계 내 배정', int(hit.sum()))

# 4) 이름 결합 (표기 차이 정규화 후 결합, 남는 동은 시군구 단위 '잔여' 묶음으로 합산)
def norm(x): return re.sub(r'[\s·.,ㆍ]', '', x)
b['key'] = b['adm_nm'].map(norm); p['key'] = p['name'].map(norm)
p['sgg'] = p['name'].str.split().str[:-1].str.join(' ').map(norm)
b['sgg'] = b['adm_nm'].str.split().str[:-1].str.join(' ').map(norm)
b['unit'] = b['key']; p['unit'] = p['key']
common = set(b['key']) & set(p['key'])
b.loc[~b['key'].isin(common), 'unit'] = b['sgg'] + ' (잔여동)'
p.loc[~p['key'].isin(common), 'unit'] = p['sgg'] + ' (잔여동)'
B = b.groupby('unit').agg(area=('area', 'sum'), stops=('stops', 'sum'), sgg=('sgg', 'first')).reset_index()
P = p.groupby('unit').agg(pop=('pop', 'sum'), old65=('old65', 'sum')).reset_index()
m = B.merge(P, on='unit', how='outer', indicator=True)
print(m['_merge'].value_counts().to_string())
print('인구 총합', int(P['pop'].sum()), '결합 인구', int(m.loc[m['_merge'] == 'both', 'pop'].sum()))
print('정류장 총합(경계)', int(B['stops'].sum()), '결합 정류장', int(m.loc[m['_merge'] == 'both', 'stops'].sum()))
print(m[m['_merge'] != 'both'].head(20).to_string())
print('결합 제외(경계·인구 한쪽만 존재):', int((m['_merge'] != 'both').sum()), '단위 / 제외 인구', int(m.loc[m['_merge'] == 'right_only', 'pop'].sum()), '/ 제외 정류장', int(m.loc[m['_merge'] == 'left_only', 'stops'].sum()))
m = m[m['_merge'] == 'both'].drop(columns='_merge')
m.to_csv(f'{OUT}/emd_merged.csv', index=False, encoding='utf-8-sig')
