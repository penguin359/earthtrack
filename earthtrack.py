#!/usr/bin/env python3

import os
import socket

def sendcommand(msg, host, service):
    # Lookup port by service/protocol (predict/udp)
    # Lookup hostname (localhost)
    # Lookup protocol by name (udp)
    protocol = 'udp'
    port = socket.getservbyname(service, protocol)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(1)
        sock.sendto(bytes(msg, 'utf-8'), (host, port))
        resp, server = sock.recvfrom(1024)
    return resp.decode('utf-8')

def convertlong(longitude):
    if longitude < 180.0:
        longitude = -longitude
    else:
        longitude = 360. - longitude
    return longitude

# earthtrack is xearth
# earthtrack2 is xplanet
#
# -h hostname (defaults to localhost)
# -c sat2track
# -C sat2track (zoom)
# -u updateinterval (5 <= x <= 120 or 20)
# -x extracommands
#
# sprintf(markerfile,"%s/.markerfile",getenv("HOME"));
# sprintf(greatarcfile,"%s/.greatarcfile",getenv("HOME"));
# sprintf(configfile,"%s/.xplanetconfig",getenv("HOME"));
#
# markerfile used by both
# greatarcfile and configfile used by xplanet

# Constants
R0 = 6378.16
vis2color = {
    'D': 'color=white',
    'N': 'color=blue',
    'V': 'color=yellow',
}

xplanet = True          # xearth if False
hostname = 'localhost'
sat2track = ''
zoom = False
updateinterval = 20     # 5 <= x <= 120
extra = ''

circledrawn = False

markerfile   = os.environ['HOME'] + '/.markerfile2'
greatarcfile = os.environ['HOME'] + '/.greatarcfile'
configfile   = os.environ['HOME'] + '/.xplanetconfig2'

fontfile = '/usr/share/xplanet/fonts/FreeMonoBold.ttf'
globalconfigfile = '/usr/share/xplanet/config/default'

text = """\
## "earthtrack2" parameters.  Please edit
## earthtrack.py to modify these parameters!

marker_file=""" + markerfile + """
arc_file=""" + greatarcfile + """
marker_font=""" + fontfile + """

## Your """" + globalconfigfile + """" configuration file follows:
"""

with open(configfile, 'w') as f:
    f.write(text)
    with open(globalconfigfile) as i:
        for line in i:
            f.write(line)

callsign, qthlat, qthlong, rest = \
    sendcommand("GET_QTH", hostname, 'predict').split('\n', 3)
qthlat = float(qthlat)
qthlong = convertlong(float(qthlong))

mapcenterlat = qthlat
mapcenterlong = qthlong

#print(sendcommand("GET_LIST", hostname, 'predict'))
sats = sendcommand("GET_LIST", hostname, 'predict').split('\n')
sats = [ sat for sat in sats if sat ] # Remove blank entries
# XXX Error if list empty

#print('>>>>')
#print(sats)
#print('>>>>')
with open(markerfile, 'w') as marker:
    with open(greatarcfile, 'w') as greatarc:
        print('%8.3f %8.3f "%s"' % (qthlat, qthlong, callsign), file=marker)
        for sat in sats:
            #print(sendcommand("GET_SAT " + sat, hostname, 'predict'))
            satinfo = sendcommand("GET_SAT " + sat, hostname, 'predict')
            name, slong, slat, az, el, next_event_time, footprint, srange, altitude, velocity, orbitnum, visibility, rest = satinfo.split('\n', 12)
            print('Name: ' + name)
            print('Slong: ' + slong)
            print('Slat: ' + slat)
            print('Az: ' + az)
            print('El: ' + el)
            print('Next_event_time: ' + next_event_time)
            print('Footprint: ' + footprint)
            print('Srange: ' + srange)
            print('Altitude: ' + altitude)
            print('Velocity: ' + velocity)
            print('Orbitnum: ' + orbitnum)
            print('Visibility: ' + visibility)
            print('Rest: ' + rest)

            slat = float(slat)
            slong = convertlong(float(slong))
            footprint = float(footprint)
            srange = float(srange)

            if name == sat2track:
                mapcenterlat = slat
                mapcenterlong = slong
                #rangecircle(slat, slong, footprint, visibility)
                circledrawn = True
                radius = 50
                if zoom:
                    radius = int(100.0*(R0/footprint))
                    if radius < 50:
                        radius = 50

                if srange > 0:
                    color = ''
                    if xplanet and visibility in vis2color:
                        color = vis2color[visibility]
                    print('%8.3f %8.3f "%s" %s' % (slat, slong, name, color), file=marker)

                # get time
                cmd = 'xearth -proj orth -grid -night 30 -bigstars 40 -markerfile %s -pos "fixed %f %f" -once %s' % (markerfile, mapcenterlat, mapcenterlong, extra)
                if xplanet:
                    if circledrawn:
                        cmd = 'xplanet -config "%s" -projection orth -latitude %f -longitude %f -radius %d -num_times 1 -starfreq 0.005 %s' % (configfile, mapcenterlat, mapcenterlong, radius, extra)
                    else:
                        cmd = 'xplanet -config "%s" -projection orth -latitude %f -longitude %f -num_times 1 -starfreq 0.005 %s' % (configfile, mapcenterlat, mapcenterlong, extra)

os.remove(markerfile)
os.remove(greatarcfile)
os.remove(configfile)
