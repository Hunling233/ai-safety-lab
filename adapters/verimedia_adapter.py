import requests
import time
from bs4 import BeautifulSoup
from pathlib import Path
from .base import MediaAnalyzerAdapter
import tempfile
from typing import Optional
try:
    from pdfminer.high_level import extract_text as _pdf_extract_text
except Exception:  # pragma: no cover
    _pdf_extract_text = None 

class VeriMediaAdapter(MediaAnalyzerAdapter):
    def __init__(self, base_url: str, timeout: int = 120, parse_pdf: bool = True):
        self.base_url = base_url.rstrip("/")
        self.sess = requests.Session()
        self.timeout = timeout
        self.parse_pdf = parse_pdf

    def analyze_file(self, file_path: str, file_type: str):
        fp = Path(file_path)
        data = {"file_type": file_type}  # text | audio | video
        mime = self._guess_mime(fp.suffix)
        # 确保文件句柄按时关闭，避免泄漏
        with fp.open("rb") as f:
            files = {"file": (fp.name, f, mime)}
            r = self.sess.post(f"{self.base_url}/upload", files=files, data=data, timeout=self.timeout)
            r.raise_for_status()
            html = r.text

            toxicity, suggestions, report = self._parse_results(html)
            # 为避免多次调用覆盖 PDF，使用时间戳后缀唯一命名
            pdf_filename = f"{fp.stem}-{int(time.time()*1000)}.pdf"
            # 传递解析的数据给PDF生成器
            pdf_path = self.download_pdf(
                save_to=f"runs/artifacts/{pdf_filename}",
                toxicity_level=toxicity,
                report_content=report
            )
            pdf_text = self._extract_pdf_text(pdf_path) if self.parse_pdf else None
            return {"toxicity": toxicity, "suggestions": suggestions, "report": report,
                    "pdf_path": pdf_path, "raw_html": html, "pdf_text": pdf_text}

    def analyze_text(self, text: str, file_type: str = "text", filename: Optional[str] = None):
        """
        将一段原始文本写入临时 .txt 文件后复用 analyze_file。
        适用于后端只接受文件而不接受纯文本的场景。
        """
        fname = filename or "input.txt"
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir) / fname
            tmp.write_text(text, encoding="utf-8")
            return self.analyze_file(str(tmp), file_type)

    def download_pdf(self, save_to: str, toxicity_level: str = "Unknown", report_content: str = "") -> str:
        """
        下载PDF报告。需要传递分析结果数据以生成正确的PDF。
        
        Args:
            save_to: 保存路径
            toxicity_level: 毒性等级（从HTML解析获取）
            report_content: 报告内容（从HTML解析获取）
        """
        Path(save_to).parent.mkdir(parents=True, exist_ok=True)
        
        # 使用POST请求并传递必要的数据
        data = {
            "toxicity_level": toxicity_level,
            "report_content": report_content
        }
        
        r = self.sess.post(f"{self.base_url}/download_report_pdf", data=data, timeout=self.timeout)
        r.raise_for_status()
        Path(save_to).write_bytes(r.content)
        return str(save_to)

    def _parse_results(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        # 更新CSS选择器以匹配实际的HTML结构
        tox_el = soup.select_one(".toxicity-level, #toxicity, .toxicity")
        toxicity = tox_el.get_text(strip=True) if tox_el else "Unknown"
        suggestions = [li.get_text(strip=True) for li in soup.select("#suggestions li, .suggestions li")][:5]
        rpt_el = soup.select_one("#report, .report")
        report = rpt_el.get_text("\n", strip=True) if rpt_el else ""
        return toxicity, suggestions, report

    def _serialize_result(self, vr: dict) -> str:
        toxicity = vr.get("toxicity")
        suggestions = vr.get("suggestions") or []
        report = vr.get("report") or ""
        pdf_path = vr.get("pdf_path")

        lines = []
        if toxicity is not None:
            lines.append(f"toxicity: {toxicity}")
        if suggestions:
            lines.append("suggestions: " + "; ".join(map(str, suggestions[:5])))
        if report:
            rpt = str(report)
            if len(rpt) > 2000:
                rpt = rpt[:2000] + "... (truncated)"
            lines.append("report: " + rpt)
        if pdf_path:
            lines.append(f"pdf_path: {pdf_path}")
        return "\n".join(lines) if lines else str(vr)

    def _extract_pdf_text(self, pdf_path: str, max_chars: int = 8000) -> Optional[str]:
        """使用 pdfminer 抽取 PDF 文本，失败或空文本返回 None。"""
        if _pdf_extract_text is None:
            return None
        try:
            text = _pdf_extract_text(pdf_path) or ""
            text = text.strip()
            if not text:
                return None
            if len(text) > max_chars:
                text = text[:max_chars] + "... (truncated)"
            return text
        except Exception:
            return None

    @staticmethod
    def _guess_mime(suffix: str):
        s = suffix.lower().lstrip(".")
        return {
            "txt":"text/plain","pdf":"application/pdf",
            "docx":"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "mp3":"audio/mpeg","wav":"audio/wav","m4a":"audio/mp4",
            "mp4":"video/mp4","webm":"video/webm"
        }.get(s, "application/octet-stream")

    # 让 VeriMedia 也可作为“文本型 Agent”被 testsuites 调用
    # compliance_audit 将调用 invoke(prompt) 获取输出进行评分
    def invoke(self, prompt_or_inputs):
        # 处理字典输入，提取prompt字符串
        if isinstance(prompt_or_inputs, dict):
            prompt = prompt_or_inputs.get("input", prompt_or_inputs.get("prompt", ""))
        else:
            prompt = prompt_or_inputs
            
        result = self.analyze_text(prompt, file_type="text")
        
        # 优先返回PDF中的实际文本内容供测试套件分析
        pdf_text = result.get("pdf_text")
        if pdf_text and pdf_text.strip():
            # PDF文本提取成功，返回实际内容
            output = pdf_text.strip()
        else:
            # PDF文本提取失败，使用HTML解析的结构化结果
            toxicity = result.get("toxicity")
            if toxicity and toxicity != "Unknown":
                output = self._serialize_result(result)
            else:
                # 如果都失败了，返回基本状态信息
                output = f"toxicity: {result.get('toxicity', 'Unknown')}\npdf_path: {result.get('pdf_path', 'N/A')}"
        
        # 保持与常见 Agent 返回结构相似
        return {
            "output": output,
            "toxicity": result.get("toxicity"),
            "pdf_path": result.get("pdf_path"),
            "suggestions": result.get("suggestions"),
            "pdf_text": result.get("pdf_text"),  # 额外提供PDF文本
        }
