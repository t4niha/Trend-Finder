import httpx, os, time, re, json
from xpoz_scraper import call_mcp
export_op_id = "op_datadump_1771925116157_bb5418"
key=os.getenv('XPOZ_API_KEY','K3A5RTRGPpKcRa4sop6Hlw0sR6Fze1aCflegTHTcCoTLEYnNxGQztb5BWaayG1ZJgj1qcHf')
client=httpx.Client(headers={'Authorization':f'Bearer {key}','Host':'mcp.xpoz.ai','Content-Type':'application/json','Accept':'application/json, text/event-stream'}, transport=httpx.HTTPTransport(retries=1, verify=False), timeout=30)
texts=call_mcp(client,'checkOperationStatus',{'operationId':export_op_id})
print('blocks',len(texts))
for t in texts:
    print(t[:500])
