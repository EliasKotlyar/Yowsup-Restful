# Yowsup-Restful


This Project provides a REST-Api for the Yowsup2 Interface. You can Send/Receive Whatsapp-Messages with it.


Installation(on Ubuntu):
sudo apt-get install pip3 python3-dev
pip3 install git+https://github.com/tgalal/yowsup@v2.3.84

Configuration:
Use yowsup-cli to register a Number.

Run like:

    python3 run.py <user> <password>

Usage:
You will get a Web Interface on port 5000. This Interface can be used to interact with Whatsapp

http://127.0.0.1:5000/postMessage?msg=Test&number=XXXXXX
http://127.0.0.1:5000/getMessage


