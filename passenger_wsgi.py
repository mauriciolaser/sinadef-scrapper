# -*- coding: utf-8 -*-
"""Minimal WSGI app required by cPanel Setup Python App.
This project runs via cron; this endpoint is only for app boot sanity.
"""

def application(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/plain; charset=utf-8')]
    start_response(status, headers)
    return [b'SINADEF job app is up. Use cron to run script.py.\n']
