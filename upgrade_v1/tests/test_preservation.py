"""Compare protected source against hashes taken from the published base commit."""
import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'mega_vector_v1/mega_vector_v1.ino').read_text()
REFERENCE=json.loads((ROOT/'SOURCE_COMPARISON_TOUCH_V2.json').read_text())

def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()

class PreservationTests(unittest.TestCase):
    def test_thirteen_motor_line_corner_servo_functions(self):
        for name,expected in REFERENCE['function_sha256'].items():
            with self.subTest(function=name):
                match=re.search(r'^(?:void|int) '+name+r'\([^;]*?\)\s*\{',SOURCE,re.M)
                self.assertIsNotNone(match)
                index=match.end();depth=1
                while depth:
                    if SOURCE[index]=='{':depth+=1
                    if SOURCE[index]=='}':depth-=1
                    index+=1
                self.assertEqual(digest(SOURCE[match.start():index]),expected)

    def test_complete_line_corner_body_except_approved_entry_threshold(self):
        start=SOURCE.index('void handleLineAndObstacleMode() {')
        end=SOURCE.index('void logCorner(',start)
        body=SOURCE[start:end]
        self.assertEqual(body.count('rangeF.cm <= VM_OBSTACLE_CM'),1)
        self.assertEqual(digest(body.replace('rangeF.cm <= VM_OBSTACLE_CM','rangeF.cm <= 60')),
                         REFERENCE['line_corner_sha256_before_approved_threshold_change'])

    def test_pin_sensor_speed_corner_constants(self):
        prefix=SOURCE[SOURCE.index('// 1. CHAN MOTOR'):SOURCE.index('VmAvoid vectorAvoid;')]
        self.assertEqual(digest(prefix),REFERENCE['pin_constants_prefix_sha256'])

if __name__=='__main__':unittest.main()
