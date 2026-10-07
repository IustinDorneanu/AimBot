"""Separate preview window: never draws into the game or controls the mouse."""

def render(frame, detections, selected, profile, stats):
    import cv2
    canvas = frame.copy()
    center = (canvas.shape[1] // 2, canvas.shape[0] // 2)
    cv2.circle(canvas, center, profile.aim_radius, (180, 110, 30), 1)
    cv2.drawMarker(canvas, center, (255, 255, 255), cv2.MARKER_CROSS, 18, 1)
    for d in detections:
        color = (50, 230, 120) if d is selected else (30, 180, 240)
        cv2.rectangle(canvas, (int(d.x), int(d.y)), (int(d.x + d.width), int(d.y + d.height)), color, 2)
        label = d.label if d.label == 'health-bar + level' else f"{d.label} {d.confidence:.2f}"
        cv2.putText(canvas, label, (int(d.x), max(18, int(d.y) - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    if selected is not None:
        point = tuple(round(n) for n in selected.point(profile.target_point))
        cv2.line(canvas, center, point, (50, 230, 120), 2)
        cv2.circle(canvas, point, 5, (50, 230, 120), -1)
    for index, line in enumerate(stats):
        y = 22 + index * 22
        cv2.putText(canvas, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
        cv2.putText(canvas, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return canvas
