from kbsync.convert import html_to_markdown


def test_keeps_headings_lists_and_relative_links():
    md = html_to_markdown(
        '<h2>Setup</h2><ul><li>One</li><li>Two</li></ul>'
        '<p>See <a href="/hc/en-us/articles/1-foo">the guide</a>.</p>'
    )
    assert "## Setup" in md
    assert "- One" in md and "- Two" in md
    assert "[the guide](/hc/en-us/articles/1-foo)" in md


def test_code_block_is_fenced_and_inline_code_kept():
    md = html_to_markdown("<p>Run <code>ls -la</code></p><pre>echo hi\necho bye</pre>")
    assert "`ls -la`" in md
    assert "```\necho hi\necho bye\n```" in md


def test_removes_scripts_styles_images_and_rules():
    md = html_to_markdown(
        '<style>p{}</style><script>x()</script><p>Text</p><img src="a.png" alt="a"><hr>'
    )
    assert md == "Text"


def test_in_page_toc_is_dropped_but_content_links_stay():
    md = html_to_markdown(
        '<ul><li><a href="#a">A</a></li><li><a href="#b">B</a></li></ul>'
        '<p>Go to <a href="#a">A</a> or <a href="https://x.test/y">Y</a></p>'
    )
    assert "#a" not in md
    assert "- [A]" not in md
    assert "Go to A or [Y](https://x.test/y)" in md


def test_youtube_embed_becomes_watch_link():
    md = html_to_markdown('<iframe src="https://www.youtube.com/embed/abc123?rel=0"></iframe>')
    assert md == "Video: https://www.youtube.com/watch?v=abc123"


def test_single_column_table_becomes_blockquote_and_data_table_stays():
    md = html_to_markdown(
        "<table><tbody><tr><td><strong>NOTE</strong></td></tr>"
        "<tr><td>Be careful</td></tr></tbody></table>"
        "<table><thead><tr><th>Plan</th><th>Limit</th></tr></thead>"
        "<tbody><tr><td>Pro</td><td>5</td></tr></tbody></table>"
    )
    assert "> **NOTE**" in md and "> Be careful" in md
    assert "| Plan | Limit |" in md and "| Pro | 5 |" in md


def test_underscores_not_escaped_and_whitespace_normalised():
    md = html_to_markdown("<p>file my_file_name.txt\u00a0ok\u200b</p><p></p><p>end</p>")
    assert "my_file_name.txt ok" in md
    assert "\\_" not in md
    assert "\n\n\n" not in md


def test_table_without_header_row_promotes_first_row():
    md = html_to_markdown(
        "<table><tbody><tr><td>Plan</td><td>Limit</td></tr>"
        "<tr><td>Pro</td><td>5</td></tr></tbody></table>"
    )
    assert md.splitlines()[0] == "| Plan | Limit |"
    assert "|  |" not in md
