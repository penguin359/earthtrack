#!/usr/bin/env python3
#
# EARTHTRACK:  A Real-Time Satellite Tracking Display Client for PREDICT
#   Original concept by Wade Hampton.  This implimentation was written 
#   by John A. Magliacane, KD2BD in November 2000.  The -x switch code 
#          was contributed by Tom Busch, WB8WOR in October 2001.       
#
#   Invoke earthtrack to run with xearth.
#   Invoke earthtrack2 to run with xplanet version 1.0 or above.
#
#
#  This is based on the C program last modified by KD2BD on 10-Sep-2005.
#  The Python version was developed by Loren M. Lang, KG7GAN
#
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License or any later
# version.
#
# This program is distributed in the hope that it will useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

# TODO Support Python 2

import sys
import os
import socket
import argparse
import time
#import math
from math import pi, cos, sin, acos, asin


# Constants
R0 = 6378.16
deg2rad = 1.74532925199e-02  # TODO replace with Python degrees function


# This function generates a character string based on the
# visibility information returned by PREDICT.  It is used
# to set the colors of the markers and range circles
# plotted by xearth and xplanet.
vis2color = {
    'D': 'color=white # In sunlight',
    'N': 'color=blue # In darkness',
    'V': 'color=yellow # Optically visible',
}


# connectsock:
#   created AF_INET socket
#   looks up port by service/protocol with getservbyname
#   or falls back to int() conversion
#   looks up addr by host with gethostbyname
#   looks up proto by protocol with getprotobyname
#   sets socket type as appropriate
#   socket(PF_INET, type, proto)
#   connect(s, addr, port)
# get_response:
#   read up to 625 bytes
#   ignore EINTR
#   exit on ECONNREFUSED

# This function sends "command" to PREDICT running on
# machine "host", and returns the result of the command
# as a character string.
def send_command(msg, host):
    protocol = 'udp'
    service = 'predict'
    try:
        port = socket.getservbyname(service, protocol)
    except IOError as ex:
        try:
            port = int(service)
        except ValueError:
            raise ex
    addr = socket.gethostbyname(host)
    proto = socket.getprotobyname(protocol)
    if protocol == 'udp':
        type_ = socket.SOCK_DGRAM
    else:
        type_ = socket.SOCK_STREAM
    with socket.socket(socket.AF_INET, type_, proto) as sock:
        sock.settimeout(1)
        sock.sendto(bytes(msg + '\n', 'utf-8'), (host, port))
        resp, server = sock.recvfrom(1024)
    return resp.decode('utf-8')


# This function implements the arccosine function,
# returning a value between 0 and two pi.
def arccos(x, y):
    result = 0.0
    if y > 0:
        result = acos(x/y)
    elif y < 0:
        result = pi + acos(x/y)
    return result


# This function converts west longitudes (0-360 degrees)
# to a value between -180 and 180 degrees, as required
# by xearth and xplanet.
def convertlong(longitude):
    if longitude < 180.0:
        longitude = -longitude
    else:
        longitude = 360. - longitude
    return longitude


# This function generates a sequence of latitude and
# longitude positions used to plot range circles of
# satellites based on the spacecraft's sub-satellite
# latitude, longitude, and footprint.  The visibility
# information is used to set the range circle to an
# appropriate color.  Output is written to ~/.greatarcfile,
# and read and processed by xplanet.
def rangecircle(ssplat, ssplong, footprint, visibility, greatarc):
    ssplat = ssplat * deg2rad
    ssplong = ssplong * deg2rad
    beta = 0.5 * footprint / R0

    for azi in range(360):
        azimuth = deg2rad * azi
        rangelat = asin(sin(ssplat)*cos(beta) + cos(azimuth)*sin(beta)*cos(ssplat))
        num = cos(beta) - sin(ssplat)*sin(rangelat)
        den = cos(ssplat)*cos(rangelat)

        if azi == 0 and beta > pi/2 - ssplat:
            rangelong = ssplong + pi
        elif azi == 180 and beta > pi/2 + ssplat:
            rangelong = ssplong + pi
        elif abs(num/den) > 1.0:
            rangelong = ssplong
        else:
            if 180 - azi >= 0:
                rangelong = ssplong - arccos(num, den)
            else:
                rangelong = ssplong + arccos(num, den)

        # XXX Replace with modulus?
        while rangelong < 0.0:
                rangelong += 2*pi
        while rangelong > 2*pi:
                rangelong -= 2*pi

        # TODO replace with radians function
        rangelat = rangelat/deg2rad
        rangelong = rangelong/deg2rad

        rangelong = convertlong(rangelong)

        # Write range circle data to greatarcfile

        color = ''
        if azi % 2 and visibility in vis2color:
            color = vis2color[visibility] + '\n'
        print('%8.3f %8.3f %s' % (rangelat, rangelong, color), end='', file=greatarc)


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

# TODO Set xplanet if arg0 is earthtrack2
# hostname set by -h hostname || ''
# sat2track set by -c/-C || ''
# zoom set by -C || False
# updateinterval set by -u || 0
# extra set by -x || ''
# TODO Add defaults to output
parser = argparse.ArgumentParser(description='Satellite tracker using PREDICT with xearth/xplanet',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-H', dest='hostname', default='localhost', help='Hostname of PREDICT server')
parser.add_argument('-c', dest='sat2track', help='Satellite to track')
parser.add_argument('-C', dest='sat2trackzoom', help='Satellite to track w/ zoom')
parser.add_argument('-u', dest='updateinterval', type=int, default=20, help='Update interval of background in seconds')
parser.add_argument('-x', dest='extra', default='', help='Extra arguments to pass to xearth/xplanet')
args = parser.parse_args()

xplanet = False
if '2' in sys.argv[0]:
    xplanet = True          # xearth if False
zoom = False
if args.sat2trackzoom:
    args.sat2track = args.sat2trackzoom
    zoom = True
if args.updateinterval < 5 or args.updateinterval > 120:
    args.updateinterval = 20

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
            send_command("GET_QTH", args.hostname).split('\n', 3)
        qthlat = float(qthlat)
        qthlong = convertlong(float(qthlong))

        mapcenterlat = qthlat
        mapcenterlong = qthlong

        sats = send_command("GET_LIST", args.hostname).split('\n')
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
                    satinfo = send_command("GET_SAT " + sat, args.hostname)
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
                    slong = float(slong)
                    el = float(el)
                    next_event_time = int(next_event_time)
                    footprint = float(footprint)
                    srange = float(srange)

                    radius = 50
                    if sat == args.sat2track and srange > 0:
                        mapcenterlat = slat
                        mapcenterlong = convertlong(slong)
                        rangecircle(slat, slong, footprint, visibility, greatarc)
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
                        current_time = int(send_command("GET_TIME", args.hostname))
                        # Draw range circle if satellite is in range,
                        # or will be in range within 5 minutes.
                        if xplanet and not zoom and (el >= 0 or (next_event_time - current_time) < 300):
                            rangecircle(slat, slong, footprint, visibility, greatarc)
                            circledrawn = True
        # XXX Do this only if no error
        starttime = int(time.time())
        cmd = 'xearth -proj orth -grid -night 30 -bigstars 40 -markerfile %s -pos "fixed %f %f" -once %s' % (markerfile, mapcenterlat, mapcenterlong, args.extra)
        if xplanet:
            if circledrawn:
                cmd = 'xplanet -config "%s" -projection orth -latitude %f -longitude %f -radius %d -num_times 1 -starfreq 0.005 %s' % (configfile, mapcenterlat, mapcenterlong, radius, args.extra)
            else:
                cmd = 'xplanet -config "%s" -projection orth -latitude %f -longitude %f -num_times 1 -starfreq 0.005 %s' % (configfile, mapcenterlat, mapcenterlong, args.extra)
        print('Running %s' % (cmd))
        os.system(cmd)
        print('Done.')
        endtime = int(time.time())
        sleeptime = args.updateinterval - (endtime-starttime)
        if sleeptime > 0:
            time.sleep(sleeptime)
finally:
    # XXX Only remove on error
    os.remove(markerfile)
    if xplanet:
        os.remove(greatarcfile)
    os.remove(configfile)
