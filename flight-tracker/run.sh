#!/usr/bin/with-contenv bashio
# shellcheck shell=bash

cd /app || exit 1
exec python -u run.py
