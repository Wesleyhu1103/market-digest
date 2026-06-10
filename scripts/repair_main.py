"""Auto-repair <main> HTML before daily publish. Run on main_html string."""
import re


def _repair_feedback_textarea(main_html: str, field_id: str) -> str:
    def strip_id_attr(attrs: str) -> str:
        return re.sub(
            rf'\s+id=(["\']){re.escape(field_id)}\1',
            "",
            attrs,
            count=1,
            flags=re.I,
        )

    def ensure_textarea_id(tag: str) -> str:
        if re.search(r"\bid=", tag, flags=re.I):
            return re.sub(r'\bid=(["\']).*?\1', f'id="{field_id}"', tag, count=1, flags=re.I)
        return tag[:-1] + f' id="{field_id}">'

    wrapper_with_textarea = re.compile(
        rf'<div(?P<attrs>[^>]*)\bid=(?P<quote>["\']){re.escape(field_id)}(?P=quote)'
        rf'(?P<attrs_after>[^>]*)>(?P<body>[\s\S]*?<textarea[^>]*>[\s\S]*?</textarea>[\s\S]*?)</div>',
        flags=re.I,
    )

    def move_id_to_inner_textarea(match):
        attrs = strip_id_attr(match.group("attrs") + match.group("attrs_after"))
        body = re.sub(
            r"<textarea[^>]*>",
            lambda m: ensure_textarea_id(m.group(0)),
            match.group("body"),
            count=1,
            flags=re.I,
        )
        return f"<div{attrs}>{body}</div>"

    main_html, replacements = wrapper_with_textarea.subn(move_id_to_inner_textarea, main_html, count=1)
    if replacements:
        return main_html

    simple_wrapper = re.compile(
        rf'<div(?P<attrs>[^>]*)\bid=(?P<quote>["\']){re.escape(field_id)}(?P=quote)'
        rf'(?P<attrs_after>[^>]*)>(?P<body>[\s\S]*?)</div>',
        flags=re.I,
    )

    def convert_wrapper_to_textarea(match):
        attrs = strip_id_attr(match.group("attrs") + match.group("attrs_after"))
        attrs = attrs.rstrip()
        if attrs:
            attrs += " "
        return f'<textarea{attrs}id="{field_id}" rows="4">{match.group("body")}</textarea>'

    return simple_wrapper.sub(convert_wrapper_to_textarea, main_html, count=1)


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

    # Feedback must use textarea for .value; move wrapper IDs onto existing
    # textareas instead of creating malformed nested textarea markup.
    main_html = _repair_feedback_textarea(main_html, "fb-missing")
    main_html = _repair_feedback_textarea(main_html, "fb-open")

    bull_on = len(re.findall(r'data-side="bull"[^>]*class="bull on"|class="bull on"[^>]*data-side="bull"', main_html))
    show_bull = main_html.count('class="bullbear show-bull"')
    if bull_on < 3 or show_bull < 3:
        raise SystemExit(f"ABORT: toggle structure bull_on={bull_on} show_bull={show_bull} (need 3 each)")

    n_chart = main_html.count('id="chartData"')
    if n_chart != 1:
        raise SystemExit(f"ABORT: expected exactly 1 chartData block, got {n_chart}")

    return main_html
