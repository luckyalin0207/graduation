"""
简历解析模块 v2
- PDF 解析：pymupdf（比 pdfminer 更快，中文更友好）
- Word 解析：python-docx
- 结构化提取：正则 + 规则，识别工作经历、教育经历、项目经历、技能
"""
import re
import logging
import tempfile
import os

logger = logging.getLogger(__name__)


# ── 常量 ──────────────────────────────────────────────────────────────────────

TECH_SKILLS = [
    # 语言
    'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Go', 'Rust',
    'PHP', 'Ruby', 'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB',
    # 前端
    'Vue', 'React', 'Angular', 'Node.js', 'HTML', 'CSS', 'jQuery',
    'Bootstrap', 'Webpack', 'Vite', 'Next.js', 'Nuxt.js',
    # 后端框架
    'Django', 'Flask', 'FastAPI', 'Spring', 'SpringBoot', 'Express', 'Gin',
    # 数据库
    'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQL Server',
    'Elasticsearch', 'SQLite', 'ClickHouse', 'HBase',
    # 大数据
    'Spark', 'Hadoop', 'Hive', 'Kafka', 'Flink', 'Airflow',
    # 运维/云
    'Docker', 'Kubernetes', 'Linux', 'Git', 'Jenkins', 'CI/CD',
    'Nginx', 'Apache', 'AWS', 'Azure', '阿里云', '腾讯云', 'GCP',
    # AI/ML
    '机器学习', '深度学习', '数据分析', '数据挖掘', 'NLP', '自然语言处理',
    '计算机视觉', '推荐系统', 'TensorFlow', 'PyTorch', 'Scikit-learn',
    'Pandas', 'NumPy', 'Matplotlib', 'Seaborn', 'XGBoost', 'LightGBM',
    # 架构
    '微服务', 'RESTful', 'GraphQL', 'gRPC', 'WebSocket', 'RabbitMQ',
    # 其他
    'Selenium', 'Scrapy', 'Celery', 'Redis', 'Nginx',
]

EDU_LEVELS = ['博士', '硕士', '本科', '大专', '专科', '高中', '中专']

# 章节标题关键词（用于切分简历段落）
SECTION_PATTERNS = {
    'education':   r'教育|学历|学习经历|Education',
    'work':        r'工作经历|工作经验|职业经历|实习经历|Work\s*Experience|Employment',
    'project':     r'项目经历|项目经验|Project',
    'skills':      r'技能|专业技能|技术栈|Skills|Skill',
    'summary':     r'个人简介|自我评价|个人优势|Summary|Profile|About',
    'awards':      r'荣誉|奖项|证书|Awards|Certificates',
}

# 日期模式（用于识别时间段）
DATE_PATTERN = r'(\d{4})[.\-/年](\d{1,2})?[.\-/月]?\s*[-~至到]\s*(\d{4}|至今|present|now)[.\-/年]?(\d{1,2})?'


# ── 文本提取 ──────────────────────────────────────────────────────────────────

def extract_text_from_pdf(file_path: str) -> str:
    """用 pymupdf 提取 PDF 文本，保留换行结构"""
    try:
        import fitz  # pymupdf
        doc = fitz.open(file_path)
        pages = []
        for page in doc:
            # 按块提取，保留段落结构
            blocks = page.get_text('blocks')
            lines = []
            for b in sorted(blocks, key=lambda x: (x[1], x[0])):  # 按 y, x 排序
                text = b[4].strip()
                if text:
                    lines.append(text)
            pages.append('\n'.join(lines))
        doc.close()
        return '\n'.join(pages)
    except Exception as e:
        logger.warning(f'pymupdf 失败，降级到 pdfminer: {e}')
        return _extract_pdf_fallback(file_path)


def _extract_pdf_fallback(file_path: str) -> str:
    """pdfminer 降级方案"""
    try:
        from pdfminer.high_level import extract_text
        return extract_text(file_path) or ''
    except Exception as e:
        logger.error(f'pdfminer 也失败: {e}')
        return ''


def extract_text_from_docx(file_path: str) -> str:
    """从 Word 文件提取文本"""
    try:
        import docx
        doc = docx.Document(file_path)
        parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text.strip())
        # 也提取表格内容
        for table in doc.tables:
            for row in table.rows:
                row_text = ' | '.join(c.text.strip() for c in row.cells if c.text.strip())
                if row_text:
                    parts.append(row_text)
        return '\n'.join(parts)
    except Exception as e:
        logger.error(f'Word 解析失败: {e}')
        return ''


def extract_text_from_upload(file_obj, filename: str) -> str:
    """从 Django 上传文件对象提取文本"""
    suffix = os.path.splitext(filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        for chunk in file_obj.chunks():
            f.write(chunk)
        tmp = f.name
    try:
        if suffix == '.pdf':
            return extract_text_from_pdf(tmp)
        elif suffix in ('.docx', '.doc'):
            return extract_text_from_docx(tmp)
        return ''
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass


# ── 基础字段提取 ──────────────────────────────────────────────────────────────

def extract_name(text: str) -> str | None:
    """提取姓名：取前几行中符合中文姓名规则的词"""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for line in lines[:8]:
        # 2-4个中文字，独占一行或行首
        m = re.match(r'^([\u4e00-\u9fa5]{2,4})[\s\u3000]*$', line)
        if m:
            return m.group(1)
        # 带"姓名："前缀
        m = re.search(r'姓\s*名[：:]\s*([\u4e00-\u9fa5]{2,4})', line)
        if m:
            return m.group(1)
    return None


def extract_email(text: str) -> str | None:
    m = re.search(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}', text)
    return m.group(0) if m else None


def extract_phone(text: str) -> str | None:
    m = re.search(r'(?:\+86[-\s]?)?1[3-9]\d{9}', text)
    if m:
        phone = re.sub(r'\D', '', m.group(0))
        if phone.startswith('86'):
            phone = phone[2:]
        if len(phone) == 11:
            return phone
    return None


def extract_education_level(text: str) -> str | None:
    for edu in EDU_LEVELS:
        if edu in text:
            return edu
    return None


def extract_experience_years(text: str) -> int | None:
    patterns = [
        r'(\d+)\s*年.*?经验',
        r'工作.*?(\d+)\s*年',
        r'从业.*?(\d+)\s*年',
        r'经验.*?(\d+)\s*年',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return int(m.group(1))
    return None


def extract_skills(text: str) -> list[str]:
    found = []
    upper = text.upper()
    for skill in TECH_SKILLS:
        if skill.upper() in upper:
            found.append(skill)
    return found


# ── 结构化段落切分 ────────────────────────────────────────────────────────────

def _split_sections(text: str) -> dict[str, str]:
    """把简历文本按章节切分，返回 {section_key: content}"""
    lines = text.split('\n')
    sections: dict[str, list[str]] = {'header': []}
    current = 'header'

    for line in lines:
        stripped = line.strip()
        if not stripped:
            sections.setdefault(current, []).append('')
            continue

        matched = False
        for key, pattern in SECTION_PATTERNS.items():
            # 章节标题：短行（<15字）且匹配关键词
            if len(stripped) < 15 and re.search(pattern, stripped, re.IGNORECASE):
                current = key
                sections.setdefault(current, [])
                matched = True
                break

        if not matched:
            sections.setdefault(current, []).append(stripped)

    return {k: '\n'.join(v).strip() for k, v in sections.items()}


# ── 工作经历解析 ──────────────────────────────────────────────────────────────

def _parse_work_section(text: str) -> list[dict]:
    """解析工作经历段落，返回结构化列表"""
    if not text:
        return []

    entries = []
    # 按日期行切分（每段工作经历通常以时间开头）
    blocks = re.split(r'\n(?=\d{4})', text)

    for block in blocks:
        if not block.strip():
            continue
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if not lines:
            continue

        entry: dict = {'raw': block.strip()}

        # 提取时间段，同时尝试从时间行提取公司名
        date_m = re.search(DATE_PATTERN, block, re.IGNORECASE)
        if date_m:
            entry['start'] = f"{date_m.group(1)}.{date_m.group(2) or '01'}"
            end_year = date_m.group(3)
            entry['end'] = '至今' if re.search(r'至今|present|now', end_year, re.I) else f"{end_year}.{date_m.group(4) or '01'}"
            # 时间行里去掉日期后剩余的文字可能是公司名
            date_line = next((l for l in lines if re.search(DATE_PATTERN, l, re.I)), '')
            company_candidate = re.sub(DATE_PATTERN, '', date_line, flags=re.I).strip(' \t-~至')
            if company_candidate and len(company_candidate) > 1:
                entry['company'] = company_candidate

        # 如果时间行没有公司名，找含公司关键词的行
        if 'company' not in entry:
            for line in lines[:4]:
                if re.search(r'公司|集团|科技|网络|信息|有限|股份|企业|银行|医院|学校|大学|研究院|研究所', line):
                    entry['company'] = line
                    break

        # 提取职位（含"工程师/开发/经理/专员"等关键词的行）
        for line in lines:
            if re.search(r'工程师|开发|经理|专员|架构师|设计师|分析师|运营|产品|测试|运维|顾问|总监|主管', line):
                entry.setdefault('title', line)
                break

        # 剩余内容作为描述
        desc_lines = [l for l in lines if l != entry.get('company') and l != entry.get('title')]
        entry['description'] = '\n'.join(desc_lines[:6])  # 最多6行

        entries.append(entry)

    return entries


# ── 教育经历解析 ──────────────────────────────────────────────────────────────

def _parse_education_section(text: str) -> list[dict]:
    """解析教育经历段落"""
    if not text:
        return []

    entries = []
    blocks = re.split(r'\n(?=\d{4})', text)

    for block in blocks:
        if not block.strip():
            continue
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if not lines:
            continue

        entry: dict = {}

        date_m = re.search(DATE_PATTERN, block, re.IGNORECASE)
        if date_m:
            entry['start'] = f"{date_m.group(1)}.{date_m.group(2) or '09'}"
            end_year = date_m.group(3)
            entry['end'] = '至今' if re.search(r'至今|present|now', end_year, re.I) else f"{end_year}.{date_m.group(4) or '06'}"

        # 学历
        for edu in EDU_LEVELS:
            if edu in block:
                entry['degree'] = edu
                break

        # 学校名（含"大学/学院/学校"的行）
        for line in lines:
            if re.search(r'大学|学院|学校|University|College|Institute', line):
                entry['school'] = line
                break

        # 专业
        for line in lines:
            if re.search(r'专业|系|学院', line) and line != entry.get('school'):
                entry.setdefault('major', line)
                break

        if entry:
            entries.append(entry)

    return entries


# ── 项目经历解析 ──────────────────────────────────────────────────────────────

def _parse_project_section(text: str) -> list[dict]:
    """解析项目经历段落"""
    if not text:
        return []

    entries = []
    # 按项目名切分（通常是较短的行后跟描述）
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    current: dict | None = None

    for line in lines:
        # 新项目：短行（<30字）且不含日期
        if len(line) < 30 and not re.search(r'\d{4}.*[-~至]', line):
            if current:
                entries.append(current)
            current = {'name': line, 'description': ''}
        elif current:
            current['description'] += line + '\n'

    if current:
        entries.append(current)

    # 清理描述
    for e in entries:
        e['description'] = e['description'].strip()[:300]

    return entries[:5]  # 最多5个项目


# ── 主入口 ────────────────────────────────────────────────────────────────────

class ResumeParser:
    """简历解析器（向后兼容旧接口）"""

    TECH_SKILLS = TECH_SKILLS
    EDU_KEYWORDS = EDU_LEVELS

    @staticmethod
    def extract_text_from_pdf(file_path):
        return extract_text_from_pdf(file_path)

    @staticmethod
    def extract_text_from_docx(file_path):
        return extract_text_from_docx(file_path)

    @staticmethod
    def extract_text_from_file(file_obj, filename):
        return extract_text_from_upload(file_obj, filename)

    @staticmethod
    def extract_email(text):
        return extract_email(text)

    @staticmethod
    def extract_phone(text):
        return extract_phone(text)

    @staticmethod
    def extract_education(text):
        return extract_education_level(text)

    @staticmethod
    def extract_experience_years(text):
        return extract_experience_years(text)

    @staticmethod
    def extract_skills(text):
        return extract_skills(text)

    @staticmethod
    def extract_name(text):
        return extract_name(text)

    @staticmethod
    def parse_resume(file_obj, filename: str) -> dict:
        """
        完整解析简历，返回结构化数据：
        {
          success, name, email, phone, education, experience_years, skills,
          work_experience: [{company, title, start, end, description}],
          education_list:  [{school, degree, major, start, end}],
          projects:        [{name, description}],
          summary: str,
          raw_text: str (前800字)
        }
        """
        text = extract_text_from_upload(file_obj, filename)

        if not text or len(text.strip()) < 20:
            return {'success': False, 'error': '无法解析文件，请确保文件格式正确（PDF 或 DOCX）'}

        sections = _split_sections(text)

        result = {
            'success': True,
            'name': extract_name(text),
            'email': extract_email(text),
            'phone': extract_phone(text),
            'education': extract_education_level(text),
            'experience_years': extract_experience_years(text),
            'skills': extract_skills(text),
            'work_experience': _parse_work_section(sections.get('work', '')),
            'education_list': _parse_education_section(sections.get('education', '')),
            'projects': _parse_project_section(sections.get('project', '')),
            'summary': sections.get('summary', '')[:300],
            'raw_text': text[:800],
        }

        return result
