import fitz, json, re, math
from collections import defaultdict
SRC='Rapport_Diagnostic_Operationnel_Rapide_ESS_EpiC_RDC_FHI360_ICHESS_Rapport_final_version_propre_05-11-26.pdf'

def cluster(vals,tol=1.5):
 vals=sorted(vals); out=[]
 for v in vals:
  if not out or v-out[-1][-1]>tol: out.append([v])
  else: out[-1].append(v)
 return [sum(g)/len(g) for g in out]

def grid_lines(page,region,min_len_frac=0.08):
 ys=[]; xs=[]
 W=region.width; H=region.height
 for dr in page.get_drawings():
  r=fitz.Rect(dr['rect'])
  if not r.intersects(region): continue
  # filled rectangles that are thin lines
  if dr.get('fill') is not None:
   if r.width>=min_len_frac*W and r.height<=1.5: ys.append(r.y0)
   if r.height>=5 and r.width<=1.5: xs.append(r.x0)
  for it in dr['items']:
   if it[0]=='l':
    a,b=it[1],it[2]
    if abs(a.y-b.y)<0.5 and max(a.x,b.x)-min(a.x,b.x)>=min_len_frac*W: ys.append(a.y)
    if abs(a.x-b.x)<0.5 and max(a.y,b.y)-min(a.y,b.y)>=5: xs.append(a.x)
   elif it[0]=='re':
    r=fitz.Rect(it[1])
    if r.width>=min_len_frac*W and r.height<=1.5: ys.append(r.y0)
    if r.height>=5 and r.width<=1.5: xs.append(r.x0)
 return cluster(ys),cluster(xs)

def cell_text(page,rect):
 txt=page.get_text('text',clip=rect,sort=True)
 lines=[re.sub(r'\s+',' ',l).strip() for l in txt.splitlines() if l.strip()]
 return ' '.join(lines).strip()

def extract(page_no,region,min_len_frac=0.08):
 d=fitz.open(SRC); p=d[page_no-1]
 ys,xs=grid_lines(p,fitz.Rect(region),min_len_frac)
 # keep boundaries within region
 ys=[v for v in ys if region[1]-2<=v<=region[3]+2]
 xs=[v for v in xs if region[0]-2<=v<=region[2]+2]
 # strip near duplicates at edge
 print('PAGE',page_no,'ys',len(ys),[round(v,1) for v in ys[:50]])
 print('PAGE',page_no,'xs',len(xs),[round(v,1) for v in xs[:20]])
 rows=[]
 for i in range(len(ys)-1):
  row=[]
  for j in range(len(xs)-1):
   rect=fitz.Rect(xs[j],ys[i],xs[j+1],ys[i+1])
   row.append(cell_text(p,rect))
  rows.append(row)
 return rows

if __name__=='__main__':
 regions={
  9:(56,82,540,785), 10:(56,60,540,545), 15:(55,505,541,750), 17:(54,426,513,578),
  20:(55,112,541,657),22:(54,148,516,384),23:(55,83,541,373),24:(55,83,541,402)
 }
 allrows={}
 for n,r in regions.items():
  rows=extract(n,r)
  allrows[n]=rows
  print(' rows',len(rows),'cols',max(len(x) for x in rows))
  for row in rows[:3]: print('  ',row)
  print('  ...')
  for row in rows[-2:]: print('  ',row)
 json.dump(allrows,open('work/tables_raw.json','w'),ensure_ascii=False,indent=1)
