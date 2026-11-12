"""The recipe's configuration: exactly the written constants of t04-values-v4.md section 4.3 that the light model and the
readout model need, and nothing else, so a constant derived from pulls or targets has nowhere to go (section 2.2).

The sensor geometry follows from the constants: the Fibonacci lattice of section 4.3, sensor i at polar angle
arccos(1 - 2 (i + 0.5)/1000) and azimuth pi (1 + sqrt 5)(i + 0.5), on the sphere of radius R_s, normal pointing outward. The
lattice index i is the stable channel ID. The time constants (photon speed, time spread) are part of the stated model; the
charge-only likelihood of stage 1 does not use them.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy

FORMAT = "light-likelihood-configuration/1"
DEFAULT = Path(__file__).resolve().parent.parent / "t09-sphere-1.configuration.json"
NUMBER_KEYS = ("sphere_radius_m", "sensor_area_m2", "photon_speed_m_per_ns", "attenuation_length_m", "emission_f", "emission_k",
               "dark_mean_per_window", "window_ns", "time_spread_ns", "photon_charge_mean", "photon_charge_sigma", "charge_threshold")
KEYS = {"format", "sensors", *NUMBER_KEYS}


class ConfigurationError(ValueError):
    """The configuration file is refused."""


@dataclass(frozen=True)
class Configuration:
    values: dict
    sha256: str

    def __getattr__(self, name):
        try:
            return self.__dict__["values"][name]
        except KeyError:
            raise AttributeError(name) from None


@dataclass(frozen=True)
class Geometry:
    """Sensor positions (C, 3) in m, outward unit normals (C, 3), one area in m2. Row i is channel i."""
    positions: numpy.ndarray
    normals: numpy.ndarray
    area: float

    @property
    def channels(self) -> int:
        return self.positions.shape[0]


def load(path=None, expected_format: str = FORMAT) -> Configuration:
    """Read and check a configuration file. expected_format is FORMAT for the main recipe; the single-photon variant's reader
    (single_photon.load, D4 E1b) passes its own format, so each reader refuses the other's file and no file carries a flag."""
    path = Path(path) if path is not None else DEFAULT
    try:
        content = path.read_bytes()
        doc = json.loads(content)
    except (OSError, ValueError) as exc:
        raise ConfigurationError(f"configuration cannot be read: {exc}") from None
    if not isinstance(doc, dict) or set(doc) != KEYS:
        raise ConfigurationError(f"configuration keys must be exactly {sorted(KEYS)}")
    if doc["format"] != expected_format:
        raise ConfigurationError(f"configuration format must be {expected_format}")
    if isinstance(doc["sensors"], bool) or not isinstance(doc["sensors"], int) or doc["sensors"] < 1:
        raise ConfigurationError("sensors must be a positive integer")
    for key in NUMBER_KEYS:
        value = doc[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ConfigurationError(f"{key} must be a positive finite number")
    if not doc["emission_f"] <= 1:
        raise ConfigurationError("emission_f must be at most 1")
    return Configuration({k: (float(v) if k in NUMBER_KEYS else v) for k, v in doc.items()}, hashlib.sha256(content).hexdigest())


def fibonacci_geometry(cfg: Configuration) -> Geometry:
    count = cfg.sensors
    index = numpy.arange(count) + 0.5
    polar = numpy.arccos(1.0 - 2.0 * index / count)
    azimuth = math.pi * (1.0 + math.sqrt(5.0)) * index
    normals = numpy.column_stack((numpy.sin(polar) * numpy.cos(azimuth), numpy.sin(polar) * numpy.sin(azimuth), numpy.cos(polar)))
    return Geometry(cfg.sphere_radius_m * normals, normals, cfg.sensor_area_m2)
