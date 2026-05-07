import re
from collections import Counter

import gradio as gr
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Agg")

from database import (
    get_all_quotes, create_quote, update_quote,
    delete_quote, get_quote, get_stats,
)
from scraper import run_scraper, CATEGORIES

plt.rcParams["axes.unicode_minus"] = False


def render_stats():
    stats = get_stats()
    quotes = get_all_quotes(limit=10000)

    stop = {
        "the","a","an","and","or","but","in","on","at","to","for",
        "of","with","by","is","it","its","as","that","this","be",
        "are","was","were","have","has","had","not","from","i",
        "you","we","he","she","they","do","did","my","your","our",
        "me","him","her","us","them","what","who","when","where",
        "which","if","can","will","would","so","just","about","up",
        "out","no","more","one","all","there","their","than","been",
    }
    words: list[str] = []
    for q in quotes:
        for w in re.findall(r"[a-z']+", q["text"].lower()):
            w = w.strip("'")
            if len(w) > 2 and w not in stop:
                words.append(w)
    freq = Counter(words).most_common(20)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.patch.set_facecolor("#0f172a")
    for ax in axes:
        ax.set_facecolor("#1e293b")
        ax.tick_params(colors="white")
        ax.spines["bottom"].set_color("#475569")
        ax.spines["left"].set_color("#475569")
        for sp in ["top","right"]:
            ax.spines[sp].set_visible(False)

    if freq:
        wds, cnts = zip(*freq)
        colors = plt.cm.plasma(np.linspace(0.2, 0.9, len(wds)))
        axes[0].barh(list(wds), list(cnts), color=colors)
        axes[0].invert_yaxis()
        axes[0].set_title("Top 20 Words", color="white", fontsize=13, pad=10)
        axes[0].set_xlabel("Count", color="#94a3b8")
        axes[0].tick_params(axis="y", labelsize=9, labelcolor="white")
        axes[0].tick_params(axis="x", labelcolor="#94a3b8")

    top_authors = stats["top_authors"][:10]
    if top_authors:
        authors = [a["author"].split()[-1] for a in top_authors]
        cnts2   = [a["count"] for a in top_authors]
        colors2 = plt.cm.cool(np.linspace(0.2, 0.9, len(authors)))
        axes[1].bar(authors, cnts2, color=colors2, edgecolor="#0f172a", linewidth=0.5)
        axes[1].set_title("Top 10 Authors", color="white", fontsize=13, pad=10)
        axes[1].set_ylabel("Quotes", color="#94a3b8")
        axes[1].tick_params(axis="x", rotation=35, labelsize=8, labelcolor="white")
        axes[1].tick_params(axis="y", labelcolor="#94a3b8")

    top_tags = stats["top_tags"][:8]
    if top_tags:
        tags  = [t["tag"] for t in top_tags]
        cnts3 = [t["count"] for t in top_tags]
        wedge_props = {"width": 0.55, "edgecolor": "#0f172a", "linewidth": 2}
        axes[2].pie(cnts3, labels=tags, autopct="%1.0f%%",
                    wedgeprops=wedge_props, textprops={"color": "white", "fontsize": 8},
                    colors=plt.cm.Set3.colors[:len(tags)])
        axes[2].set_title("Top Tags (Donut)", color="white", fontsize=13, pad=10)

    plt.tight_layout(pad=2)
    return (
        fig,
        f"📚 총 격언: **{stats['total_quotes']}개**\n\n"
        f"✍️ 저자 수: **{stats['unique_authors']}명**",
    )


def search_quotes(keyword, author, tag):
    rows = get_all_quotes(
        keyword=keyword or None,
        author=author or None,
        tag=tag or None,
        limit=200,
    )
    if not rows:
        return "검색 결과가 없습니다."
    return "\n\n".join(
        f"**[{r['id']}]** {r['text']}\n— *{r['author']}*  |  태그: `{r['tags']}`"
        for r in rows
    )


def crud_create(text, author, tags):
    if not text.strip() or not author.strip():
        return "❌ 내용과 저자는 필수입니다."
    q = create_quote(text, author, tags)
    return f"✅ 저장 완료! ID={q['id']}"


def crud_read(qid):
    try:
        q = get_quote(int(qid))
    except Exception:
        return "❌ ID는 숫자로 입력하세요."
    if not q:
        return f"❌ ID={qid} 를 찾을 수 없습니다."
    return (
        f"**ID**: {q['id']}\n\n"
        f"**Text**: {q['text']}\n\n"
        f"**Author**: {q['author']}\n\n"
        f"**Tags**: {q['tags']}\n\n"
        f"**Source**: {q['source']}\n\n"
        f"**Created**: {q['created_at']}"
    )


def crud_update(qid, text, author, tags):
    try:
        q = update_quote(int(qid),
                         text=text or None,
                         author=author or None,
                         tags=tags or None)
    except Exception:
        return "❌ ID는 숫자로 입력하세요."
    if not q:
        return f"❌ ID={qid} 를 찾을 수 없습니다."
    return f"✅ 수정 완료!\n{q['text']} — {q['author']}"


def crud_delete(qid):
    try:
        ok = delete_quote(int(qid))
    except Exception:
        return "❌ ID는 숫자로 입력하세요."
    return f"✅ ID={qid} 삭제 완료!" if ok else f"❌ ID={qid} 를 찾을 수 없습니다."


def run_crawl(selected_cats):
    if not selected_cats:
        return "카테고리를 하나 이상 선택하세요."
    result = run_scraper(categories=selected_cats, max_per_cat=20)
    return (
        f"🎉 크롤링 완료!\n\n"
        f"- 저장된 격언: **{result['saved']}개**\n"
        f"- 중복 건너뜀: **{result['skipped_duplicates']}개**\n"
        f"- 수집 카테고리: {', '.join(result['categories'])}"
    )


def text_analysis():
    quotes = get_all_quotes(limit=10000)
    if not quotes:
        return None, "데이터가 없습니다. 먼저 크롤링을 실행하세요."

    lengths = [len(q["text"]) for q in quotes]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor("#0f172a")
    for ax in axes:
        ax.set_facecolor("#1e293b")
        ax.tick_params(colors="white")
        for sp in ["top","right"]:
            ax.spines[sp].set_visible(False)
        for sp in ["bottom","left"]:
            ax.spines[sp].set_color("#475569")

    axes[0].hist(lengths, bins=20, color="#6366f1", edgecolor="#0f172a", linewidth=0.7)
    axes[0].set_title("Quote Length Distribution", color="white", fontsize=13)
    axes[0].set_xlabel("Characters", color="#94a3b8")
    axes[0].set_ylabel("Count", color="#94a3b8")
    axes[0].tick_params(labelcolor="white")

    from collections import defaultdict
    author_len: dict = defaultdict(list)
    for q in quotes:
        author_len[q["author"]].append(len(q["text"]))
    avg = sorted(
        {a: sum(v)/len(v) for a, v in author_len.items()}.items(),
        key=lambda x: x[1], reverse=True
    )[:10]
    if avg:
        auths, avgs = zip(*avg)
        auths = [a.split()[-1] for a in auths]
        colors = plt.cm.magma(np.linspace(0.3, 0.9, len(auths)))
        axes[1].barh(list(auths), list(avgs), color=colors)
        axes[1].invert_yaxis()
        axes[1].set_title("Avg Quote Length by Author (Top 10)", color="white", fontsize=13)
        axes[1].set_xlabel("Avg Characters", color="#94a3b8")
        axes[1].tick_params(labelcolor="white")

    plt.tight_layout(pad=2)
    summary = (
        f"📊 **분석 결과**\n\n"
        f"- 총 격언 수: {len(quotes)}\n"
        f"- 평균 길이: {sum(lengths)/len(lengths):.1f}자\n"
        f"- 최장 격언: {max(lengths)}자\n"
        f"- 최단 격언: {min(lengths)}자"
    )
    return fig, summary


def build_gradio_app() -> gr.Blocks:
    with gr.Blocks(title="📚 Quotes Manager") as app:

        gr.Markdown(
            "# 📚 격언 관리 & 분석 시스템\n"
            "> quotes.toscrape.com 기반 FastAPI + Gradio 통합 서비스"
        )

        with gr.Tab("📊 통계 대시보드"):
            stats_btn = gr.Button("🔄 통계 새로고침", variant="primary")
            stats_plot = gr.Plot(label="시각화")
            stats_info = gr.Markdown()
            stats_btn.click(render_stats, outputs=[stats_plot, stats_info])

        with gr.Tab("🔍 검색"):
            with gr.Row():
                kw_in  = gr.Textbox(label="키워드 (본문)", placeholder="life, love ...")
                au_in  = gr.Textbox(label="저자", placeholder="Einstein ...")
                tg_in  = gr.Textbox(label="태그", placeholder="humor ...")
            search_btn = gr.Button("검색", variant="primary")
            search_out = gr.Markdown()
            search_btn.click(search_quotes, inputs=[kw_in, au_in, tg_in], outputs=search_out)

        with gr.Tab("✏️ CRUD 관리"):
            with gr.Accordion("➕ 새 격언 추가", open=True):
                with gr.Row():
                    c_text   = gr.Textbox(label="격언 내용", lines=3)
                    c_author = gr.Textbox(label="저자")
                    c_tags   = gr.Textbox(label="태그 (쉼표 구분)")
                c_btn = gr.Button("저장", variant="primary")
                c_out = gr.Markdown()
                c_btn.click(crud_create, inputs=[c_text, c_author, c_tags], outputs=c_out)

            with gr.Accordion("🔎 ID로 조회"):
                r_id  = gr.Number(label="ID", precision=0)
                r_btn = gr.Button("조회")
                r_out = gr.Markdown()
                r_btn.click(crud_read, inputs=r_id, outputs=r_out)

            with gr.Accordion("📝 수정"):
                with gr.Row():
                    u_id     = gr.Number(label="ID", precision=0)
                    u_text   = gr.Textbox(label="새 내용 (선택)")
                    u_author = gr.Textbox(label="새 저자 (선택)")
                    u_tags   = gr.Textbox(label="새 태그 (선택)")
                u_btn = gr.Button("수정", variant="secondary")
                u_out = gr.Markdown()
                u_btn.click(crud_update, inputs=[u_id, u_text, u_author, u_tags], outputs=u_out)

            with gr.Accordion("🗑️ 삭제"):
                d_id  = gr.Number(label="ID", precision=0)
                d_btn = gr.Button("삭제", variant="stop")
                d_out = gr.Markdown()
                d_btn.click(crud_delete, inputs=d_id, outputs=d_out)

        with gr.Tab("🕷️ 크롤링"):
            gr.Markdown("카테고리를 선택하고 크롤링을 실행하면 DB에 자동 저장됩니다.")
            cats_check = gr.CheckboxGroup(
                choices=CATEGORIES,
                value=CATEGORIES[:5],
                label="수집할 카테고리",
            )
            crawl_btn = gr.Button("🚀 크롤링 시작", variant="primary")
            crawl_out = gr.Markdown()
            crawl_btn.click(run_crawl, inputs=cats_check, outputs=crawl_out)

        with gr.Tab("📈 텍스트 분석"):
            analysis_btn = gr.Button("분석 실행", variant="primary")
            analysis_plot = gr.Plot()
            analysis_info = gr.Markdown()
            analysis_btn.click(text_analysis, outputs=[analysis_plot, analysis_info])

    return app