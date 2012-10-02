#!/bin/bash
export AVG_DEPLOY=1
while [ true ]; do
    ./appChooser.py >> appChooser.log 2>&1
    sleep 3
done
