"""Auto-repair <main> HTML before daily publish. Run on main_html string."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_config import repair_chart_heights, repair_thresholds


def repair_main_html(main_html: str) -> str:
    # Archive is mounted outside <main> by the static template — strip if injected.
    main_html = re.sub(
        r'<section[^>]*\bid=["\']archive["\'][^>]*>[\s\S]*?</section>\s*',
        '',
        main_html,
        flags=re.I,
    )

    # Bull button active + visible on load
    main_html = re.sub(
        r'<button([^>]*)\bclass="bull"([^>]*)\bdata-side="bull"',
        r'<button\1class="bull on"\2data-side="bull"',
        main_html,
    )
    main_html = re.sub(
        r'<button class="bull" data-side="bull">',
        '<button class="bull on" data-side="bull">',
        main_html,
    )
    main_html = main_html.replace('<div class="bullbear">', '<div class="bullbear show-bull">')

    # Quiz only: data-val on .opt breaks scoring (feedback buttons use data-val intentionally)
    def _quiz_opt_fix(m):
        tag = m.group(0)
        if 'class="opt"' not in tag and "class='opt'" not in tag:
            return tag
        return tag.replace(' data-val=', ' data-opt=')

    main_html = re.sub(r'<span class="opt"[^>]*>', _quiz_opt_fix, main_html)

    # chartData must be the last child inside <main> (before </main>)
    chart_blocks = re.findall(
        r'<script[^>]*\bid=["\']chartData["\'][^>]*>[\s\S]*?</script>',
        main_html,
        flags=re.I,
    )
    if chart_blocks:
        for block in chart_blocks:
            main_html = main_html.replace(block, '', 1)
        merged = chart_blocks[-1]
        main_html = main_html.replace('</main>', merged + '\n</main>', 1)

    # Canvas height wrappers (Chart.js needs explicit container height)
    wrappers = repair_chart_heights()
    for cid, h in wrappers.items():
        pat = rf'<canvas id="{cid}"[^>]*></canvas>'
        repl = (
            f'<div style="position:relative;height:{h}px;width:100%">'
            f'<canvas id="{cid}"></canvas></div>'
        )
        if re.search(rf'height:\d+px[^"]*"><canvas id="{cid}"', main_html):
            continue
        main_html = re.sub(pat, repl, main_html, count=1)

    # Feedback must use textarea for .value
    main_html = re.sub(
        r'<div([^>]*)\bid="fb-missing"([^>]*)>',
        r'<textarea\1id="fb-missing"\2 rows="4">',
        main_html,
        count=1,
    )
    main_html = re.sub(
        r'<div([^>]*)\bid="fb-open"([^>]*)>',
        r'<textarea\1id="fb-open"\2 rows="4">',
        main_html,
        count=1,
    )

    min_bull_on, min_show_bull = repair_thresholds()
    bull_on = len(re.findall(r'data-side="bull"[^>]*class="bull on"|class="bull on"[^>]*data-side="bull"', main_html))
    show_bull = main_html.count('class="bullbear show-bull"')
    if bull_on < min_bull_on or show_bull < min_show_bull:
        raise SystemExit(
            f"ABORT: toggle structure bull_on={bull_on} show_bull={show_bull} "
            f"(need {min_bull_on} each: 3 narratives + buyside summary)"
        )

    n_chart = main_html.count('id="chartData"')
    if n_chart != 1:
        raise SystemExit(f"ABORT: expected exactly 1 chartData block, got {n_chart}")

    return main_html
