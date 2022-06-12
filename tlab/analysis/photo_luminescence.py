# Copyright (c) 2022 Shuhei Nitta. All rights reserved.
import os
import io
import dataclasses
import functools
import typing as t

import numpy as np
import numpy.typing as npt
import pandas as pd

FilePath = str | os.PathLike[str]


@dataclasses.dataclass(frozen=True)
class PLData:
    intensity: npt.NDArray[np.uint32]
    wavelength: npt.NDArray[np.float32]
    time: npt.NDArray[np.float32]
    header: bytes = bytes.fromhex(
        "49 4d cd 01 80 02 e0 01 00 00 00 00 02 00 00 00"
        "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
        "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
        "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
    )
    metadata: list[str] = dataclasses.field(default_factory=list)

    @classmethod
    def from_raw_file(cls, filepath_or_buffer: FilePath | io.BufferedIOBase) -> "PLData":
        if isinstance(filepath_or_buffer, (str, os.PathLike)):
            with open(filepath_or_buffer, "rb") as f:
                self = cls._from_raw_buffer(f)
        elif isinstance(filepath_or_buffer, io.BufferedIOBase):
            self = cls._from_raw_buffer(filepath_or_buffer)
        else:
            raise TypeError("The type of filepath_or_buffer must be FilePath or io.BufferedIOBase")
        return self

    @classmethod
    def _from_raw_buffer(cls, file: io.BufferedIOBase) -> "PLData":
        sector_size = 1024
        wavelength_resolution = 640
        time_resolution = 480
        header = file.read(64)
        metadata = [file.readline() for _ in range(4)]
        intensity = np.frombuffer(file.read(sector_size*600), dtype=np.uint16)
        wavelength = np.frombuffer(file.read(sector_size*4), dtype=np.float32)[:wavelength_resolution]
        time = np.frombuffer(file.read(sector_size*4), dtype=np.float32)[:time_resolution]
        data: dict[str, t.Any] = dict()
        data["header"] = header
        data["metadata"] = [b.decode("UTF-8") for b in metadata]
        data["intensity"] = intensity
        data["wavelength"] = wavelength
        data["time"] = time
        return cls(**data)

    @functools.cached_property
    def df(self) -> pd.DataFrame:
        df = pd.DataFrame(dict(
            time=np.repeat(self.time, len(self.wavelength)),        # [ns]
            wavelength=np.tile(self.wavelength, len(self.time)),    # [nm]
            intensity=self.intensity                                # [arb. units]
        ))
        return df

    @functools.cached_property
    def streak_image(self) -> npt.NDArray[np.uint32]:
        return self.intensity.reshape(len(self.time), len(self.wavelength))

    def to_hdf(
        self,
        time_range: tuple[float, float] | None = None,
    ) -> pd.DataFrame:
        assert "wavelength" in self.df.columns
        assert "intensity" in self.df.columns
        if time_range is None:
            time = self.df["time"]
            time_range = time.min(), time.max()
        hdf = self.df[self.df["time"].between(*time_range)] \
            .groupby("wavelength") \
            .sum() \
            .drop("time", axis=1) \
            .reset_index()
        return hdf

    def to_vdf(
        self,
        wavelength_range: tuple[float, float] | None = None,
        auto_time_offset: bool = True,
        auto_intensity_offset: bool = True
    ) -> pd.DataFrame:
        assert "time" in self.df.columns
        assert "intensity" in self.df.columns
        if wavelength_range is None:
            wavelength = self.df["wavelength"]
            wavelength_range = wavelength.min(), wavelength.max()
        vdf = self.df[self.df["wavelength"].between(*wavelength_range)] \
            .groupby("time") \
            .sum() \
            .drop("wavelength", axis=1) \
            .reset_index()
        offset_index = _get_offset_index_for_vdf(vdf)
        if auto_time_offset:
            time_offset = vdf["time"][offset_index]
            vdf["time"] += -time_offset
        if auto_intensity_offset:
            intensity_offset = np.polyfit(
                vdf["time"][:offset_index],
                vdf["intensity"][:offset_index],
                deg=0
            )
            vdf["intensity"] += -intensity_offset
        return vdf

    def to_raw_binary(self) -> bytes:
        data = self.header \
            + "".join(self.metadata).encode("UTF-8") \
            + self.intensity.astype(np.uint16).tobytes("C") \
            + self.wavelength.tobytes("C").ljust(4096, b"\x00") \
            + self.time.tobytes("C").ljust(4096, b"\x00")
        return data


def _get_offset_index_for_vdf(vdf: pd.DataFrame, window: int = 10, k: int = 2) -> pd.Index:  # pragma: nocover
    assert "time" in vdf.columns
    assert "intensity" in vdf.columns
    intensity = vdf["intensity"]
    rolling = intensity.rolling(window)
    mean = rolling.mean()
    std = rolling.std()
    offset_index = vdf.index[(intensity > mean + k * std).shift(-3).fillna(False)]
    return offset_index[0]
