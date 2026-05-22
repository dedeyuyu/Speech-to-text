"""
标点符号后处理模块

对 Whisper 输出的文字自动添加中文标点符号：
  - 逗号（，）：根据语意分割长文本
  - 句号（。）：陈述句结尾
  - 问号（？）：问句结尾
  - 感叹号（！）：感叹句结尾

整段文本的结尾必须以句号/问号/感叹号结束。
"""

import re

# ─── 标点字符集 ────────────────────────────────────────────
FULL_PUNCT = set('，。！？、；：""''（）【】《》')
END_PUNCT = set('。！？.!?')
ANY_PUNCT = set('，。！？、；：,.!?;:')

# ─── 问句模式（句尾关键词/词组）────────────────────────────
_QUESTION_END = re.compile(
    r'[吗呢嘛啊哦]'                      # 语气词
    r'|什么[？?]?$'
    r'|为什么[？?]?$'
    r'|怎么[？?]?$'
    r'|怎样[？?]?$'
    r'|如何[？?]?$'
    r'|哪[里个些儿][？?]?$'
    r'|谁[？?]?$'
    r'|哪个[？?]?$'
    r'|多少[？?]?$'
    r'|几[？?]?$'
    r'|[Ww]hat\b'
    r'|[Ww]hy\b'
    r'|[Hh]ow\b'
    r'|[Ww]here\b'
    r'|[Ww]hen\b'
    r'|[Ww]ho\b'
    r'|\?$'
)

# ─── 感叹句模式 ─────────────────────────────────────────────
_EXCLAIM_END = re.compile(
    r'太.{0,6}了[！!]?$'
    r'|好.{0,4}啊[！!]?$'
    r'|真的[！!]?$'
    r'|哇+[啊]?[！!]?$'
    r'|[！!]$'
)

# ─── 自然断句位置（在这些词前插入逗号）────────────────────
_BREAK_WORDS = re.compile(
    r'(?<=[^，。！？,!?；;])'   # 前面没有标点
    r'(?='
    r'然后|但是|不过|而且|另外|所以|因为|如果|虽然|尽管'
    r'|当然|其实|事实上|总之|总的来说|并且|以及|或者'
    r'|还有|同时|然而|因此|于是|不仅|还是|甚至|除此之外'
    r'|首先|其次|最后|接下来|此外|换句话说'
    r')'
)

# ─── 主函数 ─────────────────────────────────────────────────

def add_punctuation(text: str) -> str:
    """
    对转录文字进行标点后处理。

    Args:
        text: Whisper 原始输出

    Returns:
        添加标点后的文字
    """
    if not text:
        return text

    text = text.strip()
    if not text:
        return text

    # 去掉尾部不完整标点，重新判断
    cleaned = text.rstrip('，,；; \t')

    # ── 判断句型 ──────────────────────────────────────────
    tail = cleaned[-20:] if len(cleaned) > 20 else cleaned

    if _QUESTION_END.search(tail):
        end_punct = '？'
    elif _EXCLAIM_END.search(tail):
        end_punct = '！'
    else:
        end_punct = '。'

    # ── 已有完整结尾标点则只修正类型 ─────────────────────
    if cleaned and cleaned[-1] in END_PUNCT:
        # 替换为正确的标点
        result = cleaned[:-1] + end_punct
    else:
        result = cleaned + end_punct

    # ── 处理长文本内部逗号 ───────────────────────────────
    result = _insert_internal_commas(result)

    return result


def _insert_internal_commas(text: str) -> str:
    """在长句内部合适位置插入逗号。"""
    # 短文本或已有内部标点，直接返回
    if len(text) <= 15:
        return text

    has_internal = any(c in text[:-1] for c in '，。！？,!?；')
    if has_internal:
        return text

    # 在转折/连接词前插入逗号
    result = _BREAK_WORDS.sub('，', text)

    # 若仍无逗号且文本超过 30 字，按语境分割
    if '，' not in result and len(result) > 30:
        result = _split_by_particles(result)

    return result


def _split_by_particles(text: str) -> str:
    """
    在语气助词/结构助词后适当插入逗号，保证可读性。
    仅对纯中文长句生效。
    """
    # 检测是否主要是中文
    cjk_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    if cjk_count < len(text) * 0.5:
        return text  # 英文文本不处理

    # 在结构助词"的/了/过/着/地/得"后，若后面还有较长内容则加逗号
    pattern = re.compile(
        r'([的了过着地得])(?=[^\s，。！？,!?；]{8,})'
    )

    result = text
    last_comma = 0
    output = []
    i = 0

    # 找到每个可能的断句点，但保持间隔 ≥ 10 个字符
    for m in pattern.finditer(text[:-1]):  # 不处理最后一个字符（可能是标点）
        pos = m.end()
        if pos - last_comma >= 12:
            output.append(text[last_comma:pos])
            output.append('，')
            last_comma = pos

    output.append(text[last_comma:])
    result = ''.join(output)

    return result
