import urllib.request
import json
import urllib.error

req = urllib.request.Request(
    'http://localhost:8000/api/design',
    data=json.dumps({'query':'scara robot'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    res = urllib.request.urlopen(req)
    print('STATUS:', res.getcode())
    print('BODY:', res.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print('STATUS:', e.code)
    print('BODY:', e.read().decode('utf-8'))
except Exception as e:
    print('ERROR:', str(e))
