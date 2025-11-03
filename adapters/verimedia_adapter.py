import requests
from bs4 import BeautifulSoup
from pathlib import Path
from .base import MediaAnalyzerAdapter

class VeriMediaAdapter(MediaAnalyzerAdapter):
    def __init__(self, base_url: str, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.sess = requests.Session()
        self.timeout = timeout

    def analyze_file(self, file_path: str, file_type: str):
        fp = Path(file_path)
        files = {"file": (fp.name, fp.open("rb"), self._guess_mime(fp.suffix))}
        data = {"file_type": file_type}  # text | audio | video
        r = self.sess.post(f"{self.base_url}/upload", files=files, data=data, timeout=self.timeout)
        r.raise_for_status()
        html = r.text

        toxicity, suggestions, report = self._parse_results(html)
        pdf_path = self.download_pdf(save_to=f"runs/artifacts/{fp.stem}.pdf")
        return {"toxicity": toxicity, "suggestions": suggestions, "report": report,
                "pdf_path": pdf_path, "raw_html": html}

    def download_pdf(self, save_to: str) -> str:
        Path(save_to).parent.mkdir(parents=True, exist_ok=True)
        r = self.sess.get(f"{self.base_url}/download_report_pdf", timeout=self.timeout)
        r.raise_for_status()
        Path(save_to).write_bytes(r.content)
        return str(save_to)

    def _parse_results(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        tox_el = soup.select_one("#toxicity, .toxicity")
        toxicity = tox_el.get_text(strip=True) if tox_el else "Unknown"
        suggestions = [li.get_text(strip=True) for li in soup.select("#suggestions li, .suggestions li")][:5]
        rpt_el = soup.select_one("#report, .report")
        report = rpt_el.get_text("\n", strip=True) if rpt_el else ""
        return toxicity, suggestions, report

    @staticmethod
    def _guess_mime(suffix: str):
        s = suffix.lower().lstrip(".")
        return {
            "txt":"text/plain","pdf":"application/pdf",
            "docx":"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "mp3":"audio/mpeg","wav":"audio/wav","m4a":"audio/mp4",
            "mp4":"video/mp4","webm":"video/webm"
        }.get(s, "application/octet-stream")
