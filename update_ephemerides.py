#!/usr/bin/env python3
"""Fetch JPL Horizons geocentric apparent RA/Dec; run in GitHub Actions, not browser."""
import json, urllib.parse, urllib.request, datetime as dt, re, pathlib, sys, time
UTC=dt.timezone.utc
now=dt.datetime.now(UTC).replace(minute=0,second=0,microsecond=0)
start=now-dt.timedelta(days=2)
end=now+dt.timedelta(days=32)
objects={'3I/ATLAS':'3I;','161P/Hartley-IRAS':'90001108','(523) Ada':'523;'}
result={'generated_utc':now.isoformat().replace('+00:00','Z'),'source':'NASA JPL Horizons; observer center Earth 500@399; QUANTITIES=2; hourly samples','objects':{},'errors':{}}
for name,command in objects.items():
    params={'format':'json','COMMAND':command,'OBJ_DATA':'NO','MAKE_EPHEM':'YES','EPHEM_TYPE':'OBSERVER','CENTER':'500@399','START_TIME':start.strftime('%Y-%m-%d %H:%M'),'STOP_TIME':end.strftime('%Y-%m-%d %H:%M'),'STEP_SIZE':'60m','QUANTITIES':'2','CSV_FORMAT':'YES','ANG_FORMAT':'DEG','EXTRA_PREC':'YES'}
    url='https://ssd.jpl.nasa.gov/api/horizons.api?'+urllib.parse.urlencode(params)
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'HeavenOnEarth-Ephemeris/1.7'})
        with urllib.request.urlopen(req,timeout=90) as r: payload=json.load(r)
        body=payload.get('result','')
        if '$$SOE' not in body: raise ValueError((payload.get('error') or body[-450:])[:450])
        block=body.split('$$SOE',1)[1].split('$$EOE',1)[0]
        rows=[]
        for line in block.splitlines():
            if ',' not in line: continue
            cols=[v.strip() for v in line.split(',')]
            # Horizons CSV QUANTITIES=2: calendar date, JD, optional flags, RA(deg), DEC(deg).
            # Parse date explicitly, then the final RA/DEC pair. Reject ambiguous rows.
            date_text=cols[0].replace('A.D. ','').strip()
            match=re.search(r'(\d{4})-([A-Za-z]{3})-(\d{2})\s+(\d{2}):(\d{2})',date_text)
            if not match:continue
            d=dt.datetime.strptime(match.group(0),'%Y-%b-%d %H:%M').replace(tzinfo=UTC)
            nums=[]
            for c in cols[2:]:
                try:nums.append(float(c))
                except ValueError:pass
            if len(nums)!=2:raise ValueError('Unexpected Horizons CSV fields; refusing ambiguous RA/DEC: '+line[:180])
            ra,dec=nums
            if not(0<=ra<360 and -90<=dec<=90):raise ValueError('RA/DEC out of range')
            rows.append([d.isoformat().replace('+00:00','Z'),round(ra,9),round(dec,9)])
        if len(rows)<20:raise ValueError('Too few parsed samples: '+str(len(rows)))
        result['objects'][name]=rows
        print(name,len(rows),'samples')
    except Exception as exc:
        result['errors'][name]=str(exc)
        print('ERROR',name,exc,file=sys.stderr)
    time.sleep(1)
if not result['objects']:
    raise SystemExit('No valid ephemerides. Keeping previous feed unchanged.')
pathlib.Path('ephemerides.json').write_text(json.dumps(result,separators=(',',':'))+'\n',encoding='utf-8')
