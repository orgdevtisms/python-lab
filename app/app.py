import datetime
import os
import platform
import socket

import psutil
from flask import Flask, jsonify, render_template

app = Flask(__name__)

APP_NAME = os.getenv("APP_NAME", "config-viewer")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
SENSITIVE = ("KEY", "SECRET", "TOKEN", "PASS", "PWD", "CREDENTIAL")


def host_os():
    """Nome do SO do host (monte /etc/os-release em /host/os-release)."""
    try:
        with open("/host/os-release") as f:
            info = dict(l.strip().split("=", 1) for l in f if "=" in l)
        return info.get("PRETTY_NAME", "").strip('"') or platform.system()
    except OSError:
        return f"{platform.system()} {platform.release()}"


def gb(n):
    return round(n / 1024**3, 2)


def env_vars():
    """Variáveis de ambiente, mascarando as sensíveis."""
    out = {}
    for k, v in sorted(os.environ.items()):
        out[k] = "********" if any(s in k.upper() for s in SENSITIVE) else v
    return out


def collect():
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    ifaces = []
    for name, addrs in psutil.net_if_addrs().items():
        ips = [a.address for a in addrs if a.family == socket.AF_INET]
        if ips:
            ifaces.append({"name": name, "ipv4": ", ".join(ips)})
    boot = datetime.datetime.fromtimestamp(psutil.boot_time())
    return {
        "app": {"nome": APP_NAME, "versao": APP_VERSION},
        "sistema": {
            "hostname": socket.gethostname(),
            "so": host_os(),
            "arquitetura": platform.machine(),
            "python": platform.python_version(),
            "boot": boot.strftime("%Y-%m-%d %H:%M:%S"),
            "agora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "cpu": {
            "cores_logicos": psutil.cpu_count(logical=True),
            "uso_percent": psutil.cpu_percent(interval=0.2),
        },
        "memoria": {
            "total_gb": gb(vm.total),
            "usada_gb": gb(vm.used),
            "uso_percent": vm.percent,
        },
        "disco": {
            "total_gb": gb(disk.total),
            "usado_gb": gb(disk.used),
            "uso_percent": disk.percent,
        },
        "rede": ifaces,
        "env": env_vars(),
    }


@app.route("/")
def index():
    return render_template("index.html", data=collect())


@app.route("/api/config")
def api_config():
    return jsonify(collect())


@app.route("/health")
def health():
    return jsonify(status="ok", app=APP_NAME, versao=APP_VERSION)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=False)
