#!/usr/bin/env python3
import re
import unittest

from repair_main import repair_main_html


def valid_main_with(feedback_html: str) -> str:
    return f"""<main>
<div class="narrative" data-nar="bonds"><button class="bull on" data-side="bull">Bull</button><div class="bullbear show-bull"></div></div>
<div class="narrative" data-nar="iran"><button class="bull on" data-side="bull">Bull</button><div class="bullbear show-bull"></div></div>
<div class="narrative" data-nar="aicapex"><button class="bull on" data-side="bull">Bull</button><div class="bullbear show-bull"></div></div>
{feedback_html}
<script id="chartData">{{}}</script>
</main>"""


class RepairMainFeedbackTest(unittest.TestCase):
    def test_moves_legacy_feedback_wrapper_ids_to_nested_textareas(self):
        feedback_html = """<section id="feedback"><form id="fb-form">
<div id="fb-missing">
  <label>Missing story:</label>
  <textarea name="missing" rows="3" placeholder="Missing placeholder"></textarea>
</div>
<div id="fb-open">
  <label>Open feedback:</label>
  <textarea name="open" rows="3" placeholder="Open placeholder"></textarea>
</div>
</form></section>"""

        repaired = repair_main_html(valid_main_with(feedback_html))

        self.assertNotIn('<div id="fb-missing"', repaired)
        self.assertNotIn('<div id="fb-open"', repaired)
        self.assertEqual(len(re.findall(r'id="fb-missing"', repaired)), 1)
        self.assertEqual(len(re.findall(r'id="fb-open"', repaired)), 1)
        self.assertRegex(repaired, r'<textarea[^>]*name="missing"[^>]*id="fb-missing"')
        self.assertRegex(repaired, r'<textarea[^>]*name="open"[^>]*id="fb-open"')
        self.assertNotIn('<textarea id="fb-missing" rows="4"><label>', repaired)
        self.assertNotIn('<textarea id="fb-open" rows="4"><label>', repaired)


if __name__ == "__main__":
    unittest.main()
