import urllib.request
req=urllib.request.Request('https://api.render.com/v1/services/srv-daem9k1t0dsc73ar02dg/deploys', data=b'{"clearCache": "do_not_clear"}', headers={'Authorization': 'Bearer rnd_coICmwUZglrHzzHC84glOBZTgl1U', 'Content-Type': 'application/json', 'Accept': 'application/json'}, method='POST')
try:
    urllib.request.urlopen(req)
    print('Deployed!')
except Exception as e:
    print('Err:', e)
