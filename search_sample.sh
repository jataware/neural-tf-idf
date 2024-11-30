#!/usr/bin/env bash
# Requires jq to be installed in the system
python search_populated_es_embeddings.py | tail -n 1 | jq
