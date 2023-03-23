import subprocess


def notify(title: str, msg: str):
    subprocess.Popen(["dunstify", title, msg])
