YUM Proxy
=========

yumproxy is just a tiny, and in many ways oversimplified, proxy cache for YUM repositories.

It's just me scratching an itch. It was most likely faster to write this script than to learn to configure an actual proxy cache server properly.

## How to use it
Execute it: `python main.py` and then point yum to you new YUM server at `http://localhost:8080/fedora`

There are also other top directories available by default:

* `/fedora`: Fedora repository
* `/centos`: CentOS repository
* `/redhat`: Red Hat's engineering repository

Enjoy it,  
Alvaro