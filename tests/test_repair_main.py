import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from repair_main import repair_main_html


def valid_main(feedback_html: str) -> str:
    narratives = "\n".join(
        f'''
        <div class="narrative" data-nar="{name}">
          <div class="toggles"><button class="bull" data-side="bull">Bull</button></div>
          <div class="bullbear"><div class="bull">Bull case</div><div class="bear">Bear case</div></div>
        </div>
        '''
        for name in ("bonds", "iran", "aicapex")
    )
    return f"""
    <main>
      {narratives}
      <section id="feedback">
        <form id="fb-form">
          {feedback_html}
        </form>
      </section>
      <script type="application/json" id="chartData">{{}}</script>
    </main>
    """


class RepairMainHtmlTest(unittest.TestCase):
    def test_moves_feedback_wrapper_ids_to_inner_textareas(self):
        fixed = repair_main_html(
            valid_main(
                """
                <div id="fb-missing">
                  <label>What did we miss?</label>
                  <textarea name="missing" rows="3"></textarea>
                </div>
                <div id="fb-open">
                  <label>Open feedback:</label>
                  <textarea name="open" rows="3"></textarea>
                </div>
                """
            )
        )

        self.assertNotIn('<div id="fb-missing"', fixed)
        self.assertNotIn('<div id="fb-open"', fixed)
        self.assertIn('<textarea name="missing" rows="3" id="fb-missing"></textarea>', fixed)
        self.assertIn('<textarea name="open" rows="3" id="fb-open"></textarea>', fixed)
        self.assertIsNone(re.search(r'<textarea[^>]*id="fb-missing"[^>]*>(?:(?!</textarea>).)*<textarea', fixed))
        self.assertIsNone(re.search(r'<textarea[^>]*id="fb-open"[^>]*>(?:(?!</textarea>).)*<textarea', fixed))

    def test_converts_simple_feedback_wrappers_to_closed_textareas(self):
        fixed = repair_main_html(
            valid_main(
                """
                <div class="notes" id="fb-missing">Plain missing text</div>
                <div id="fb-open">Plain open text</div>
                """
            )
        )

        self.assertIn('<textarea class="notes" id="fb-missing" rows="4">Plain missing text</textarea>', fixed)
        self.assertIn('<textarea id="fb-open" rows="4">Plain open text</textarea>', fixed)


if __name__ == "__main__":
    unittest.main()
