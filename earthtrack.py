#!/usr/bin/env python3
# EARTHTRACK:  A Real-Time Satellite Tracking Display Client for PREDICT
#   Original concept by Wade Hampton.  This implimentation was written 
#   by John A. Magliacane, KD2BD in November 2000.  The -x switch code 
#          was contributed by Tom Busch, WB8WOR in October 2001.       

# TODO Add comments/license

import os
import socket
import time

def sendcommand(msg, host, service):
    # Lookup port by service/protocol (predict/udp)
    # Lookup hostname (localhost)
    # Lookup protocol by name (udp)
    protocol = 'udp'
    try:
        port = socket.getservbyname(service, protocol)
    except IOError as ex:
        try:
            port = int(service)
        except ValueError:
            raise ex
    addr = socket.gethostbyname(host)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(1)
        sock.sendto(bytes(msg, 'utf-8'), (host, port))
        resp, server = sock.recvfrom(1024)
    return resp.decode('utf-8')

# This function converts west longitudes (0-360 degrees)
# to a value between -180 and 180 degrees, as required
# by xearth and xplanet.
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


# This function generates a character string based on the
# visibility information returned by PREDICT.  It is used
# to set the colors of the markers and range circles
# plotted by xearth and xplanet.
vis2color = {
    'D': 'color=white # In sunlight',
    'N': 'color=blue # In darkness',
    'V': 'color=yellow # Optically visible',
}

# TODO Set xplanet if arg0 is earthtrack2
# hostname set by -h hostname || ''
# sat2track set by -c/-C || ''
# zoom set by -C || False
# updateinterval set by -u || 0
# extra set by -x || ''
xplanet = True          # xearth if False
hostname = 'localhost'
if not hostname:
    hostname = 'localhost'
sat2track = ''
zoom = False
updateinterval = 20
if updateinterval < 5 or updateinterval > 120:
    updateinterval = 20
extra = ''

circledrawn = False

markerfile   = os.path.join(os.environ['HOME'], '.markerfile2')
greatarcfile = os.path.join(os.environ['HOME'], '.greatarcfile')
configfile   = os.path.join(os.environ['HOME'], '.xplanetconfig2')

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

try:
    while True:
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

        # XXX Loop until error
        with open(markerfile, 'w') as marker, \
             open(greatarcfile, 'w') as greatarc:
                print('%8.3f %8.3f "%s"' % (qthlat, qthlong, callsign), file=marker)
                for sat in sats:
                    satinfo = sendcommand("GET_SAT " + sat, hostname, 'predict')
                    #print(satinfo)
                    # XXX Error if empty response
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
                    el = float(el)
                    next_event_time = int(next_event_time)
                    footprint = float(footprint)
                    srange = float(srange)

                    radius = 50
                    if sat == sat2track and srange > 0:
                        mapcenterlat = slat
                        mapcenterlong = slong
                        # XXX rangecircle(slat, slong, footprint, visibility)
                        circledrawn = True
                        if zoom:
                            radius = int(100.0*(R0/footprint))
                            if radius < 50:
                                radius = 50

                    if srange > 0:
                        color = ''
                        if xplanet and visibility in vis2color:
                            color = vis2color[visibility]
                        print('%8.3f %8.3f "%s" %s' % (slat, slong, name, color), file=marker)

                        # Get current time from PREDICT server
                        current_time = int(sendcommand("GET_TIME", hostname, 'predict'))
                        # Draw range circle if satellite is in range,
                        # or will be in range within 5 minutes.
                        if xplanet and not zoom and (el >= 0 or (next_event_time - current_time) < 300):
                            # XXX rangecircle(slat, slong, footprint, visibility)
                            circledrawn = True
        # XXX Do this only if no error
        starttime = int(time.time())
        cmd = 'xearth -proj orth -grid -night 30 -bigstars 40 -markerfile %s -pos "fixed %f %f" -once %s' % (markerfile, mapcenterlat, mapcenterlong, extra)
        if xplanet:
            if circledrawn:
                cmd = 'xplanet -config "%s" -projection orth -latitude %f -longitude %f -radius %d -num_times 1 -starfreq 0.005 %s' % (configfile, mapcenterlat, mapcenterlong, radius, extra)
            else:
                cmd = 'xplanet -config "%s" -projection orth -latitude %f -longitude %f -num_times 1 -starfreq 0.005 %s' % (configfile, mapcenterlat, mapcenterlong, extra)
        print('Running %s' % (cmd))
        os.system(cmd)
        print('Done.')
        endtime = int(time.time())
        sleeptime = updateinterval - (endtime-starttime)
        if sleeptime > 0:
            time.sleep(sleeptime)
finally:
    # XXX Only remove on error
    os.remove(markerfile)
    if xplanet:
        os.remove(greatarcfile)
    os.remove(configfile)
