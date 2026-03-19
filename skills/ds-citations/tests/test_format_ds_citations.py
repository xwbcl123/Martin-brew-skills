import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "format_ds_citations.py"
SPEC = importlib.util.spec_from_file_location("format_ds_citations", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DsCitationsRegressionTests(unittest.TestCase):
    def test_detects_body_footnote_definitions_before_final_block(self) -> None:
        content = r"""# Demo

正文段落。[^1]

[^2]: bad body definition

## Footnotes

[^1]: good footnote
[^2]: another footnote
"""

        self.assertEqual(
            MODULE.find_body_footnote_definition_lines(content),
            [5],
        )

    def test_gpt_conversion_preserves_inline_citations_across_sections(self) -> None:
        content = r"""# Demo

## Section A

Overview.[\[1\]](https://example.com/a)

---

## Section B

| Item | Value |
| :---- | :---- |
| SoC | M4[\[1\]](https://example.com/a) |

1\) Capacity matters.[\[2\]](https://example.com/b)

---

[\[1\]](https://example.com/a) https://example.com/a

[https://example.com/a](https://example.com/a)

[\[2\]](https://example.com/b) https://example.com/b

[https://example.com/b](https://example.com/b)
"""

        converted = MODULE.convert_gpt_variant_references(content)
        converted = MODULE.convert_gpt_inline(converted)

        self.assertIn("Overview.[^1]", converted)
        self.assertIn("| SoC | M4[^1] |", converted)
        self.assertIn("1\\) Capacity matters.[^2]", converted)
        self.assertIn("## Footnotes", converted)
        self.assertIn("[^1]: https://example.com/a https://example.com/a", converted)
        self.assertEqual(MODULE.find_body_footnote_definition_lines(converted), [])

    def test_process_file_blocks_malformed_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "bad.md"
            file_path.write_text(
                "# Demo\n\n正文引用[^1]\n\n[^1]: bad body definition\n\n## Footnotes\n\n[^1]: good footnote\n",
                encoding="utf-8",
            )

            result = MODULE.process_file(file_path, check_only=True)

            self.assertTrue(result.success)
            self.assertIn("Body footnote definitions", result.message)

    def test_gemini_inline_conversion_avoids_dimensions_and_decimals(self) -> None:
        content = (
            "设备尺寸 5×5×2 英寸，重量 0.73 千克，结论层级 1。升级溢价）4，本报告继续。"
        )

        converted = MODULE.convert_gemini_inline(content)

        self.assertIn("5×5×2 英寸", converted)
        self.assertIn("0.73 千克", converted)
        self.assertIn("层级  [^1]。", converted)
        self.assertIn("溢价） [^4]，", converted)


if __name__ == "__main__":
    unittest.main()
