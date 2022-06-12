# Copyright (c) 2022 Shuhei Nitta. All rights reserved.
from unittest import TestCase, mock
import io
import os
import tempfile

import numpy as np
import pandas as pd
import pandas.testing as pdt

from tlab.analysis import pomp_probe as pp


COUNT = 151
HEADER = f"""
8.2
9.7
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00
0
0
0
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00
{COUNT}
"no data"
"no data"
"no data"
"no data"
"no data"
"no data"
"no data"
"no data"
"no data"
"no data"
"""
DF = pd.DataFrame({
    "x (cm)": np.linspace(8.2, 9.7, COUNT),
    "強度1 (mv)": np.random.random(COUNT),
    "強度2 (mV)": np.zeros(COUNT),
    "Unnamed: 3": np.nan,
    "Unnamed: 4": np.nan
})
RAW_CSV = HEADER + DF.to_csv(index=False)


class TestPompProbeData_from_raw_file(TestCase):

    def setUp(self) -> None:
        position = DF["x (cm)"]
        intensity = DF["強度1 (mv)"] * 1000
        time = position / pp.C
        df = pd.DataFrame(dict(
            time=time,                  # [ps]
            intensity=intensity         # [arb. units]
        ))
        self.ppdata = pp.PompProbeData(df)

    def _test(
        self,
        filepath_or_buffer: pp.FilePath | io.BufferedIOBase,
        auto_time_offset: bool = False,
        auto_intensity_offset: bool = False
    ) -> None:
        self.setUp()
        offset_index = pd.Index([10])[0]
        if auto_time_offset:
            time_offset = self.ppdata.df["time"][offset_index]
            self.ppdata.df["time"] += -time_offset
        if auto_intensity_offset:
            intensity_offset = np.polyfit(
                self.ppdata.df["time"][:offset_index],
                self.ppdata.df["intensity"][:offset_index],
                deg=0
            )
            self.ppdata.df["intensity"] += -intensity_offset
        with mock.patch("tlab.analysis.pomp_probe.PompProbeData.get_offset_index", return_value=offset_index):
            ppdata = pp.PompProbeData.from_raw_file(
                filepath_or_buffer,
                auto_time_offset=auto_time_offset,
                auto_intensity_offset=auto_intensity_offset
            )
        pdt.assert_frame_equal(ppdata.df, self.ppdata.df)

    def test_filepath_or_buffer(self) -> None:
        with self.subTest("Filepath"):
            with tempfile.TemporaryDirectory() as tmpdir:
                filepath = os.path.join(tmpdir, "pomp_probe_testcase.csv")
                with open(filepath, "w", encoding="cp932") as f:
                    f.write(RAW_CSV)
                self._test(filepath)
        with self.subTest("Buffer"):
            with io.BytesIO(RAW_CSV.encode("cp932")) as f:
                self._test(f)
        with self.subTest("Invalid Type"):
            with self.assertRaises(TypeError):
                pp.PompProbeData.from_raw_file(None)  # type: ignore

    def test_auto_time_offset(self) -> None:
        for auto_time_offset in [True, False]:
            with self.subTest(auto_time_offset=auto_time_offset):
                with io.BytesIO(RAW_CSV.encode("cp932")) as f:
                    self._test(f, auto_time_offset=auto_time_offset)

    def test_auto_intensity_offset(self) -> None:
        for auto_intensity_offset in [True, False]:
            with self.subTest(auto_intensity_offset=auto_intensity_offset):
                with io.BytesIO(RAW_CSV.encode("cp932")) as f:
                    self._test(f, auto_intensity_offset=auto_intensity_offset)


@mock.patch("tlab.analysis.pomp_probe.PompProbeData.from_raw_file")
class TestPompProbePairData_from_raw_files(TestCase):
    RRmock = mock.Mock(spec_set=pp.PompProbeData)
    RLmock = mock.Mock(spec_set=pp.PompProbeData)

    def test_filepath_or_buffer(self, from_raw_file_mock: mock.Mock) -> None:
        from_raw_file_mock.side_effect = [self.RRmock, self.RLmock]
        filepaths = ["filepathRR", "filepathRL"]
        pair = pp.PompProbePairData.from_raw_files(*filepaths)
        self.assertEqual(pair.RR, self.RRmock)
        self.assertEqual(pair.RL, self.RLmock)
        self.assertListEqual(
            from_raw_file_mock.mock_calls,
            [mock.call(filepath, None) for filepath in filepaths]
        )

    def test_encoding(self, from_raw_file_mock: mock.Mock) -> None:
        filepaths = ["filepathRR", "filepathRL"]
        encodings = [None, "UTF-8", "cp932"]
        for encoding in encodings:
            from_raw_file_mock.reset_mock()
            from_raw_file_mock.side_effect = [self.RRmock, self.RLmock]
            with self.subTest(encoding=encoding):
                pair = pp.PompProbePairData.from_raw_files(filepaths[0], filepaths[1], encoding=encoding)
                self.assertEqual(pair.RR, self.RRmock)
                self.assertEqual(pair.RL, self.RLmock)
                self.assertListEqual(
                    from_raw_file_mock.mock_calls,
                    [mock.call(filepath, encoding) for filepath in filepaths]
                )


class TestPompProbePairData_property(TestCase):

    def setUp(self) -> None:
        position = DF["x (cm)"]
        intensity = DF["強度1 (mv)"] * 1000
        time = position / pp.C
        df = pd.DataFrame(dict(
            time=time,                  # [ps]
            intensity=intensity         # [arb. units]
        ))
        self.pair = pp.PompProbePairData(
            pp.PompProbeData(df),
            pp.PompProbeData(df)
        )

    def test_df(self) -> None:
        time = self.pair.RR.df["time"]
        RR = self.pair.RR.df["intensity"]
        RL = self.pair.RL.df["intensity"]
        df = pd.DataFrame(dict(
            time=time,                                     # [ps]
            RR=RR,                                         # [arb. units]
            RL=RL,                                         # [arb. units]
            SpinPolarization=(RR - RL) / (RR + RL) * 100,  # [%]
        ))
        pdt.assert_frame_equal(self.pair.df, df)
