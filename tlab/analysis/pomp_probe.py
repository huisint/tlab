# Copyright (c) 2022 Shuhei Nitta. All rights reserved.
import io
import os
import functools
import dataclasses
import typing as t

import pandas as pd
import numpy as np
from scipy import optimize


FilePath = str | os.PathLike[str]
C = 3.0 * 1e-2  # 光速 [cm/ps]


@dataclasses.dataclass(frozen=True)
class PompProbeData:
    df: pd.DataFrame

    @classmethod
    def from_raw_file(
        cls,
        filepath_or_buffer: FilePath | io.BufferedIOBase,
        encoding: str | None = None,
        auto_time_offset: bool = True,
        auto_intensity_offset: bool = True,
    ) -> "PompProbeData":
        if isinstance(filepath_or_buffer, (str, os.PathLike)):
            with open(filepath_or_buffer, "rb") as f:
                self = cls._from_raw_buffer(f, encoding)
        elif isinstance(filepath_or_buffer, io.BufferedIOBase):
            self = cls._from_raw_buffer(filepath_or_buffer, encoding)
        else:
            raise TypeError("The type of filepath_or_buffer must be FilePath or io.BufferedIOBase")
        offset_index = self.get_offset_index()
        if auto_time_offset:
            time_offset = self.df["time"][offset_index]
            self.df["time"] += -time_offset
        if auto_intensity_offset:
            intensity_offset = np.polyfit(
                self.df["time"][:offset_index],
                self.df["intensity"][:offset_index],
                deg=0
            )
            self.df["intensity"] += -intensity_offset
        return self

    @classmethod
    def _from_raw_buffer(cls, file: io.BufferedIOBase, encoding: str | None = None) -> "PompProbeData":
        raw_df = pd.read_csv(
            file,
            encoding=encoding or "cp932",
            header=18
        )
        position = raw_df["x (cm)"]
        intensity = raw_df["強度1 (mv)"] * 1000
        time = position / C
        df = pd.DataFrame(dict(
            time=time,                  # [ps]
            intensity=intensity         # [arb. units]
        ))
        data = dict()
        data["df"] = df
        return cls(**data)

    def get_offset_index(self, window: int = 10, k: int = 2) -> pd.Index:  # pragma: no cover
        assert "time" in self.df.columns
        assert "intensity" in self.df.columns
        intensity = self.df["intensity"]
        rolling = intensity.rolling(window)
        mean = rolling.mean()
        std = rolling.std()
        offset_index = self.df.index[(intensity > mean + k * std).shift(-3).fillna(False)]
        return offset_index[0]


@dataclasses.dataclass(frozen=True)
class PompProbePairData:
    RR: PompProbeData
    RL: PompProbeData

    @classmethod
    def from_raw_files(
        cls,
        RR_filepath_or_buffer: FilePath | io.BufferedIOBase,
        RL_filepath_or_buffer: FilePath | io.BufferedIOBase,
        encoding: str | None = None
    ) -> "PompProbePairData":
        return cls(
            PompProbeData.from_raw_file(RR_filepath_or_buffer, encoding),
            PompProbeData.from_raw_file(RL_filepath_or_buffer, encoding),
        )

    @functools.cached_property
    def df(self) -> pd.DataFrame:
        time = self.RR.df["time"]
        RR = self.RR.df["intensity"]
        RL = self.RL.df["intensity"]
        return pd.DataFrame(dict(
            time=time,                                     # [ps]
            RR=RR,                                         # [arb. units]
            RL=RL,                                         # [arb. units]
            SpinPolarization=(RR - RL) / (RR + RL) * 100,  # [%]
        ))

    def fit(self, time_range: tuple[float, float], func: t.Callable[[t.Any], t.Any]) -> t.Any:  # pragma: no cover
        time = self.df["time"]
        index = self.df.index[time.between(*time_range)]
        params, cov = optimize.curve_fit(func, time[index], self.df["SpinPolarization"][index])
        self.df["fit"] = np.nan
        self.df["fit"][index] = func(time[index], *params)
        return params, cov
