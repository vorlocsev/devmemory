"""Independent SDK interoperability gate; dependencies are CI-only."""
import asyncio, json, ssl, subprocess, sys, tempfile, threading
from pathlib import Path
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Store
from mcp_http import make_http_server
from mcp_managed import start_managed

TOKEN='sdk_fixture_'+'C'*40
READ_NAMES={'list_projects','search_memory','get_context','get_blockers','get_decisions','get_ci_evidence'}

async def exercise(session,write=False):
    info=await session.initialize()
    assert info.serverInfo.name=='devmemory'
    assert info.protocolVersion in ('2025-11-25','2025-06-18','2025-03-26','2024-11-05')
    tools=await session.list_tools()
    assert {t.name for t in tools.tools}==READ_NAMES|({'add_memory'} if write else set())
    result=await session.call_tool('list_projects',{})
    assert not result.isError
    assert [row['slug'] for row in json.loads(result.content[0].text)['rows']]==['alpha']
    result=await session.call_tool('search_memory',{'project':'alpha','query':'провер'})
    assert not result.isError and len(json.loads(result.content[0].text)['rows'])==1
    result=await session.call_tool('get_context',{'project':'beta'})
    assert result.isError
    if write:
        result=await session.call_tool('add_memory',{'project':'alpha','kind':'decision','title':'SDK decision','body':'Agent-reported fixture'})
        assert not result.isError
        result=await session.call_tool('add_memory',{'project':'alpha','kind':'evidence','title':'Claim','body':'Fixture','status':'verified'})
        assert result.isError
    else:
        result=await session.call_tool('add_memory',{'project':'alpha','kind':'note','title':'Denied','body':'Fixture'})
        assert result.isError

async def http_exercise(url,verify,write=False):
    async with httpx.AsyncClient(headers={'Authorization':'Bearer '+TOKEN},verify=verify,follow_redirects=False,trust_env=False,timeout=10) as client:
        async with streamable_http_client(url,http_client=client) as (read,write_stream,_):
            async with ClientSession(read,write_stream) as session:
                await exercise(session,write)

async def main():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);store=Store(root/'memory.sqlite3')
        for p in ('alpha','beta'): store.add_project({'slug':p,'name':p})
        store.add(dict(project='alpha',kind='note',status='reported',title='Проверка ядра',body='Fixture'))
        script=str(Path(__file__).resolve().parents[1]/'mcp_server.py')
        args=StdioServerParameters(command=sys.executable,args=[script,'--data',tmp,'--project','alpha','--allow-write'])
        async with stdio_client(args) as (read,write):
            async with ClientSession(read,write) as session:
                await exercise(session,True)
        assert store.entries('alpha','SDK decision')[0]['status']=='reported'
        print('PASS: official MCP Python SDK stdio and append boundary',flush=True)
        srv=make_http_server(store,0,TOKEN,['alpha'])
        thread=threading.Thread(target=srv.serve_forever,daemon=True);thread.start()
        try:
            await http_exercise('http://127.0.0.1:'+str(srv.server_port)+'/mcp',True)
        finally:
            srv.shutdown();srv.server_close();thread.join()
        print('PASS: official MCP Python SDK Streamable HTTP',flush=True)
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(root/'mcp.key'),'-out',str(root/'mcp.crt')],check=True,capture_output=True,timeout=20)
        # Bind a free port, then set the exact public authority for this fixture.
        (root/'options.json').write_text(json.dumps({'mcp_enabled':True,'mcp_token':TOKEN,'mcp_projects':'alpha','mcp_host':'localhost:8100'}))
        managed,status=start_managed(store,root,config_dir=root,port=0)
        assert managed and status['state']=='enabled'
        try:
            port=managed.server.server_port
            managed.server.allowed_hosts={'localhost:'+str(port)}
            ctx=ssl.create_default_context(cafile=str(root/'mcp.crt'))
            await http_exercise('https://localhost:'+str(port)+'/mcp',ctx)
        finally: managed.close()
        print('PASS: official MCP Python SDK managed HTTPS with trusted fixture certificate',flush=True)

if __name__=='__main__': asyncio.run(asyncio.wait_for(main(),timeout=90))
