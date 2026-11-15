"""Small GPT-2-era in-domain sanity check; not modern-model validation."""
import sys,json,time,urllib.request,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from detector.text import analyze_text,TextError
from detector.assets import ROOT
rows=[]
for source,label in [('webtext.test.jsonl',0),('xl-1542M.test.jsonl',1)]:
    url='https://openaipublic.azureedge.net/gpt-2/output-dataset/v1/'+source
    with urllib.request.urlopen(url,timeout=60) as response:
        for index,line in enumerate(response):
            if index>=10:break
            item=json.loads(line);text=item['text']
            record={'label':label,'source':source,'row':index,'text_sha256':hashlib.sha256(text.encode()).hexdigest()}
            try:
                start=time.perf_counter();result=analyze_text(text)
                record.update(predicted_ai=result['is_ai'],score=result['model_ai_score'],tokens_analyzed=result['tokens_analyzed'],seconds=time.perf_counter()-start)
            except TextError as exc:
                record['excluded']=str(exc)
            rows.append(record)
path=ROOT/'external'/'text_smoke_results.json'
path.write_text(json.dumps(rows,indent=2))
eligible=[r for r in rows if 'excluded' not in r]
print('Correct:',sum(r['label']==r['predicted_ai'] for r in eligible),'Eligible:',len(eligible),'Excluded:',len(rows)-len(eligible))
print('In-domain smoke check only. Results:',path)
