#!/usr/bin/python
# poller.py
# http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
# mikeder 2015

import sys
import time
from daemon import Daemon
import os
import platform
import requests
import subprocess
from socket import socket
import psutil

CLIENT_NAME = 'cherrym'

class Data:
  # Functions for gathering data:
  # get conns to :port
  def get_conns(self, port):
    conns = psutil.net_connections
    active = 0
    for conn in conns:
      if conn.laddr[1] == port and status == 'ESTABLISHED':
        active += 1
    return active
  # get climate data from arduino/dht sensor
  def get_climate(self):
    r = requests.get('http://192.168.1.20')
    tC = int(r.json()[u'tempC'])
    tF = int(r.json()[u'tempF'])
    h = int(r.json()[u'humidity'])
    return(tC, tF, h)
  # load averages (1m, 5m, 15m)
  def get_loadavg(self):
    # For more details, "man proc" and "man uptime"  
    if platform.system() == "Linux":
      return open('/proc/loadavg').read().strip().split()[:3]
    else:   
      command = "uptime"
      process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
      os.waitpid(process.pid, 0)
      output = process.stdout.read().replace(',', ' ').strip().split()
      length = len(output)
      return output[length - 3:length]

# Graphite client that gets daemonized
class Client:
  def run(self):
    CARBON_SERVER = 'graphite'
    CARBON_PORT = 2003
    # How often to send message to graphite
    delay = 60 
    data = Data()
    sock = socket()
    try:
      sock.connect( (CARBON_SERVER,CARBON_PORT) )
    except:
      print "Couldn't connect to %(server)s on port %(port)d, is carbon-agent.py running?" % { 'server':CARBON_SERVER, 'port':CARBON_PORT }
      sys.exit(1)
    # While the connection to graphite is open send messages
    while True:
      now = int( time.time() )
      lines = []
      #We're gonna report all three loadavg values
      loadavg = data.get_loadavg()
      lines.append("%s.loadavg_1min %s %d" % (CLIENT_NAME,loadavg[0],now))
      lines.append("%s.loadavg_5min %s %d" % (CLIENT_NAME,loadavg[1],now))
      lines.append("%s.loadavg_15min %s %d" % (CLIENT_NAME,loadavg[2],now))
      #Check for connections to port 8080
      listeners = data.get_conns(8080)
      lines.append("%s.listeners %d %d" % (CLIENT_NAME,listeners,now))
      message = '\n'.join(lines) + '\n' #all lines must end in a newline
      print "sending message\n"
      print '-' * 80
      print message
      print
      sock.sendall(message)
      time.sleep(delay) 

# Daemonize all the things!
class Daemon(Daemon):
  def run(self):
    # Or simply merge your code with MyDaemon.
    client = Client() 
    client.run()

if __name__ == "__main__":
  # Name the pid file something useful
  daemon = Daemon('/tmp/graphite-client.pid')
  if len(sys.argv) == 2:
    # Start daemon
    if 'start' == sys.argv[1]:
      daemon.start()
    # Stop daemon
    elif 'stop' == sys.argv[1]:
      daemon.stop()
    # Restart daemon
    elif 'restart' == sys.argv[1]:
      daemon.restart()
    else:
      print "Unknown command"
      sys.exit(2)
    sys.exit(0)
  else:
    print "usage: %s start|stop|restart" % sys.argv[0]
    sys.exit(2)
