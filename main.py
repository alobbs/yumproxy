# Copyright (c) 2013 - Alvaro Lopez Ortega <alvaro@alobbs.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Six Apart Ltd. nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import re
import os
import logging

from twisted.web.client import getPage
from twisted.web import static, proxy, server
from twisted.protocols.basic import LineReceiver
from twisted.internet import protocol, reactor, endpoints, defer

# Defaults
DOMAINS = {
    'fedora': {'domain': 'dl.fedoraproject.org',      'prefix': '/pub'},
    'centos': {'domain': 'msync.centos.org',          'prefix': ''},
    'redhat': {'domain': 'download.devel.redhat.com', 'prefix': ''},
}

# Constants
CACHE_DIR      = '/var/cache/yumproxy'
CACHEABLE_EXTS = ('.rpm', '.img', '.sqlite.bz2', '.xml', '.xml.gz', '.qcow2', '.raw.xz', '.iso', 'filelist.gz', 'vmlinuz')
CRLF           = "\r\n"

class CacheProtocol (protocol.Protocol):
    def on_error(self, failure):
        ret = 'HTTP/1.0 ' + failure.value.status + ' ' + failure.value.message + CRLF + CRLF + failure.value.response
        self.transport.write(ret)
        self.transport.loseConnection()

    def dataReceived(self, data):
        # Read the URL
        tmp = re.findall (r'(GET|HEAD) (.+?) ', data.split('\n')[0])
        if not tmp:
            logging.error ("Couldn't parse request: "+data)
            return

        url = tmp[0][1]
        logging.info ("Received request: %s" %(url))

        # In the cache?
        self.local_fp = os.path.join (CACHE_DIR, url[1:])

        if os.path.exists (self.local_fp) and \
           os.path.isfile (self.local_fp) and \
           self._get_should_cache (self.local_fp):

            logging.info ("HIT: %s" %(self.local_fp))
            with open(self.local_fp, 'r') as f:
                while True:
                    block = f.read(2**21)
                    if not block:
                        break
                    self.transport.write(block)
                return self.transport.loseConnection()

        # Parse
        top_dir = url.split('/')[1]
        if not top_dir in DOMAINS:
            ret =  self._get_top_level_content()
            self.transport.write(ret)
            return self.transport.loseConnection()

        domain_info = DOMAINS[top_dir]
        uri = "http://" + domain_info['domain'] + domain_info['prefix'] + url
        logging.info ("MISS: %s" %(uri))

        # Sub-request
        deferredData = getPage(uri)
        deferredData.addCallback(self.sendAndClose)
        deferredData.addErrback(self.on_error)

    def _get_top_level_content (self):
        return str(DOMAINS)

    def _get_should_cache (self, fp):
        for txt in CACHEABLE_EXTS:
            if txt in fp:
                return True

    def sendAndClose(self, data):
        # Header?
        data = 'HTTP/1.0 200 OK' + CRLF + CRLF + data

        # File cache
        if not os.path.exists (self.local_fp) and \
           self._get_should_cache (self.local_fp):
            dirname = os.path.dirname (self.local_fp)
            if not os.path.exists(dirname):
                os.makedirs (dirname)

            with open(self.local_fp, 'w+b') as f:
                f.write (data)
                logging.info ("STORED: %s" %(self.local_fp))

        # Transfer it to the client
        self.transport.write(data)
        self.transport.loseConnection()


class CacheFactory(protocol.ServerFactory):
    protocol = CacheProtocol

def main():
    endpoints.serverFromString(reactor, "tcp:8080").listen(CacheFactory())
    reactor.run()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
