#!/usr/bin/env python3
"""Local HTTPS tests for production TLS policy and Android PEM root loader.
No live accounts/services are touched; device trust-store paths are NOT TESTED.
"""
# GeneralsX @bugfix Codex 07/10/2026 Valid trust, bad trust, hostname and downgrade regressions.
import http.server, os, pathlib, ssl, subprocess, tempfile, threading
ROOT=pathlib.Path(__file__).resolve().parents[2]
HEADER=ROOT/'GeneralsMD/Code/GameEngine/Include/GameNetwork/GeneralsOnline/HTTP/OnlineTLS.h'
def run(cmd):subprocess.run(list(map(str,cmd)),check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/redirect':
            self.send_response(302);self.send_header('Location','http://localhost:1/blocked');self.send_header('Content-Length','0');self.end_headers()
        else:
            self.send_response(200);self.send_header('Content-Length','13');self.end_headers();self.wfile.write(b'valid-service')
    def log_message(self,*args):pass

def main():
 with tempfile.TemporaryDirectory(prefix='gx-tls-') as temporary:
    work=pathlib.Path(temporary)
    for name in ('root','other'):
        run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',work/(name+'.key'),'-out',work/(name+'.pem'),'-days','1','-subj','/CN='+name])
    run(['openssl','req','-newkey','rsa:2048','-nodes','-keyout',work/'server.key','-out',work/'server.csr','-subj','/CN=localhost'])
    (work/'server.ext').write_text('subjectAltName=DNS:localhost\nextendedKeyUsage=serverAuth\n')
    run(['openssl','x509','-req','-in',work/'server.csr','-CA',work/'root.pem','-CAkey',work/'root.key','-CAcreateserial','-out',work/'server.pem','-days','1','-extfile',work/'server.ext'])
    client=work/'client.cpp'
    client.write_text('#define GX_TEST_ANDROID_TLS\n#include "'+str(HEADER)+'"\n'+r'''
#include <cstdio>
size_t discard(char*,size_t size,size_t count,void*){return size*count;}
CURLcode localSystemRoots(CURL*,void*context,void*directory){return GXLoadSystemCertificateDirectory(SSL_CTX_get_cert_store(static_cast<SSL_CTX*>(context)),static_cast<const char*>(directory))?CURLE_OK:CURLE_SSL_CACERT_BADFILE;}
int main(int argc,char**argv){if(argc!=3)return 2;curl_global_init(CURL_GLOBAL_DEFAULT);CURL*c=curl_easy_init();GXConfigureOnlineTLS(c,false);curl_easy_setopt(c,CURLOPT_URL,argv[1]);curl_easy_setopt(c,CURLOPT_SSL_CTX_FUNCTION,localSystemRoots);curl_easy_setopt(c,CURLOPT_SSL_CTX_DATA,argv[2]);curl_easy_setopt(c,CURLOPT_PROXY,"");curl_easy_setopt(c,CURLOPT_TIMEOUT,5L);curl_easy_setopt(c,CURLOPT_FOLLOWLOCATION,1L);curl_easy_setopt(c,CURLOPT_WRITEFUNCTION,discard);CURLcode result=curl_easy_perform(c);curl_easy_cleanup(c);curl_global_cleanup();return static_cast<int>(result);}
''')
    flags=subprocess.check_output(['pkg-config','--cflags','--libs','libcurl','openssl'],text=True).split()
    run([os.environ.get('CXX','c++'),'-std=c++17','-Wall','-Wextra','-Werror',client,'-o',work/'client',*flags])
    for root_name in ('root','other'):
        certificate_dir=work/(root_name+'-certs');certificate_dir.mkdir();(certificate_dir/'arbitrary-old-hash.0').write_bytes((work/(root_name+'.pem')).read_bytes())
    roots=work/'android-roots';roots.mkdir();(roots/'arbitrary-old-hash.0').write_bytes((work/'root.pem').read_bytes());(roots/'not-a-certificate').write_text('ignored')
    loader=work/'loader.cpp';loader.write_text('#define GX_TEST_ANDROID_TLS\n#include "'+str(HEADER)+'"\n'+r'''
#include <cassert>
int main(int argc,char**argv){assert(argc==2);X509_STORE*s=X509_STORE_new();assert(s);assert(GXLoadSystemCertificateDirectory(s,argv[1])==1);assert(GXLoadSystemCertificateDirectory(s,"/missing/gx-ca-directory")==0);assert(GXAndroidSystemTrust(nullptr,nullptr,nullptr)!=CURLE_OK);X509_STORE_free(s);}
''')
    run([os.environ.get('CXX','c++'),'-std=c++17','-Wall','-Wextra','-Werror',loader,'-o',work/'loader',*flags]);run([work/'loader',roots]);print('PASS: Android PEM roots with arbitrary hash filenames; missing roots/null context fail closed')
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(work/'server.pem',work/'server.key');server.socket=context.wrap_socket(server.socket,server_side=True)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();port=server.server_address[1]
    try:
        for label,url,ca,expected in [
            ('valid service','https://localhost:'+str(port)+'/','root-certs',0),
            ('untrusted certificate','https://localhost:'+str(port)+'/','other-certs',60),
            ('hostname mismatch','https://127.0.0.1:'+str(port)+'/','root-certs',60),
            ('HTTPS downgrade redirect','https://localhost:'+str(port)+'/redirect','root-certs',1),
            ('plain HTTP','http://localhost:'+str(port)+'/','root-certs',1),
        ]:
            result=subprocess.run([str(work/'client'),url,str(work/ca)],capture_output=True,text=True)
            assert result.returncode==expected,(label,result.returncode,result.stderr)
            print('PASS:',label)
    finally:server.shutdown();server.server_close();thread.join()
    # Confirm both actual call sites use the policy rather than overriding its verification.
    for path,marker in [('GeneralsMD/Code/GameEngine/Source/GameNetwork/GeneralsOnline/HTTP/HTTPRequest.cpp','GXConfigureOnlineTLS(m_pCURL, false)'),('GeneralsMD/Code/GameEngine/Source/GameNetwork/GeneralsOnline/OnlineServices_RoomsInterface.cpp','GXConfigureOnlineTLS(m_pCurlWS, true)')]:
        source=(ROOT/path).read_text();assert marker in source and 'CURLOPT_SSL_VERIFYPEER, 0' not in source and 'CURLOPT_SSL_VERIFYHOST, 0' not in source
    print('PASS: production HTTP/WebSocket call sites enforce verified TLS')
if __name__=='__main__':main()
