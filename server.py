#!/usr/bin/env python3
"""Simple API server for VPS Monitor PWA"""
import os, json, time, subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

PORT = 8080
BASE = "/opt/data/vpsmonitor/web"

def sh(cmd, timeout=10):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except:
        return 1, "TIMEOUT"

def get_cpu():
    try:
        # Read initial CPU usage
        with open("/sys/fs/cgroup/cpu.stat") as f:
            for line in f:
                p = line.split()
                if p and p[0] == "usage_usec":
                    usage1 = int(p[1])
                    break
        
        # Wait a short time
        import time
        time.sleep(0.1)
        
        # Read again
        with open("/sys/fs/cgroup/cpu.stat") as f:
            for line in f:
                p = line.split()
                if p and p[0] == "usage_usec":
                    usage2 = int(p[1])
                    break
        
        # Calculate delta
        delta_usage = usage2 - usage1
        delta_time = 100000  # 0.1s in microseconds
        
        # Percentage (2 cores)
        pct = (delta_usage / delta_time) * 100 / 2
        return {"pct": min(100, max(0, pct)), "cores": 2}
    except:
        pass
    return {"pct": 0, "cores": 2}

def get_ram():
    try:
        cur = int(open("/sys/fs/cgroup/memory.current").read())
        mx = open("/sys/fs/cgroup/memory.max").read().strip()
        total = int(mx) if mx != "max" else 4096 * 1024 * 1024
        cache = 0
        for line in open("/sys/fs/cgroup/memory.stat"):
            p = line.split()
            if len(p) >= 2 and p[0] in ("inactive_file", "active_file"):
                cache += int(p[1])
        used = max(0, cur - cache)
        return {"total": total, "used": used, "cache": cache, "pct": used / total * 100}
    except:
        return {"total": 0, "used": 0, "cache": 0, "pct": 0}

def get_disk():
    try:
        st = os.statvfs("/")
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - free
        return {"total": total, "used": used, "free": free, "pct": used / total * 100}
    except:
        return {"total": 0, "used": 0, "free": 0, "pct": 0}

def get_net():
    try:
        with open("/proc/net/dev") as f:
            lines = f.readlines()[2:]
            rx = tx = 0
            for line in lines:
                p = line.split(":")
                if len(p) >= 2:
                    f = p[1].split()
                    rx += int(f[0])
                    tx += int(f[8])
            return {"rx_rate": rx / 1024, "tx_rate": tx / 1024}
    except:
        return {"rx_rate": 0, "tx_rate": 0}

def get_services():
    services = {}
    for name, port in [("9Router", 3001), ("Proxy", 3002), ("OpenViking", 1933), ("Dashboard", 9119)]:
        rc, _ = sh(f"curl -s -o /dev/null -w '%{{http_code}}' -m 2 http://127.0.0.1:{port}/")
        services[name] = rc == 0
    for name, proc in [("Tailscale", "tailscaled"), ("Cloudflared", "cloudflared")]:
        rc, _ = sh(f"pgrep -x {proc}")
        services[name] = rc == 0
    return services

def clean_ram():
    killed = 0
    for pattern in ["hermes setup", "hermes dashboard"]:
        rc, out = sh(f"ps -eo pid,comm,args | grep '{pattern}' | grep -v grep | awk '{{print $1}}'")
        for pid in out.splitlines():
            if pid.strip().isdigit():
                try:
                    os.kill(int(pid), 9)
                    killed += 1
                except:
                    pass
    return {"killed": killed}

def clean_storage():
    freed = 0
    for path in ["/opt/data/home/.cache/uv", "/tmp"]:
        if os.path.isdir(path):
            rc, out = sh(f"du -sb {path}")
            if rc == 0:
                freed += int(out.split()[0])
            sh(f"find {path} -type f -mtime +1 -delete 2>/dev/null")
    return {"freed": freed}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE, **kwargs)
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == "/api/cpu":
            self.send_json(get_cpu())
        elif path == "/api/ram":
            self.send_json(get_ram())
        elif path == "/api/disk":
            self.send_json(get_disk())
        elif path == "/api/net":
            self.send_json(get_net())
        elif path == "/api/services":
            self.send_json(get_services())
        elif path == "/api/procs":
            rc, out = sh("ps -eo rss,comm --sort=-rss | head -10")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(out.encode())
        else:
            super().do_GET()
    
    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/clean/ram":
            self.send_json(clean_ram())
        elif path == "/api/clean/storage":
            self.send_json(clean_storage())
        else:
            self.send_error(404)
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

if __name__ == "__main__":
    print(f"🌐 VPS Monitor Web running on http://0.0.0.0:{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
