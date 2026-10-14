# -*- coding: utf-8 -*-
"""이동취약 읍면동 선별·집계·시각화. 입력: out/emd_merged.csv, data/hjd.geojson  출력: out/*.png, out/results.json"""
import sys, re, json, math
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.ticker
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon as MPoly
from scipy.stats import spearmanr
from shapely.geometry import shape

D = sys.argv[1] if len(sys.argv) > 1 else 'data'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'out'
for f in ['malgun.ttf', 'malgunbd.ttf']:
    try: fm.fontManager.addfont(r'C:/Windows/Fonts/' + f)
    except Exception: pass
plt.rcParams.update({'font.family': 'Malgun Gothic', 'axes.unicode_minus': False, 'figure.dpi': 200,
                     'axes.spines.top': False, 'axes.spines.right': False})
C_VUL, C_OLD, C_BASE, C_TXT = '#D55E00', '#0072B2', '#C9CED6', '#333333'

m = pd.read_csv(f'{OUT}/emd_merged.csv')
m = m[~m.unit.str.contains('잔여')].copy()
m['t'] = np.where(m.unit.str.endswith('읍'), '읍', np.where(m.unit.str.endswith('면'), '면', '동'))
SIDO = ['서울특별시', '부산광역시', '대구광역시', '인천광역시', '광주광역시', '대전광역시', '울산광역시', '세종특별자치시', '경기도',
        '강원특별자치도', '충청북도', '충청남도', '전북특별자치도', '전라남도', '경상북도', '경상남도', '제주특별자치도']
def sido(u):
    for s in SIDO:
        if u.startswith(s): return s
    return '기타'
m['sido'] = m.unit.map(sido)
m['sg'] = [u[len(s):] if u.startswith(s) else u for u, s in zip(m.sgg, m.sido)]
# 수집 누락 의심 시군구 판정(3개 규칙, 하나라도 해당하면 분석에서 제외)
#  (1) 정류장 0개인 '동'이 3개 이상  (2) 인구 1천명당 정류장: 시 1.0 미만, 군 2.5 미만  (3) 정류장 0개 읍면동 3개 이상이면서 1천명당 정류장 5 미만
gs = m.groupby('sgg').agg(stops=('stops', 'sum'), pop=('pop', 'sum'), zero_all=('stops', lambda s: int((s == 0).sum())))
gs['p'] = gs.stops / gs['pop'] * 1000
gs['zero_dong'] = m[(m.stops == 0) & (m.t == '동')].groupby('sgg').size().reindex(gs.index).fillna(0)
is_gun = gs.index.str.endswith('군'); is_si = gs.index.str.endswith('시')
flag = (gs.zero_dong >= 3) | (is_si & (gs.p < 1.0)) | (is_gun & (gs.p < 2.5)) | ((gs.zero_all >= 3) & (gs.p < 5))
excl = sorted(gs.index[flag])
gs[flag].to_csv(f'{OUT}/table_excluded.csv', encoding='utf-8-sig')
all_n = len(m)
m['excluded'] = m.sgg.isin(excl)
print('제외 시군구', excl)
A = m[~m.excluded].copy()
A['share'] = A.old65 / A['pop']; A['dens'] = A.stops / A.area
R = {'excluded_sgg': excl, 'n_all': all_n, 'n_excl': int(m.excluded.sum()), 'n': len(A),
     'pop': int(A['pop'].sum()), 'old': int(A.old65.sum()), 'stops': int(A.stops.sum()), 'area': float(A.area.sum())}
R['old_share'] = R['old'] / R['pop']
LIM5 = 1 / (math.pi * .5 * .5)
rows = []
for t, g in A.groupby('t'):
    rows.append(dict(유형=t, 읍면동수=len(g), 인구=int(g['pop'].sum()), 고령인구=int(g.old65.sum()),
                     고령비중=g.old65.sum() / g['pop'].sum(), 정류장=int(g.stops.sum()), 면적=g.area.sum(),
                     밀도=g.stops.sum() / g.area.sum(), 정류장당면적ha=g.area.sum() / g.stops.sum() * 100,
                     고령자천명당정류장=g.stops.sum() / g.old65.sum() * 1000,
                     밀도기준미만비율=(g.dens < LIM5).mean(), 중위면적=g.area.median()))
T = pd.DataFrame(rows).set_index('유형').loc[['동', '읍', '면']]
T.to_csv(f'{OUT}/table_type.csv', encoding='utf-8-sig'); R['type'] = T.reset_index().to_dict('records')
R['rho'] = spearmanr(A.share, A.dens)[0]

def vul(r, th=.4):
    lim = 1 / (math.pi * r * r)
    return (A.share >= th) & (A.dens < lim), lim
sens = []
for r in [.3, .4, .5]:
    v, lim = vul(r)
    sens.append(dict(r=r, lim=lim, n=int(v.sum()), pop=int(A.loc[v, 'pop'].sum()), old=int(A.loc[v, 'old65'].sum()),
                     area=float(A.loc[v, 'area'].sum()), mian=int((v & (A.t == '면')).sum())))
R['sens'] = sens
v, lim = vul(.5); A['vul'] = v
V = A[A.vul]
R['vul'] = dict(n=len(V), pop=int(V['pop'].sum()), old=int(V.old65.sum()), area=float(V.area.sum()), stops=int(V.stops.sum()),
                zero=int((V.stops == 0).sum()), by_t=V.t.value_counts().to_dict(),
                area_ha_per_stop=float(V.area.sum() / max(V.stops.sum(), 1) * 100),
                old_share_of_all_old=float(V.old65.sum() / A.old65.sum()), area_share=float(V.area.sum() / A.area.sum()),
                pop_share=float(V['pop'].sum() / A['pop'].sum()), median_share=float(V.share.median()),
                n_stop_lt5=int((V.stops < 5).sum()), n_mian_total=int((A.t == '면').sum()),
                mian_vul_ratio=float(((A.t == '면') & A.vul).sum() / (A.t == '면').sum()))
A['band'] = pd.cut(A.share, [0, .2, .3, .4, .5, 1], labels=['20% 미만', '20~30%', '30~40%', '40~50%', '50% 이상'], right=False)
B = A.groupby('band', observed=True).agg(n=('unit', 'size'), pop=('pop', 'sum'), stops=('stops', 'sum'), area=('area', 'sum'),
                                         low=('dens', lambda s: (s < lim).mean()))
B['dens'] = B.stops / B.area; B.to_csv(f'{OUT}/table_band.csv', encoding='utf-8-sig')
R['band'] = B.reset_index().astype({'band': str}).to_dict('records')
S = A.groupby('sido').agg(n=('unit', 'size'), vn=('vul', 'sum'), pop=('pop', 'sum')).sort_values('vn', ascending=False)
S['vpop'] = V.groupby('sido')['pop'].sum(); S['vold'] = V.groupby('sido')['old65'].sum(); S = S.fillna(0)
S.to_csv(f'{OUT}/table_sido.csv', encoding='utf-8-sig'); R['sido'] = S.reset_index().to_dict('records')
G = V.groupby(['sido', 'sg']).agg(vn=('unit', 'size'), vpop=('pop', 'sum'), vold=('old65', 'sum'), varea=('area', 'sum'),
                                   vstops=('stops', 'sum')).reset_index()
tot = A.groupby(['sido', 'sg']).agg(n=('unit', 'size')).reset_index()
G = G.merge(tot, on=['sido', 'sg']); G['ratio'] = G.vn / G.n
G = G.sort_values(['vn', 'vold'], ascending=False); G.to_csv(f'{OUT}/table_sigungu.csv', encoding='utf-8-sig', index=False)
R['sg_top'] = G.head(15).to_dict('records'); R['sg_count'] = len(G)
R['sg_ge5'] = int((G.vn >= 5).sum()); R['sg_ge5_share'] = float(G[G.vn >= 5].vn.sum() / G.vn.sum())
R['top10_share'] = float(G.head(10).vn.sum() / G.vn.sum())
R['sg_total'] = int(A.groupby(['sido', 'sg']).ngroups)
V.sort_values(['old65'], ascending=False).head(20)[['sido', 'sg', 'unit', 'pop', 'old65', 'share', 'area', 'stops']].to_csv(
    f'{OUT}/table_top_units.csv', encoding='utf-8-sig', index=False)
A.to_csv(f'{OUT}/emd_final.csv', index=False, encoding='utf-8-sig')
json.dump(R, open(f'{OUT}/results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)

# ---------- 그림 1 ----------
fig, ax = plt.subplots(figsize=(7.4, 4.4))
d = A.copy(); d['dd'] = d.dens.clip(lower=0.01)
ax.scatter(d.loc[~d.vul, 'share'] * 100, d.loc[~d.vul, 'dd'], s=5, c=C_BASE, alpha=.55, linewidths=0, label='그 외 읍면동')
ax.scatter(d.loc[d.vul, 'share'] * 100, d.loc[d.vul, 'dd'], s=8, c=C_VUL, alpha=.8, linewidths=0, label=f'이동취약 읍면동 ({len(V)}개)')
ax.set_yscale('log'); ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:g}')); ax.axhline(lim, color=C_TXT, lw=.8, ls='--'); ax.axvline(40, color=C_TXT, lw=.8, ls='--')
ax.text(64, lim * 1.15, f'정류장 밀도 {lim:.2f}개/㎢', ha='right', fontsize=7.5, color=C_TXT)
ax.text(40.6, 70, '고령비중 40%', fontsize=7.5, color=C_TXT)
ax.set_xlabel('65세 이상 인구 비중(%)'); ax.set_ylabel('정류장 밀도(개/㎢, 로그)')
ax.legend(loc='upper right', frameon=False, fontsize=8, markerscale=2.5)
ax.set_title(f'읍면동 {len(A):,}개의 고령비중과 정류장 밀도 (Spearman ρ = {R["rho"]:.2f})', fontsize=10, loc='left')
fig.text(0.01, 0.005, '자료: 국토교통부 전국 버스정류장 위치정보(2025.10.31), 행정안전부 주민등록 연령별 인구(2025.10), 행정동 경계(2025.10.01) / 정류장 0개는 0.01로 표시', fontsize=5.5, color='#666')
fig.tight_layout(rect=(0, .02, 1, 1)); fig.savefig(f'{OUT}/fig1_scatter.png'); plt.close(fig)

# ---------- 그림 2 ----------
fig, axs = plt.subplots(1, 3, figsize=(7.4, 2.4))
for ax, (k, ttl, fmt) in zip(axs, [('밀도', '정류장 밀도(개/㎢)', '{:.1f}'), ('고령비중', '65세 이상 비중(%)', '{:.1f}'),
                                      ('정류장당면적ha', '정류장 1개당 면적(ha)', '{:,.0f}')]):
    vals = T[k] * (100 if k == '고령비중' else 1)
    bars = ax.bar(T.index, vals, color=C_OLD, width=.6)
    for b_, vv in zip(bars, vals): ax.text(b_.get_x() + b_.get_width() / 2, vv, fmt.format(vv), ha='center', va='bottom', fontsize=8)
    ax.set_title(ttl, fontsize=9, loc='left'); ax.set_ylim(0, vals.max() * 1.18); ax.tick_params(labelsize=8)
fig.tight_layout(); fig.savefig(f'{OUT}/fig2_type.png'); plt.close(fig)

# ---------- 그림 3: 지도 ----------
g = json.load(open(f'{D}/hjd.geojson', encoding='utf-8'))
norm = lambda x: re.sub(r'[\s·.,ㆍ]', '', x)
st = dict(zip(A.unit, A.vul))
fig, ax = plt.subplots(figsize=(5.2, 6.0))
polys = {'base': [], 'vul': []}
for f in g['features']:
    k = norm(f['properties']['adm_nm'])
    geom = shape(f['geometry']).simplify(0.004)
    parts = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
    cat = 'vul' if st.get(k, False) else 'base'
    for p_ in parts:
        if p_.is_empty: continue
        polys[cat].append(MPoly(np.array(p_.exterior.coords), closed=True))
ax.add_collection(PatchCollection(polys['base'], facecolor='#E6E9EE', edgecolor='#FFFFFF', linewidth=.1))
ax.add_collection(PatchCollection(polys['vul'], facecolor=C_VUL, edgecolor=C_VUL, linewidth=.2))
ax.set_xlim(124.5, 131.9); ax.set_ylim(33.0, 38.7); ax.set_aspect(1.22); ax.axis('off')
ax.set_title(f'이동취약 읍면동 {len(V)}개 분포\n(고령비중 40% 이상 + 정류장 밀도 {lim:.2f}개/㎢ 미만)', fontsize=9, loc='left')
fig.text(0.02, 0.01, '회색: 그 외·분석 제외 지역 / 경계: vuski/admdongkor 2025.10.01', fontsize=6, color='#666')
fig.tight_layout(); fig.savefig(f'{OUT}/fig3_map.png'); plt.close(fig)

# ---------- 그림 4 ----------
top = G.head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(7.4, 3.4))
ab = {'강원특별자치도': '강원', '경기도': '경기', '충청북도': '충북', '충청남도': '충남', '전북특별자치도': '전북', '전라남도': '전남',
      '경상북도': '경북', '경상남도': '경남', '제주특별자치도': '제주', '인천광역시': '인천', '부산광역시': '부산', '대구광역시': '대구',
      '울산광역시': '울산', '광주광역시': '광주', '대전광역시': '대전', '세종특별자치시': '세종', '서울특별시': '서울'}
labels = [f'{r.sg} ({ab.get(r.sido, r.sido)})' for r in top.itertuples()]
ax.barh(labels, top.vn, color=C_VUL, height=.65)
for y, (a, b_) in enumerate(zip(top.vn, top.n)): ax.text(a + .1, y, f'{int(a)}개 / 전체 {int(b_)}개', va='center', fontsize=7.5)
ax.set_xlabel('이동취약 읍면동 수'); ax.tick_params(labelsize=8); ax.set_xlim(0, top.vn.max() * 1.3)
ax.set_title('이동취약 읍면동이 많은 시·군 상위 15곳', fontsize=10, loc='left')
fig.tight_layout(); fig.savefig(f'{OUT}/fig4_sigungu.png'); plt.close(fig)
print(json.dumps({k: R[k] for k in ['n', 'pop', 'old', 'stops', 'rho', 'vul', 'sens', 'sg_count', 'sg_total', 'sg_ge5', 'sg_ge5_share', 'top10_share']},
                 ensure_ascii=False, indent=1, default=float))
