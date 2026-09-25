"""One Euro Filter: low-latency jitter reduction for interactive pointing.

Reference: Casiez, Roussel & Vogel, "1 Euro Filter" (CHI 2012).
A moving average removes jitter but adds lag; this filter adapts its
cutoff to the pointer speed, so it stays smooth when still and
responsive when moving fast.
"""
import math
import time


class OneEuroFilter:
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.0, d_cutoff: float = 1.0):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self._x_prev = None
        self._dx_prev = 0.0
        self._t_prev = None

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x: float, t: float = None) -> float:
        t = time.monotonic() if t is None else t
        if self._x_prev is None:
            self._x_prev, self._t_prev = x, t
            return x

        dt = t - self._t_prev
        if dt <= 0:
            dt = 1e-6

        dx = (x - self._x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1.0 - a_d) * self._dx_prev

        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)
        x_hat = a * x + (1.0 - a) * self._x_prev

        self._x_prev, self._dx_prev, self._t_prev = x_hat, dx_hat, t
        return x_hat

    def reset(self) -> None:
        self._x_prev = None
        self._dx_prev = 0.0
        self._t_prev = None


class Point2DFilter:
    """A One Euro Filter applied independently to the x and y of a point."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.0):
        self._fx = OneEuroFilter(min_cutoff, beta)
        self._fy = OneEuroFilter(min_cutoff, beta)

    def __call__(self, x: float, y: float, t: float = None):
        return self._fx(x, t), self._fy(y, t)

    def reset(self) -> None:
        self._fx.reset()
        self._fy.reset()
