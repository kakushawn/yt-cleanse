import sys
import re


for line in sys.stdin:
    line = line.strip("\n")
    line = re.sub(r'([0-9]+)', r'▁\1▁', line)
    line = re.sub(r'([A-Za-z\']+)', r'▁\1▁', line)
    line = re.sub(r' +', '', line)
    line = re.sub(r'▁+', '▁', line)
    line = re.sub(r'([^A-Za-z0-9\']+)(▁)', r'\1', line)
    line = re.sub(r'(▁)([^A-Za-z0-9]+)', r'\2', line)
    print(line)