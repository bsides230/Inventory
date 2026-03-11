#!/bin/bash
python3 server.py > server.log 2>&1 &
echo $! > server.pid
