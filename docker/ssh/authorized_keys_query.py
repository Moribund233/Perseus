#!/usr/bin/env python3
"""SSH AuthorizedKeysCommand -- query all SSH public keys from Perseus DB"""
import sys
import psycopg2

# Hardcoded for internal SSH AuthorizedKeysCommand (env not available)
DB = "host=capella-pg dbname=perseus user=perseus password=Perseus_2024!"

def get_all_keys():
    try:
        conn = psycopg2.connect(DB, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT public_key FROM ssh_keys ORDER BY created_at")
        keys = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        return keys
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return []

if __name__ == "__main__":
    for key in get_all_keys():
        print(key)
