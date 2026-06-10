#!/usr/bin/env python3
import unittest

from repair_main import repair_main_html


class RepairMainTest(unittest.TestCase):
    def test_moves_feedback_ids_from_wrappers_to_textareas(self) -> None:
        main_html = """<main>
<button class="bull" data-side="bull">Bull</button>
<button class="bull" data-side="bull">Bull</button>
<button class="bull" data-side="bull">Bull</button>
<div class="bullbear"></div>
<div class="bullbear"></div>
<div class="bullbear"></div>
<div id="fb-missing">
  <label>What did we miss?</label>
  <textarea name="missing" rows="3"></textarea>
</div>
<div id="fb-open">
  <label>Open feedback</label>
  <textarea name="open" rows="3"></textarea>
</div>
<script type="application/json" id="chartData">{}</script>
</main>"""

        repaired = repair_main_html(main_html)

        self.assertIn('<textarea id="fb-missing" name="missing"', repaired)
        self.assertIn('<textarea id="fb-open" name="open"', repaired)
        self.assertNotIn('<div id="fb-missing">', repaired)
        self.assertNotIn('<div id="fb-open">', repaired)


if __name__ == "__main__":
    unittest.main()
