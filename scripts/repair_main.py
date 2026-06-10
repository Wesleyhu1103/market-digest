"""Auto-repair <main> HTML before daily publish. Run on main_html string."""
import re


def repair_main_html(main_html: str) -> str:
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
    wrappers = {
        'techMovers': 320,
        'treasuryYields': 280,
        'brentChart': 280,
        'creditChart': 240,
        'stressChart': 240,
        'redditSentiment': 240,
        'dealSizes': 240,
    }
    for cid, h in wrappers.items():
        pat = rf'<canvas id="{cid}"[^>]*></canvas>'
        repl = (
            f'<div style="position:relative;height:{h}px;width:100%">'
            f'<canvas id="{cid}"></canvas></div>'
        )
        if re.search(rf'height:\d+px[^"]*"><canvas id="{cid}"', main_html):
            continue
        main_html = re.sub(pat, repl, main_html, count=1)

    # Feedback IDs must be on textareas because submit reads .value from them.
    def _feedback_id_fix(field_id: str) -> None:
        nonlocal main_html

        def ensure_textarea_id(m):
            tag = m.group(0)
            if re.search(r'\bid=["\']', tag):
                return re.sub(r'\bid=["\'][^"\']*["\']', f'id="{field_id}"', tag, count=1)
            return tag.replace("<textarea", f'<textarea id="{field_id}"', 1)

        wrapper = re.compile(
            rf'<div([^>]*)\bid=["\']{field_id}["\']([^>]*)>([\s\S]*?)</div>',
            re.I,
        )

        def move_id_to_textarea(m):
            inner = re.sub(r"<textarea\b[^>]*>", ensure_textarea_id, m.group(3), count=1, flags=re.I)
            return f"<div{m.group(1)}{m.group(2)}>{inner}</div>"

        main_html = wrapper.sub(move_id_to_textarea, main_html, count=1)

    _feedback_id_fix("fb-missing")
    _feedback_id_fix("fb-open")

    bull_on = len(re.findall(r'data-side="bull"[^>]*class="bull on"|class="bull on"[^>]*data-side="bull"', main_html))
    show_bull = main_html.count('class="bullbear show-bull"')
    if bull_on < 3 or show_bull < 3:
        raise SystemExit(f"ABORT: toggle structure bull_on={bull_on} show_bull={show_bull} (need 3 each)")

    n_chart = main_html.count('id="chartData"')
    if n_chart != 1:
        raise SystemExit(f"ABORT: expected exactly 1 chartData block, got {n_chart}")

    return main_html
