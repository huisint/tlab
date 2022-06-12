# Copyright (c) 2022 Shuhei Nitta. All rights reserved.
from unittest import TestCase, mock
import io
import os
import tempfile

import numpy as np
import numpy.testing as npt
import pandas as pd
import pandas.testing as pdt

from tlab.analysis import photo_luminescence as pl


HEADER = bytes.fromhex(
    "49 4d cd 01 80 02 e0 01 00 00 00 00 02 00 00 00"
    "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
    "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
    "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
)
METADATA = [
    b"HiPic,1.0,100,1.0,0,0,4,8,0,0,0,01-01-1970,00:00:00,"
    b"0,0,0,0,0, , , , ,0,0,0,0,0, , ,0,, , , ,0,0,, ,0,0,0,0,0,0,0,0,0,0,"
    b"2,1,nm,*0614925,2,1,ns,*0619021,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0.0,0,0,"
    b"StopCondition:PhotonCounting, Frame=10000, Time=673.1[sec], CountingRate=0.13[%]\n",
    b"Streak:Time=10 ns, Mode=Operate, Shutter=0, MCPGain=12, MCPSwitch=1, \n",
    b"Spectrograph:Wavelength=490.000[nm], Grating=2 : 150g/mm, SlitWidthIn=100[um], Mode=Spectrograph\n",
    b"Date:2022/06/03,14:09:55\n"
]
WAVELENGTH_RESOLUTION = 640
TIME_RESOLUTION = 480
STREAK_IMAGE = np.random.randint(0, 32, WAVELENGTH_RESOLUTION * TIME_RESOLUTION, dtype=np.uint16).tobytes("C")
WAVELENGTH = np.linspace(435, 535, WAVELENGTH_RESOLUTION, dtype=np.float32).tobytes("C").ljust(1024*4, b"\x00")
TIME = np.linspace(0, 10, TIME_RESOLUTION, dtype=np.float32).tobytes("C").ljust(1024*4, b"\x00")
RAW = HEADER + b"".join(METADATA) + STREAK_IMAGE + WAVELENGTH + TIME


class TestPLData_from_raw_file(TestCase):

    def setUp(self) -> None:
        time = np.frombuffer(TIME, dtype=np.float32)[:TIME_RESOLUTION]
        wavelength = np.frombuffer(WAVELENGTH, dtype=np.float32)[:WAVELENGTH_RESOLUTION]
        intensity = np.frombuffer(STREAK_IMAGE, dtype=np.uint16).astype(np.uint32)
        self.pldata = pl.PLData(
            header=HEADER,
            metadata=[b.decode("UTF-8") for b in METADATA],
            time=time,
            wavelength=wavelength,
            intensity=intensity
        )

    def _test(self, pldata: pl.PLData) -> None:
        self.assertEqual(pldata.header, self.pldata.header)
        self.assertListEqual(pldata.metadata, self.pldata.metadata)
        npt.assert_array_equal(pldata.time, self.pldata.time)
        npt.assert_array_equal(pldata.wavelength, self.pldata.wavelength)
        npt.assert_array_equal(pldata.intensity, self.pldata.intensity)

    def test_filepath_or_buffer(self) -> None:
        with self.subTest("Filepath"):
            with tempfile.TemporaryDirectory() as tmpdir:
                filepath = os.path.join(tmpdir, "photo_luminescence_testcase.img")
                with open(filepath, "wb") as f:
                    f.write(RAW)
                pldata = pl.PLData.from_raw_file(filepath)
                self._test(pldata)
        with self.subTest("Buffer"):
            with io.BytesIO(RAW) as f:
                pldata = pl.PLData.from_raw_file(f)
            self._test(pldata)
        with self.subTest("Invalid Type"):
            with self.assertRaises(TypeError):
                pl.PLData.from_raw_file(None)  # type: ignore


class TestPLData_property(TestCase):

    def setUp(self) -> None:
        time = np.frombuffer(TIME, dtype=np.float32)[:TIME_RESOLUTION]
        wavelength = np.frombuffer(WAVELENGTH, dtype=np.float32)[:WAVELENGTH_RESOLUTION]
        intensity = np.frombuffer(STREAK_IMAGE, dtype=np.uint16).astype(np.uint32)
        self.pldata = pl.PLData(time=time, wavelength=wavelength, intensity=intensity)

    def test_streak_image(self) -> None:
        streak_image = self.pldata.intensity.reshape(len(self.pldata.time), len(self.pldata.wavelength))
        npt.assert_array_equal(self.pldata.streak_image, streak_image)

    def test_df(self) -> None:
        df = pd.DataFrame(dict(
            time=np.repeat(self.pldata.time, len(self.pldata.wavelength)),
            wavelength=np.tile(self.pldata.wavelength, len(self.pldata.time)),
            intensity=self.pldata.intensity,
        ))
        pdt.assert_frame_equal(self.pldata.df, df)


class TestPLData_to_hdf(TestCase):

    def setUp(self) -> None:
        time = np.frombuffer(TIME, dtype=np.float32)[:TIME_RESOLUTION]
        wavelength = np.frombuffer(WAVELENGTH, dtype=np.float32)[:WAVELENGTH_RESOLUTION]
        intensity = np.frombuffer(STREAK_IMAGE, dtype=np.uint16).astype(np.uint32)
        self.pldata = pl.PLData(time=time, wavelength=wavelength, intensity=intensity)

    def _test(self, time_range: tuple[float, float] | None = None) -> None:
        hdf = self.pldata.to_hdf(time_range)
        if time_range is None:
            time = self.pldata.time
            time_range = time.min(), time.max()
        df = self.pldata.df[self.pldata.df["time"].between(*time_range)] \
            .groupby("wavelength") \
            .sum() \
            .drop("time", axis=1) \
            .reset_index()
        pdt.assert_frame_equal(hdf, df)

    def test_time_range(self) -> None:
        time = self.pldata.time
        time_range_list = [
            None,
            (float(time.min()), float(time.max())),
            (float(time[5]), float(time[-5]))
        ]
        for time_range in time_range_list:
            with self.subTest(time_range=time_range):
                self._test(time_range=time_range)


class TestPLData_to_vdf(TestCase):

    def setUp(self) -> None:
        time = np.frombuffer(TIME, dtype=np.float32)[:TIME_RESOLUTION]
        wavelength = np.frombuffer(WAVELENGTH, dtype=np.float32)[:WAVELENGTH_RESOLUTION]
        intensity = np.frombuffer(STREAK_IMAGE, dtype=np.uint16).astype(np.uint32)
        self.pldata = pl.PLData(time=time, wavelength=wavelength, intensity=intensity)

    def _test(
        self,
        wavelength_range: tuple[float, float] | None = None,
        auto_time_offset: bool = False,
        auto_intensity_offset: bool = False
    ) -> None:
        offset_index = pd.Index([10])[0]
        with mock.patch("tlab.analysis.photo_luminescence._get_offset_index_for_vdf", return_value=offset_index):
            vdf = self.pldata.to_vdf(wavelength_range, auto_time_offset, auto_intensity_offset)
        if wavelength_range is None:
            wavelength = self.pldata.wavelength
            wavelength_range = wavelength.min(), wavelength.max()
        df = self.pldata.df[self.pldata.df["wavelength"].between(*wavelength_range)] \
            .groupby("time") \
            .sum() \
            .drop("wavelength", axis=1) \
            .reset_index()
        if auto_time_offset:
            time_offset = df["time"][offset_index]
            df["time"] += -time_offset
        if auto_intensity_offset:
            intensity_offset = np.polyfit(
                df["time"][:offset_index],
                df["intensity"][:offset_index],
                deg=0
            )
            df["intensity"] += -intensity_offset
        pdt.assert_frame_equal(vdf, df)

    def test_wavelength_range(self) -> None:
        wavelength = self.pldata.wavelength
        wavelength_range_list: list[tuple[float, float] | None] = [
            None,
            (float(wavelength.min()), float(wavelength.max())),
            (float(wavelength[5]), float(wavelength[-5]))
        ]
        for wavelength_range in wavelength_range_list:
            with self.subTest(wavelength_range=wavelength_range):
                self._test(wavelength_range=wavelength_range)

    def test_auto_time_offset(self) -> None:
        for auto_time_offset in [True, False]:
            with self.subTest(auto_time_offset=auto_time_offset):
                self._test(auto_time_offset=auto_time_offset)

    def test_auto_intensity_offset(self) -> None:
        for auto_intensity_offset in [True, False]:
            with self.subTest(auto_intensity_offset=auto_intensity_offset):
                self._test(auto_intensity_offset=auto_intensity_offset)


class TestPLData_to_raw_binary(TestCase):

    def setUp(self) -> None:
        time = np.frombuffer(TIME, dtype=np.float32)[:TIME_RESOLUTION]
        wavelength = np.frombuffer(WAVELENGTH, dtype=np.float32)[:WAVELENGTH_RESOLUTION]
        intensity = np.frombuffer(STREAK_IMAGE, dtype=np.uint16).astype(np.uint32)
        self.pldata = pl.PLData(
            header=HEADER,
            metadata=[b.decode("UTF-8") for b in METADATA],
            time=time,
            wavelength=wavelength,
            intensity=intensity
        )

    def test_default(self) -> None:
        data = self.pldata.header \
            + "".join(self.pldata.metadata).encode("UTF-8") \
            + self.pldata.intensity.astype(np.uint16).tobytes("C") \
            + self.pldata.wavelength.tobytes("C").ljust(4096, b"\x00") \
            + self.pldata.time.tobytes("C").ljust(4096, b"\x00")
        self.assertEqual(self.pldata.to_raw_binary(), data)
