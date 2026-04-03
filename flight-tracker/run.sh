#!/usr/bin/with-contenv bashio
# shellcheck shell=bash

cd /app || exit 1
exec python3 -u run.py
