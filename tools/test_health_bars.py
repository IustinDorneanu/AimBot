"""Offline visual check: python tools/test_health_bars.py [raw_folder]."""
import json
import sys
import time
from pathlib import Path
import cv2
import numpy as np
from visionaim.detection.health_bars import HealthBarDetector


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('datasets/control/images/raw')
    output = folder.parent.parent / 'health-bar-test'
    output.mkdir(parents=True, exist_ok=True)
    detector, tiles, records = HealthBarDetector(), [], []
    for path in sorted(folder.glob('*.png')):
        frame = cv2.imread(str(path))
        if frame is None:
            continue
        start = time.perf_counter()
        markers = detector.detect(frame)
        elapsed = (time.perf_counter()-start)*1000
        records.append({'file': path.name, 'markers': len(markers), 'ms': round(elapsed, 3)})
        for m in markers:
            cv2.rectangle(frame, (round(m.x), round(m.y)),
                          (round(m.x+m.width), round(m.y+m.height)), (0, 255, 0), 2)
        cv2.imwrite(str(output / path.name), frame)
        tile = np.zeros((295, 480, 3), np.uint8)
        tile[:270] = cv2.resize(frame, (480, 270))
        cv2.putText(tile, f'{path.stem} : {len(markers)}', (5, 288), 0, .44, (255, 255, 255), 1)
        tiles.append(tile)
    if not tiles:
        raise SystemExit('No readable screenshots found')
    rows = []
    for i in range(0, len(tiles), 4):
        row = tiles[i:i+4]
        row += [np.zeros_like(tiles[0])] * (4-len(row))
        rows.append(np.hstack(row))
    cv2.imwrite(str(output / 'contact.png'), np.vstack(rows))
    (output / 'results.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    print(f'{len(records)} frames; {sum(r["markers"] for r in records)} markers; '
          f'{sum(r["markers"] == 0 for r in records)} frames without markers; '
          f'{sum(r["ms"] for r in records)/len(records):.2f} ms average detection')
    print(output.resolve())


if __name__ == '__main__':
    main()
