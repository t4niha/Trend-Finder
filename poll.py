import os, time, httpx, re
from xpoz_scraper import call_mcp
key=os.getenv('XPOZ_API_KEY','K3A5RTRGPpKcRa4sop6Hlw0sR6Fze1aCflegTHTcCoTLEYnNxGQztb5BWaayG1ZJgj1qcHf')
client=httpx.Client(headers={'Authorization':f'Bearer {key}','Host':'mcp.xpoz.ai','Content-Type':'application/json','Accept':'application/json, text/event-stream'}, transport=httpx.HTTPTransport(retries=1, verify=False), timeout=30)
start=call_mcp(client,'getTwitterPostsByKeywords',{'query':'Winter Olympics 2026 Milano','limit':200,'responseType':'paging'})
op=None
export_id=None
for t in start:
    for line in t.splitlines():
        if line.lower().startswith('operationid:'):
            op=line.split(':',1)[1].strip()
        if 'dataDumpExportOperationId' in line:
            print('export line', line)
print('op',op)
for i in range(12):
    texts=call_mcp(client,'checkOperationStatus',{'operationId':op})
    status='?'
    url=None
    for b in texts:
        for line in b.splitlines():
            if line.lower().startswith('status:'): status=line.split(':',1)[1].strip().lower()
            if 'dataDumpExportOperationId' in line:
                parts=line.split(':',1)
                if len(parts)>1: export_id=parts[1].strip().strip('"')
            m=re.search(r'https?://\S+', line)
            if m: url=m.group(0)
    print(f'poll {i} status {status} export {export_id} url {bool(url)}')
    if url:
        print('sample url', url[:120])
        break
    time.sleep(5)
