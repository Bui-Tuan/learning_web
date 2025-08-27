import re

# --- GIỮ NGUYÊN ---
BACKSLASH_WORD = re.compile(r'\\textbackslash\s*\{?\}?', re.IGNORECASE)


def fix_math_delimiters(s: str) -> str:
    if not s:
        return s
    # \textbackslash -> \
    s = BACKSLASH_WORD.sub(r'\\', s)
    # "\ (" -> "\(" ; "\ )" -> "\)"
    s = re.sub(r'\\\s*\(', r'\\(', s)
    s = re.sub(r'\\\s*\)', r'\\)', s)
    # "\ frac" -> "\frac", "\ int" -> "\int", ...
    s = re.sub(r'\\\s+([A-Za-z]+)', r'\\\1', s)
    # gọn khoảng trắng
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def strip_choice_label(text: str) -> str:
    return re.sub(r'^[ABCD]\.\s*', '', text or '').strip()


def _soft_clean_latex_line(line: str) -> str:
    line = line.replace('\u00A0', ' ')         # NBSP -> space
    line = re.sub(r'\s+', ' ', line).strip()
    # gỡ \textbf{...}, \emph{...} nếu có
    line = re.sub(r'\\textbf\{([^}]*)\}', r'\1', line)
    line = re.sub(r'\\emph\{([^}]*)\}', r'\1', line)
    return line


# --- MỚI: làm sạch NỘI DUNG BÊN TRONG khối toán ---
MATH_INLINE_RE  = re.compile(r'\\\((.*?)\\\)', re.DOTALL)   # \( ... \)
MATH_DISPLAY_RE = re.compile(r'\\\[(.*?)\\\]', re.DOTALL)   # \[ ... \]
MATH_DOLLAR_RE  = re.compile(r'\$(.*?)\$', re.DOTALL)       # $ ... $


# Thêm các regex để nhận các khối toán
def _clean_inside_math(text: str) -> str:
    """
    Làm sạch CỤC BỘ bên trong các khối toán:
    - \_   -> _
    - \^{} -> ^
    - \^   -> ^
    - \{   -> {   ;   \} -> }
    - "\ frac" -> "\frac", v.v.
    """
    if not text:
        return text

    def _fix(inner: str) -> str:
        inner = inner.replace(r'\_', '_')                         # \_  -> _
        inner = re.sub(r'\\\^\s*\{\s*\}', '^', inner)             # \^{} -> ^
        inner = inner.replace(r'\^', '^')                         # \^  -> ^
        inner = inner.replace(r'\{', '{').replace(r'\}', '}')     # \{ \} -> { }
        inner = re.sub(r'\\\s+([A-Za-z]+)', r'\\\1', inner)       # "\ frac" -> "\frac"
        inner = re.sub(r'\\([im])(?=[^A-Za-z])', r'\1', inner)  # \i -> i, \m -> m
        inner = re.sub(r'\s+', ' ', inner).strip()
        return inner

    def repl_paren(m):  return r'\(' + _fix(m.group(1)) + r'\)'
    def repl_brack(m):  return r'\[' + _fix(m.group(1)) + r'\]'
    def repl_dollar(m): return r'$'  + _fix(m.group(1)) + r'$'

    text = MATH_INLINE_RE.sub(repl_paren, text)
    text = MATH_DISPLAY_RE.sub(repl_brack, text)
    text = MATH_DOLLAR_RE.sub(repl_dollar, text)
    return text


# --- REGEX ---
LEVEL_RE = re.compile(r'Mức\s*độ:\s*(Dễ|Trung\s*Bình|Khó).*?Câu\s*hỏi:\s*(.+)', re.IGNORECASE)
ANSWER_RE = re.compile(r'Đáp\s*án:\s*([ABCD])', re.IGNORECASE)
OPT_LINE_RE = re.compile(r'^([ABCD])\.\s*(.+)$')


def parse_docx(latex_text: str, tmp_media_dir: str = None):
    """
    Parse theo block:
    [Mức độ: ... Câu hỏi: ...]  (có thể nhiều dòng, có math)
      A. ...
      B. ...
      C. ...
      D. ...
    Đáp án: X
    """
    t = (latex_text or '').replace('\r\n', '\n').replace('\u00A0', ' ')

    # Tìm tất cả vị trí mở đầu câu hỏi
    anchors = list(re.finditer(r'Mức\s*độ:\s*(Dễ|Trung\s*Bình|Khó)\b.*?Câu\s*hỏi:', t, flags=re.IGNORECASE))
    questions = []

    for i, m in enumerate(anchors):
        start = m.start()
        end = anchors[i + 1].start() if i + 1 < len(anchors) else len(t)
        block = t[start:end]

        # Lấy mức độ
        level_raw = m.group(1).replace(' ', '')
        level = 'Trung Bình' if level_raw.lower() == 'trungbinh' else ('Dễ' if level_raw.lower() == 'dễ' else 'Khó')

        # Lấy phần sau "Câu hỏi:"
        cq = re.search(r'Câu\s*hỏi:\s*', block, flags=re.IGNORECASE)
        after = block[cq.end():] if cq else block

        # Vị trí bắt đầu đáp án hoặc "Đáp án:"
        mA   = re.search(r'^\s*(?:\\(?:tightlist|item)\s*)?A\.\s', after, flags=re.MULTILINE)
        mAns = re.search(r'Đáp\s*án\s*:', after, flags=re.IGNORECASE)
        cut  = min(mA.start() if mA else len(after), mAns.start() if mAns else len(after))
        qtext_raw = after[:cut].strip()

        # Ghép các dòng nội dung thành 1 dòng + làm sạch
        qtext = fix_math_delimiters(' '.join(qtext_raw.splitlines()))
        qtext = _clean_inside_math(qtext)

        # Lấy 4 đáp án (chấp nhận có \item / \tightlist ở đầu dòng)
        opt_pairs = re.findall(
            r'^\s*(?:\\(?:tightlist|item)\s*)?([ABCD])\.\s*(.+)$',
            after,
            flags=re.MULTILINE | re.IGNORECASE
        )
        opt_map = {}
        for lab, txt in opt_pairs:
            cleaned = fix_math_delimiters(strip_choice_label(txt.strip()))
            cleaned = _clean_inside_math(cleaned)
            opt_map[lab.upper()] = cleaned

        options = [opt_map.get(k, '') for k in ['A', 'B', 'C', 'D']]

        # Đáp án đúng
        ansm = re.search(r'Đáp\s*án\s*:\s*([ABCD])', block, flags=re.IGNORECASE)
        correct = ansm.group(1).upper() if ansm else None

        # Chỉ nhận nếu đủ dữ liệu
        if qtext and all(options) and correct:
            questions.append({
                "content": qtext,
                "options": options,
                "answer": correct,
                "images": [],           # (ảnh đề: giữ logic copy nếu bạn có)
                "rate": level,
            })

    return questions
