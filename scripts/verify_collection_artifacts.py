#!/usr/bin/env python3
"""Download and verify the complete pinned community.zabbix dependency lock."""
import argparse, hashlib, json, pathlib, subprocess, tarfile
EXPECTED = {
 'ansible-netcommon-8.4.0.tar.gz':'fafb603557bd4bb39aa40f56f3c3757d4a14d78259a57161c8f99db7fc81f33f',
 'ansible-posix-2.1.0.tar.gz':'5ff232cf69492a991f2a0990dbb23ef25a600b7e9209de6e33377a6ff08a8a29',
 'ansible-utils-6.0.1.tar.gz':'4fdd52d387fb4459ca5b80ce8b428f7a7173e40ad4106f24d7d74a8cd5aa04e9',
 'ansible-windows-3.3.0.tar.gz':'1d5793991e342dcbbcd8377e62e3f8443d39c3e625272118dae895ed43f5539c',
 'community-general-12.4.0.tar.gz':'c26b6f4b2d964bfe0b8c9eec53962324f3ed77777d915db5791d802a3fed247a',
 'community-mysql-4.1.0.tar.gz':'cc08dc63685ccc0fb4df0a3222cb14d59168941ca5215459805fd18149350643',
 'community-postgresql-4.2.0.tar.gz':'1507b58bb3ff391ed7d847fc3f2985be15667761621899d0d7bbf92aee66e30a',
 'community-windows-3.1.0.tar.gz':'9c3f950623e2d9777fc3167a0f893469be58620c4b8b9ef9e7556e5ccb28439a',
 'community-zabbix-4.3.0.tar.gz':'d30bbf022bc32bae89771f8d3611b31d9a524f5d384ff600067e7d0ba9480a5a'}
def main():
 p=argparse.ArgumentParser(); p.add_argument('scratch',type=pathlib.Path); a=p.parse_args(); a.scratch.mkdir(parents=True,exist_ok=True)
 subprocess.run(['ansible-galaxy','collection','download','-r','requirements.yml','-p',str(a.scratch),'--no-deps'],check=True)
 found={x.name for x in a.scratch.glob('*.tar.gz')}; assert found==set(EXPECTED),(found,set(EXPECTED))
 names=set()
 for n,h in EXPECTED.items():
  f=a.scratch/n; assert hashlib.sha256(f.read_bytes()).hexdigest()==h,n
  with tarfile.open(f) as t: info=json.load(t.extractfile('MANIFEST.json'))['collection_info']
  names.add(info['namespace']+'.'+info['name']); print('verified',n,h)
 with tarfile.open(a.scratch/'community-zabbix-4.3.0.tar.gz') as t: deps=json.load(t.extractfile('MANIFEST.json'))['collection_info']['dependencies']
 assert set(deps)<=names,('dependency graph not closed',set(deps)-names)
 print('verified complete dependency closure')
if __name__=='__main__': main()
