import io
from contextlib import redirect_stdout

from tenortui.config import CONFIG_OPTIONS, print_config_help


EXPECTED_KEYS = [
    "default",
    "yahoo.greeks.enabled",
    "yahoo.greeks.risk_free_rate",
    "tradier.api_key",
    "tradier.sandbox",
    "spread_thresholds.tight",
    "spread_thresholds.moderate",
    "refresh.regular",
    "refresh.extended",
    "refresh.closed",
]


class TestConfigOptions:
    def test_all_expected_keys_present(self):
        keys = [opt.key for opt in CONFIG_OPTIONS]
        for expected in EXPECTED_KEYS:
            assert expected in keys, f"Missing config option: {expected}"

    def test_no_empty_descriptions(self):
        for opt in CONFIG_OPTIONS:
            assert opt.description, f"Empty description for {opt.key}"

    def test_no_empty_types(self):
        for opt in CONFIG_OPTIONS:
            assert opt.type_name, f"Empty type for {opt.key}"

    def test_no_empty_defaults(self):
        for opt in CONFIG_OPTIONS:
            assert opt.default is not None, f"None default for {opt.key}"


class TestPrintConfigHelp:
    def _capture_output(self, config_path=None):
        buf = io.StringIO()
        with redirect_stdout(buf):
            print_config_help(config_path=config_path)
        return buf.getvalue()

    def test_header_present(self):
        output = self._capture_output()
        assert "TenorTUI Configuration Help" in output

    def test_all_option_keys_in_output(self):
        output = self._capture_output()
        for key in EXPECTED_KEYS:
            leaf = key.split(".")[-1]
            assert leaf in output, f"Option '{key}' leaf '{leaf}' not in output"

    def test_example_config_present(self):
        output = self._capture_output()
        assert "Example config:" in output
        assert "default: yahoo" in output

    def test_config_path_shown(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        output = self._capture_output(config_path=cfg)
        assert str(cfg) in output

    def test_config_exists_status(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("---\n")
        output = self._capture_output(config_path=cfg)
        assert "(exists)" in output

    def test_config_not_found_status(self, tmp_path):
        cfg = tmp_path / "nonexistent.yaml"
        output = self._capture_output(config_path=cfg)
        assert "(not found, using defaults)" in output

    def test_sections_indented(self):
        output = self._capture_output()
        assert "yahoo:" in output
        assert "tradier:" in output
        assert "spread_thresholds:" in output

    def test_conditions_shown(self):
        output = self._capture_output()
        assert "Only when provider is yahoo" in output
        assert "Required when provider is tradier" in output

    def test_refresh_section_in_output(self):
        output = self._capture_output()
        assert "refresh:" in output
        assert "regular" in output
        assert "extended" in output
        assert "closed" in output


class TestConfigHelpArgparse:
    def test_config_help_flag_recognized(self):
        from tenortui.app import _parse_args
        import sys

        original = sys.argv
        sys.argv = ["tenortui", "--config-help"]
        try:
            args = _parse_args()
            assert args.config_help is True
        finally:
            sys.argv = original

    def test_default_config_help_is_false(self):
        from tenortui.app import _parse_args
        import sys

        original = sys.argv
        sys.argv = ["tenortui"]
        try:
            args = _parse_args()
            assert args.config_help is False
        finally:
            sys.argv = original
