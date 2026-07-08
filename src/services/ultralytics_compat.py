from __future__ import annotations


def ensure_cv2_highgui_compat() -> None:
    """Patch missing OpenCV highgui APIs for headless/minimal builds.

    Ultralytics imports `cv2.imshow` during module import. Some packaged or
    headless OpenCV builds omit that symbol even though our app never opens
    OpenCV GUI windows directly. We provide lightweight no-op fallbacks so
    training and detection can still start.
    """

    import cv2

    def _noop(*_args, **_kwargs):
        return None

    fallbacks = {
        "imshow": _noop,
        "namedWindow": _noop,
        "resizeWindow": _noop,
        "destroyWindow": _noop,
        "destroyAllWindows": _noop,
        "setMouseCallback": _noop,
        "waitKey": lambda *_args, **_kwargs: -1,
    }
    for name, fallback in fallbacks.items():
        if not hasattr(cv2, name):
            setattr(cv2, name, fallback)
