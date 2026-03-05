import time
import re
LOG_FILE = "access.log" # Simulovaný log
def analyze_logs():
print("[*] Monitoring logů spuštěn...")
# Simulované vzory útoků
xss_pattern = re.compile(r"(<script|fetch|document\.cookie)", re.IGNORECASE)
while True:
try:
with open(LOG_FILE, "r") as f:
lines = f.readlines()
for line in lines:
if xss_pattern.search(line):
print(f"[!] ALERT: Detekován pokus o XSS! Log: {line.strip()}")
time.sleep(5)
except FileNotFoundError:
time.sleep(1)
if __name__ == "__main__":
analyze_logs()
