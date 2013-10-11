#!/usr/bin/env python

"""
Publish the currently active slides to Redis.
"""

import db
import redis
import time
import sys


if len(sys.argv) > 1 and sys.argv[1] == "--test":
    test = True
else:
    test = False

r = redis.Redis(port=6379 if not test else 28692)
d = db.Database(test=test)

while True:
    active = d.get_state(state="active")
    if not active:
        print("No active items, sleeping for 5 seconds")
        r.publish("osmo", "__empty__")
        time.sleep(5)
        continue

    for name, slide in active:
        print("Publishing %s, waiting %d seconds" % (name, slide["duration"]))
        r.publish("osmo", name)
        time.sleep(slide["duration"])
