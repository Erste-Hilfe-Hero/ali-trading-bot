# DaytradeMeanRevertEdge11 - wie Edge4, nur die 8 Coins, die in mehreren Laeufen vorne lagen; Runde 2 aus der Auswertung 2026-10-26 (Edge4 war ungesehen +0,20 $)
import sys
from pathlib import Path

from freqtrade.strategy import DecimalParameter, IntParameter

sys.path.append(str(Path(__file__).parent))
from DaytradeMeanRevertPro24Wide35 import DaytradeMeanRevertPro24Wide35  # noqa: E402


class DaytradeMeanRevertEdge11(DaytradeMeanRevertPro24Wide35):
    min_gap = 0.01
    bb_dev = DecimalParameter(1.8, 2.8, default=2.8, decimals=1, space="buy")
    rsi_max_entry = IntParameter(20, 38, default=22, space="buy")
    coins = {"NEAR/USDT", "UNI/USDT", "INJ/USDT", "ASTER/USDT", "FET/USDT", "TAO/USDT", "ARB/USDT", "ONDO/USDT"}

    def populate_entry_trend(self, dataframe, metadata):
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if metadata["pair"] not in self.coins:
            dataframe["enter_long"] = 0
        return dataframe
