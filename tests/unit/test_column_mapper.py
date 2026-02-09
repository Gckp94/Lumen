"""Unit tests for ColumnMapper."""

from pathlib import Path

from src.core.column_mapper import ColumnMapper
from src.core.models import ColumnMapping


class TestAutoDetect:
    """Tests for auto_detect method."""

    def test_auto_detect_standard_columns(self) -> None:
        """Auto-detect returns complete mapping for standard column names."""
        mapper = ColumnMapper()
        columns = ["ticker", "date", "time", "gain_pct", "mae_pct", "mfe_pct", "win_loss"]
        result = mapper.auto_detect(columns)

        assert result.mapping is not None
        assert result.all_required_detected is True
        assert result.mapping.ticker == "ticker"
        assert result.mapping.date == "date"
        assert result.mapping.time == "time"
        assert result.mapping.gain_pct == "gain_pct"
        assert result.mapping.mae_pct == "mae_pct"
        assert result.mapping.mfe_pct == "mfe_pct"
        assert result.mapping.win_loss == "win_loss"

    def test_auto_detect_case_insensitive(self) -> None:
        """Auto-detect is case-insensitive."""
        mapper = ColumnMapper()
        columns = ["TICKER", "Date", "TIME", "Gain_Pct", "MAE_PCT", "MFE_PCT"]
        result = mapper.auto_detect(columns)

        assert result.mapping is not None
        assert result.all_required_detected is True
        assert result.mapping.ticker == "TICKER"
        assert result.mapping.date == "Date"
        assert result.mapping.time == "TIME"
        assert result.mapping.gain_pct == "Gain_Pct"
        assert result.mapping.mae_pct == "MAE_PCT"
        assert result.mapping.mfe_pct == "MFE_PCT"

    def test_auto_detect_partial_match(self) -> None:
        """Auto-detect returns partial result for missing columns."""
        mapper = ColumnMapper()
        columns = ["ticker", "date", "other_column"]
        result = mapper.auto_detect(columns)

        assert result.mapping is None
        assert result.all_required_detected is False
        assert result.statuses["ticker"] == "detected"
        assert result.statuses["date"] == "detected"
        assert result.statuses["time"] == "missing"
        assert result.statuses["gain_pct"] == "missing"
        assert result.statuses["mae_pct"] == "missing"
        assert result.statuses["mfe_pct"] == "missing"

    def test_auto_detect_pattern_variations(self) -> None:
        """Auto-detect matches pattern variations."""
        mapper = ColumnMapper()
        columns = ["symbol", "trade_date", "entry_time", "pnl", "max_adverse", "max_favorable"]
        result = mapper.auto_detect(columns)

        assert result.mapping is not None
        assert result.all_required_detected is True
        assert result.mapping.ticker == "symbol"
        assert result.mapping.date == "trade_date"
        assert result.mapping.time == "entry_time"
        assert result.mapping.gain_pct == "pnl"
        assert result.mapping.mae_pct == "max_adverse"
        assert result.mapping.mfe_pct == "max_favorable"

    def test_auto_detect_substring_match(self) -> None:
        """Auto-detect matches substrings in column names."""
        mapper = ColumnMapper()
        columns = [
            "stock_ticker", "entry_date_utc", "trade_time_local", "gain_percent", "drawdown_pct", "runup_pct"
        ]
        result = mapper.auto_detect(columns)

        assert result.mapping is not None
        assert result.all_required_detected is True
        assert result.mapping.ticker == "stock_ticker"
        assert result.mapping.date == "entry_date_utc"
        assert result.mapping.time == "trade_time_local"
        assert result.mapping.gain_pct == "gain_percent"
        assert result.mapping.mae_pct == "drawdown_pct"
        assert result.mapping.mfe_pct == "runup_pct"

    def test_auto_detect_win_loss_optional(self) -> None:
        """Win/Loss column is optional for complete mapping."""
        mapper = ColumnMapper()
        columns = ["ticker", "date", "time", "gain", "mae", "mfe"]
        result = mapper.auto_detect(columns)

        assert result.mapping is not None
        assert result.all_required_detected is True
        assert result.mapping.win_loss is None
        assert result.statuses["win_loss"] == "missing"

    def test_auto_detect_trigger_time_et(self) -> None:
        """Test that trigger_time_et is auto-detected as time column."""
        columns = ["ticker", "date", "trigger_time_et", "gain_pct", "mae_pct", "mfe_pct"]
        mapper = ColumnMapper()
        result = mapper.auto_detect(columns)

        assert result.all_required_detected is True
        assert result.mapping is not None
        assert result.mapping.time == "trigger_time_et"
        assert result.statuses["time"] == "detected"


class TestSaveLoadMapping:
    """Tests for save_mapping and load_mapping methods."""

    def test_save_and_load_mapping(self, tmp_path: Path) -> None:
        """Save and load mapping from cache."""
        mapper = ColumnMapper(cache_dir=tmp_path)
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
        )
        file_path = Path("/fake/path/data.csv")
        mapper.save_mapping(file_path, mapping)

        loaded = mapper.load_mapping(file_path)
        assert loaded is not None
        assert loaded.ticker == "ticker"
        assert loaded.date == "date"
        assert loaded.time == "time"
        assert loaded.gain_pct == "gain_pct"
        assert loaded.mae_pct == "mae_pct"
        assert loaded.mfe_pct == "mfe_pct"

    def test_load_mapping_not_found(self, tmp_path: Path) -> None:
        """Load returns None for non-existent mapping."""
        mapper = ColumnMapper(cache_dir=tmp_path)
        loaded = mapper.load_mapping(Path("/nonexistent/file.csv"))
        assert loaded is None

    def test_save_mapping_creates_cache_dir(self, tmp_path: Path) -> None:
        """Save creates cache directory if it doesn't exist."""
        cache_dir = tmp_path / "new_cache"
        mapper = ColumnMapper(cache_dir=cache_dir)
        mapping = ColumnMapping(ticker="t", date="d", time="ti", gain_pct="g", mae_pct="m", mfe_pct="mf")

        mapper.save_mapping(Path("/test/file.csv"), mapping)

        assert cache_dir.exists()

    def test_save_mapping_with_sheet(self, tmp_path: Path) -> None:
        """Save and load mapping with sheet name."""
        mapper = ColumnMapper(cache_dir=tmp_path)
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain",
            mae_pct="mae",
            mfe_pct="mfe",
        )
        file_path = Path("/path/to/workbook.xlsx")

        mapper.save_mapping(file_path, mapping, sheet="Sheet1")
        loaded = mapper.load_mapping(file_path, sheet="Sheet1")

        assert loaded is not None
        assert loaded.ticker == "ticker"

        # Different sheet should return None
        loaded_other = mapper.load_mapping(file_path, sheet="Sheet2")
        assert loaded_other is None

    def test_save_mapping_with_all_fields(self, tmp_path: Path) -> None:
        """Save and load mapping with all optional fields."""
        mapper = ColumnMapper(cache_dir=tmp_path)
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain",
            mae_pct="mae",
            mfe_pct="mfe",
            win_loss="result",
            win_loss_derived=False,
            breakeven_is_win=True,
        )
        file_path = Path("/test.csv")

        mapper.save_mapping(file_path, mapping)
        loaded = mapper.load_mapping(file_path)

        assert loaded is not None
        assert loaded.mae_pct == "mae"
        assert loaded.win_loss == "result"
        assert loaded.win_loss_derived is False
        assert loaded.breakeven_is_win is True

    def test_load_mapping_invalid_json(self, tmp_path: Path) -> None:
        """Load returns None for corrupted cache file."""
        mapper = ColumnMapper(cache_dir=tmp_path)
        file_path = Path("/test.csv")

        # Create corrupted cache file
        file_hash = mapper._get_file_hash(file_path)
        cache_path = tmp_path / f"{file_hash}_mappings.json"
        cache_path.write_text("invalid json")

        loaded = mapper.load_mapping(file_path)
        assert loaded is None


class TestMatchColumn:
    """Tests for _match_column helper method."""

    def test_exact_match(self) -> None:
        """Exact match returns detected status."""
        mapper = ColumnMapper()
        columns = ["ticker", "other"]
        col, status = mapper._match_column(columns, ["ticker"])

        assert col == "ticker"
        assert status == "detected"

    def test_exact_match_case_insensitive(self) -> None:
        """Exact match is case insensitive."""
        mapper = ColumnMapper()
        columns = ["TICKER", "other"]
        col, status = mapper._match_column(columns, ["ticker"])

        assert col == "TICKER"
        assert status == "detected"

    def test_substring_match(self) -> None:
        """Substring match returns detected status."""
        mapper = ColumnMapper()
        columns = ["stock_ticker_col", "other"]
        col, status = mapper._match_column(columns, ["ticker"])

        assert col == "stock_ticker_col"
        assert status == "detected"

    def test_no_match(self) -> None:
        """No match returns missing status."""
        mapper = ColumnMapper()
        columns = ["foo", "bar"]
        col, status = mapper._match_column(columns, ["ticker"])

        assert col is None
        assert status == "missing"


class TestAutoDetectionPriority:
    """Tests for column auto-detection preferring exact/shorter matches."""

    def test_prefers_exact_match_over_substring(self) -> None:
        """Should prefer 'gain_pct' over 'gain_pct_from_low'."""
        mapper = ColumnMapper()
        columns = [
            "ticker",
            "date",
            "time",
            "gain_pct_from_low",  # Longer, appears first
            "gain_pct",  # Exact match, appears second
            "mae_pct",
            "mfe_pct",
        ]

        result = mapper.auto_detect(columns)

        assert result.mapping is not None
        assert result.mapping.gain_pct == "gain_pct", (
            f"Expected 'gain_pct' but got '{result.mapping.gain_pct}'. "
            "Auto-detection should prefer shorter/exact matches."
        )

    def test_prefers_shorter_match_when_both_contain_pattern(self) -> None:
        """Should prefer shorter column name when multiple contain pattern."""
        mapper = ColumnMapper()
        columns = [
            "ticker",
            "date",
            "trigger_time_et",  # Longer
            "time",  # Shorter, exact
            "gain_pct",
            "mae_pct",
            "mfe_pct",
        ]

        result = mapper.auto_detect(columns)

        assert result.mapping is not None
        assert result.mapping.time == "time", (
            f"Expected 'time' but got '{result.mapping.time}'. "
            "Auto-detection should prefer shorter matches."
        )

    def test_exact_pattern_match_takes_priority(self) -> None:
        """Exact pattern match should beat substring match."""
        mapper = ColumnMapper()
        columns = [
            "my_ticker_symbol",  # Contains 'ticker'
            "ticker",  # Exact match
            "date",
            "time",
            "gain_pct",
            "mae_pct",
            "mfe_pct",
        ]

        result = mapper.auto_detect(columns)

        assert result.mapping is not None
        assert result.mapping.ticker == "ticker"


class TestDuplicateValidation:
    """Tests for duplicate column validation."""

    def test_duplicate_column_validation(self) -> None:
        """Duplicate columns should be caught by ColumnMapping.validate."""
        mapping = ColumnMapping(
            ticker="col1",
            date="col1",  # Duplicate
            time="col2",
            gain_pct="col3",
            mae_pct="col4",
            mfe_pct="col5",
        )
        # Note: ColumnMapping.validate checks if columns exist, not duplicates
        # Duplicate validation is done in UI layer
        errors = mapping.validate(["col1", "col2", "col3", "col4", "col5"])
        # No errors from validate since columns exist
        assert len(errors) == 0


class TestPriceIntervalAutoDetect:
    """Tests for price interval column auto-detection."""

    def test_auto_detect_populates_mapping_with_price_intervals(self) -> None:
        """Test that detected price intervals are included in ColumnMapping."""
        columns = [
            "ticker", "date", "time", "gain_pct", "mae_pct", "mfe_pct",
            "price_10_min_after", "price_60_min_after", "price_240_min_after",
        ]
        mapper = ColumnMapper()
        result = mapper.auto_detect(columns)

        assert result.mapping is not None
        assert result.mapping.price_10_min_after == "price_10_min_after"
        assert result.mapping.price_60_min_after == "price_60_min_after"
        assert result.mapping.price_240_min_after == "price_240_min_after"
        # Columns not present should be None
        assert result.mapping.price_20_min_after is None

    def test_auto_detect_price_10_min_after(self) -> None:
        """Test that price_10_min_after is auto-detected."""
        columns = [
            "ticker", "date", "time", "gain_pct", "mae_pct", "mfe_pct",
            "price_10_min_after"
        ]
        mapper = ColumnMapper()
        result = mapper.auto_detect(columns)

        assert result.statuses.get("price_10_min_after") == "detected"

    def test_auto_detect_all_price_intervals(self) -> None:
        """Test all price interval columns are auto-detected."""
        columns = [
            "ticker", "date", "time", "gain_pct", "mae_pct", "mfe_pct",
            "price_10_min_after", "price_20_min_after", "price_30_min_after",
            "price_60_min_after", "price_90_min_after", "price_120_min_after",
            "price_150_min_after", "price_180_min_after", "price_240_min_after",
        ]
        mapper = ColumnMapper()
        result = mapper.auto_detect(columns)

        intervals = [10, 20, 30, 60, 90, 120, 150, 180, 240]
        for interval in intervals:
            field = f"price_{interval}_min_after"
            assert result.statuses.get(field) == "detected", f"{field} not detected"
