from dataclasses import dataclass


@dataclass(frozen=True)
class PatternSpec:
    folder: str
    queries: tuple[str, ...]


PATTERNS = [
    PatternSpec(
        "head_and_shoulders",
        (
            "head and shoulders chart pattern",
            "head and shoulders technical analysis",
            "head and shoulders trading pattern",
            "head and shoulders stock chart",
            "head and shoulders forex chart pattern",
            "head and shoulders crypto chart pattern",
            "head and shoulders tradingview pattern",
            "head and shoulders pattern diagram",
        ),
    ),
    PatternSpec(
        "inverse_head_and_shoulders",
        (
            "inverse head and shoulders chart pattern",
            "inverse head and shoulders technical analysis",
            "inverse head and shoulders trading pattern",
            "inverse head and shoulders stock chart",
            "inverse head and shoulders forex chart pattern",
            "inverse head and shoulders crypto chart pattern",
            "inverse head and shoulders tradingview pattern",
            "inverse head and shoulders pattern diagram",
        ),
    ),
    PatternSpec(
        "double_top",
        (
            "double top chart pattern",
            "double top technical analysis",
            "double top trading pattern",
            "double top stock chart",
            "double top forex chart pattern",
            "double top crypto chart pattern",
            "double top tradingview pattern",
            "double top pattern diagram",
        ),
    ),
    PatternSpec(
        "double_bottom",
        (
            "double bottom chart pattern",
            "double bottom technical analysis",
            "double bottom trading pattern",
            "double bottom stock chart",
            "double bottom forex chart pattern",
            "double bottom crypto chart pattern",
            "double bottom tradingview pattern",
            "double bottom pattern diagram",
        ),
    ),
    PatternSpec(
        "bullish_triange",
        (
            "bullish triangle chart pattern",
            "bullish triangle technical analysis",
            "bullish triangle trading pattern",
            "bullish triangle stock chart",
            "bullish triangle forex chart pattern",
            "bullish triangle crypto chart pattern",
            "bullish triangle breakout chart",
            "bullish triangle pattern diagram",
        ),
    ),
    PatternSpec(
        "bearish_triangle",
        (
            "bearish triangle chart pattern",
            "bearish triangle technical analysis",
            "bearish triangle trading pattern",
            "bearish triangle stock chart",
            "bearish triangle forex chart pattern",
            "bearish triangle crypto chart pattern",
            "bearish triangle breakdown chart",
            "bearish triangle pattern diagram",
        ),
    ),
    PatternSpec(
        "ascending_triangle",
        (
            "ascending triangle chart pattern",
            "ascending triangle technical analysis",
            "ascending triangle trading pattern",
            "ascending triangle stock chart",
            "ascending triangle forex chart pattern",
            "ascending triangle crypto chart pattern",
            "ascending triangle tradingview pattern",
            "ascending triangle pattern diagram",
        ),
    ),
    PatternSpec(
        "descending_triangle",
        (
            "descending triangle chart pattern",
            "descending triangle technical analysis",
            "descending triangle trading pattern",
            "descending triangle stock chart",
            "descending triangle forex chart pattern",
            "descending triangle crypto chart pattern",
            "descending triangle tradingview pattern",
            "descending triangle pattern diagram",
        ),
    ),
    PatternSpec(
        "cup_and_handle",
        (
            "cup and handle chart pattern",
            "cup and handle technical analysis",
            "cup and handle trading pattern",
            "cup and handle stock chart",
            "cup and handle forex chart pattern",
            "cup and handle crypto chart pattern",
            "cup and handle tradingview pattern",
            "cup and handle pattern diagram",
        ),
    ),
    PatternSpec(
        "bullish_flag",
        (
            "bullish flag chart pattern",
            "bullish flag technical analysis",
            "bullish flag trading pattern",
            "bullish flag stock chart",
            "bullish flag forex chart pattern",
            "bullish flag crypto chart pattern",
            "bull flag chart pattern",
            "bullish flag pattern diagram",
            "bullish flag continuation pattern",
            "bullish flag breakout chart",
            "bullish flag price action chart",
            "bullish flag trading setup",
        ),
    ),
    PatternSpec(
        "bearish_flag",
        (
            "bearish flag chart pattern",
            "bearish flag technical analysis",
            "bearish flag trading pattern",
            "bearish flag stock chart",
            "bearish flag forex chart pattern",
            "bearish flag crypto chart pattern",
            "bear flag chart pattern",
            "bearish flag pattern diagram",
            "bearish flag continuation pattern",
            "bearish flag breakdown chart",
            "bearish flag price action chart",
            "bearish flag trading setup",
        ),
    ),
    PatternSpec(
        "pennant",
        (
            "pennant chart pattern",
            "bullish pennant chart pattern",
            "bearish pennant chart pattern",
            "pennant technical analysis",
            "pennant trading pattern",
            "pennant stock chart",
            "pennant forex chart pattern",
            "pennant crypto chart pattern",
        ),
    ),
    PatternSpec(
        "rising_wedge",
        (
            "rising wedge chart pattern",
            "rising wedge technical analysis",
            "rising wedge trading pattern",
            "rising wedge stock chart",
            "rising wedge forex chart pattern",
            "rising wedge crypto chart pattern",
            "rising wedge tradingview pattern",
            "rising wedge pattern diagram",
        ),
    ),
    PatternSpec(
        "falling_wedge",
        (
            "falling wedge chart pattern",
            "falling wedge technical analysis",
            "falling wedge trading pattern",
            "falling wedge stock chart",
            "falling wedge forex chart pattern",
            "falling wedge crypto chart pattern",
            "falling wedge tradingview pattern",
            "falling wedge pattern diagram",
        ),
    ),
]

PATTERN_MAP = {pattern.folder: pattern for pattern in PATTERNS}
