from __future__ import annotations

import os
import uuid
import json
import mimetypes
import tempfile
import shutil
import re
from typing import Optional, Dict, Any

import requests

# PDF 文本抽取（若未安装则降级为空）
try:
    from pdfminer.high_level import extract_text as _pdf_extract_text  # type: ignore
except Exception:  # pragma: no cover
    _pdf_extract_text = None

from .base import AgentAdapter


class HateSpeechAdapter(AgentAdapter):
    """
    适配一个仅支持“上传文件 + 聊天流式输出”的 Agent：
    - 通过 /api/auth/csrf 获取 CSRF，/api/auth/callback/credentials 登录
    - 上传文件到 /api/files/upload
    - 通过 /api/chat 建立 Vercel AI Data Stream（text/plain 流），解析 text-delta/finish 等片段

    为了兼容通用 testsuite（基于 invoke(prompt) 的文本接口）
    - 若未提供 default_file_path，则会把 prompt 写成临时 .pdf 文件后上传（避免部分后端拒绝 text/plain）
    - 流式内容中若出现报告 PDF 的下载链接（.pdf），则下载并抽取 PDF 文本作为输出
    - 若提供了 default_file_path，则每次都会上传该固定文件
    最终返回 {"output": 最终文本, 可选: pdf_path/local_pdf_path}
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3000/",
        email: Optional[str] = None,
        password: Optional[str] = None,
        selected_chat_model: str = "chat-model",  # 你已配置 ClaimBuster，默认启用工具
        default_file_path: Optional[str] = None,
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.email = email or os.environ.get("AGENT_EMAIL") or ""
        self.password = password or os.environ.get("AGENT_PASSWORD") or ""
        self.selected_chat_model = selected_chat_model
        self.default_file_path = default_file_path or os.environ.get("AGENT_FILE_PATH")
        self.timeout = timeout

        self.sess = requests.Session()
        self._authed = False

    # ---- Auth helpers ----------------------------------------------------
    def _get_csrf(self) -> str:
        r = self.sess.get(
            f"{self.base_url}/api/auth/csrf",
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        r.raise_for_status()
        try:
            data = r.json()
        except Exception as e:
            snippet = (r.text or "")[:200]
            ct = r.headers.get("content-type")
            raise RuntimeError(
                f"CSRF endpoint did not return JSON. url={r.url} status={r.status_code} content-type={ct} body[:200]={snippet}"
            ) from e
        token = (data or {}).get("csrfToken", "")
        if not token:
            raise RuntimeError("CSRF token missing in response JSON")
        return token

    def _has_session_cookie(self) -> bool:
        # 兼容 Auth.js(v5) 与旧版 NextAuth 的会话 cookie 命名
        jar = self.sess.cookies
        wanted = (
            "authjs.session-token",
            "__Secure-authjs.session-token",
            "next-auth.session-token",
            "__Secure-next-auth.session-token",
        )
        return any(name in jar for name in wanted)

    def _login(self):
        # 1) 拿 CSRF（JSON）并保存 Set-Cookie
        token = self._get_csrf()

        # 2) 提交登录表单（credentials provider）
        data = {
            "csrfToken": token,
            "email": self.email,
            "password": self.password,
            "callbackUrl": f"{self.base_url}/",
            # 加上 redirect=false，便于用 JSON 判定，也允许重定向链拿 cookie
            "redirect": "false",
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/api/auth/signin?provider=credentials",
        }

        r = self.sess.post(
            f"{self.base_url}/api/auth/callback/credentials",
            data=data,
            headers=headers,
            allow_redirects=True,  # 保持允许 302，以兼容不同返回路径
            timeout=self.timeout,
        )
        r.raise_for_status()

        # 3) 如果被重定向到 /login?error=CredentialsSignin，说明账号/密码错误
        final_url = getattr(r, "url", "") or ""
        history_urls = [
            getattr(h, "headers", {}).get("Location", "")
            for h in (getattr(r, "history", []) or [])
        ]
        url_chain = " -> ".join([u for u in history_urls if u] + ([final_url] if final_url else []))
        if (
            "error=CredentialsSignin" in final_url
            or any("error=CredentialsSignin" in (u or "") for u in history_urls)
        ):
            raise RuntimeError(
                f"CredentialsSignin: invalid email/password. Redirect chain: {url_chain}"
            )

        # 4) 确认已经建立会话（cookie 或 session 接口）
        if not self._has_session_cookie():
            # 进一步检查 /api/auth/session 便于诊断（Auth.js v5 返回 JSON）
            sr = self.sess.get(
                f"{self.base_url}/api/auth/session",
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
            if sr.ok:
                try:
                    js = sr.json()
                    if js.get("user"):
                        self._authed = True
                        return
                except Exception:
                    pass
            ct = sr.headers.get("content-type")
            snippet = (sr.text or "")[:200]
            raise RuntimeError(
                f"Login did not establish session cookie. session GET: url={sr.url} status={sr.status_code} content-type={ct} body[:200]={snippet}"
            )

        self._authed = True

    def _ensure_login(self):
        if not self._authed:
            if not self.email or not self.password:
                raise RuntimeError("HateSpeechAdapter: missing email/password for login")
            self._login()

    # ---- File upload -----------------------------------------------------
    def _upload_file(self, file_path: str) -> Dict[str, Any]:
        fname = os.path.basename(file_path)
        ctype, _ = mimetypes.guess_type(fname)
        with open(file_path, "rb") as f:
            files = {"file": (fname, f, ctype or "application/octet-stream")}
            r = self.sess.post(
                f"{self.base_url}/api/files/upload",
                files=files,
                allow_redirects=False,
                timeout=self.timeout,
            )
        # 若被重定向到登录，说明会话无效
        if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers.get("Location") or r.headers.get("location") or ""
            raise RuntimeError(f"Upload requires authentication. Redirected to: {loc}")
        r.raise_for_status()
        try:
            return r.json()  # { url, pathname, contentType }
        except Exception as e:
            snippet = (r.text or "")[:200]
            ct = r.headers.get("content-type")
            raise RuntimeError(
                f"Upload endpoint did not return JSON. url={r.url} status={r.status_code} content-type={ct} body[:200]={snippet}"
            ) from e

    # ---- Chat streaming --------------------------------------------------
    def _build_chat_payload(
        self, chat_id: str, uploaded: Dict[str, Any], display_name: str, input_text: str
    ) -> Dict[str, Any]:
        user_msg_id = str(uuid.uuid4())
        return {
            "id": chat_id,
            "selectedChatModel": self.selected_chat_model,
            "messages": [
                {
                    "id": user_msg_id,
                    "role": "user",
                    "parts": [{"type": "input_text", "text": input_text}],
                    "experimental_attachments": [
                        {
                            "url": uploaded.get("url"),
                            "name": uploaded.get("pathname", display_name),
                            "contentType": uploaded.get("contentType", "application/octet-stream"),
                        }
                    ],
                }
            ],
        }

    def _stream_chat_vercel(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析 Vercel AI Data Stream（text/plain）
        - 聚合 text-delta 文本
        - 尝试从片段或 JSON 帧中提取 PDF 链接
        返回 {"text": str, 可选: "pdf_url": str}
        """
        headers = {
            "Accept": "text/plain",
            "Content-Type": "application/json",
            "X-Vercel-AI-Data-Stream": "v1",
        }
        with self.sess.post(
            f"{self.base_url}/api/chat",
            headers=headers,
            data=json.dumps(payload),
            stream=True,
            timeout=self.timeout,
        ) as r:
            if r.status_code != 200:
                snippet = (r.text or "")[:200]
                ct = r.headers.get("content-type")
                raise RuntimeError(
                    f"/api/chat error. url={r.url} status={r.status_code} content-type={ct} body[:200]={snippet}"
                )
            url_regex = re.compile(r"https?://[^\s\"']+\.pdf", re.IGNORECASE)
            agg_text: list[str] = []
            pdf_url: Optional[str] = None
            for raw in r.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                line = raw.strip()
                # 1) data: {json}
                if line.startswith("data:"):
                    data_part = line[5:].strip()
                    try:
                        obj = json.loads(data_part)
                        # text-delta
                        if obj.get("type") == "text-delta" and isinstance(obj.get("text"), str):
                            agg_text.append(obj["text"])
                        # 在任意 JSON 值里寻找 PDF 链接
                        u = self._find_pdf_url(obj)
                        if u:
                            pdf_url = u
                            break
                    except Exception:
                        pass
                # 2) f:{json} | 0:"text" 风格
                if line.startswith("f:"):
                    try:
                        obj = json.loads(line[2:].strip())
                        u = self._find_pdf_url(obj)
                        if u:
                            pdf_url = u
                            break
                    except Exception:
                        pass
                if line.startswith("0:") or line.startswith("1:"):
                    # 带引号的增量文本，例如 0:"Hello "
                    try:
                        txt = line.split(":", 1)[1].strip()
                        # 去除可能的引号包裹
                        if (txt.startswith('"') and txt.endswith('"')) or (txt.startswith("'") and txt.endswith("'")):
                            txt = txt[1:-1]
                        agg_text.append(txt)
                    except Exception:
                        pass
                # 3) 直接匹配行内 PDF URL
                if pdf_url is None:
                    m = url_regex.search(line)
                    if m:
                        pdf_url = m.group(0)
                        break
            return {"text": "".join(agg_text), **({"pdf_url": pdf_url} if pdf_url else {})}

    # ---- Public AgentAdapter API ----------------------------------------
    def invoke(self, prompt: str) -> Dict[str, Any]:
        """
        - 若提供 default_file_path：上传该文件，并将 prompt 作为文本内容发送；
        - 否则：将 prompt 写入临时 prompt.pdf 再上传；
        - 解析 Vercel 流式文本，若包含 PDF 链接则下载并抽取文本；
        返回 {"output": <最终文本>, 可选: pdf_path, local_pdf_path}。
        """
        # 选择上传的文件
        if self.default_file_path:
            # 使用固定文件，先确保登录再上传
            self._ensure_login()
            src_path = self.default_file_path
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                # 将纯文本转存为 .pdf 以规避后端对 text/plain 的限制
                src_path = os.path.join(tmpdir, "prompt.pdf")
                self._generate_pdf_from_text(prompt, src_path)
                # 保存一份可视的副本到 runs/artifacts，方便用户查看
                saved_copy = None
                try:
                    artifacts_dir = os.path.join("runs", "artifacts")
                    os.makedirs(artifacts_dir, exist_ok=True)
                    saved_copy = os.path.join(artifacts_dir, f"prompt-{uuid.uuid4().hex}.pdf")
                    shutil.copyfile(src_path, saved_copy)
                except Exception:
                    saved_copy = None

                # 在创建文件成功后再尝试登录与上传；即便登录失败，副本也已落盘可查看
                self._ensure_login()
                uploaded = self._upload_file(src_path)
                chat_id = str(uuid.uuid4())
                display_name = os.path.basename(src_path)
                payload = self._build_chat_payload(
                    chat_id, uploaded, display_name, input_text=prompt
                )
                stream_res = self._stream_chat_vercel(payload)
                out_text = stream_res.get("text") or ""
                pdf_path = None
                if stream_res.get("pdf_url"):
                    try:
                        pdf_path = self._download_pdf(stream_res["pdf_url"])
                        pdf_text = self._extract_pdf_text(pdf_path)
                        if pdf_text:
                            out_text = pdf_text
                    except Exception:
                        pass
                result = {"output": out_text}
                if saved_copy:
                    result["local_pdf_path"] = saved_copy
                if pdf_path:
                    result["pdf_path"] = pdf_path
                return result

        # 若使用固定文件，逻辑与上面相同，但不创建临时文件
        uploaded = self._upload_file(src_path)
        chat_id = str(uuid.uuid4())
        display_name = os.path.basename(src_path)
        payload = self._build_chat_payload(
            chat_id, uploaded, display_name, input_text=prompt
        )
        stream_res = self._stream_chat_vercel(payload)
        out_text = stream_res.get("text") or ""
        pdf_path = None
        if stream_res.get("pdf_url"):
            try:
                pdf_path = self._download_pdf(stream_res["pdf_url"])
                pdf_text = self._extract_pdf_text(pdf_path)
                if pdf_text:
                    out_text = pdf_text
            except Exception:
                pass
        result = {"output": out_text}
        if pdf_path:
            result["pdf_path"] = pdf_path
        return result

    # ---- Helpers --------------------------------------------------------
    def _generate_pdf_from_text(self, text: str, out_path: str) -> str:
        """将纯文本写入 PDF 文件，返回保存路径。"""
        try:
            from reportlab.lib.pagesizes import A4  # type: ignore
            from reportlab.pdfgen import canvas  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "缺少依赖 reportlab：请先 pip install reportlab 后重试。"
            ) from e
        page_width, page_height = A4
        left_margin = 50
        right_margin = 50
        top_margin = 50
        bottom_margin = 50
        text_width = page_width - left_margin - right_margin
        c = canvas.Canvas(out_path, pagesize=A4)
        c.setTitle("Prompt")
        c.setFont("Helvetica", 12)
        import textwrap
        approx_char_per_line = max(20, int(text_width / 6))
        lines = []
        for paragraph in str(text).splitlines() or [""]:
            wrapped = textwrap.wrap(paragraph, width=approx_char_per_line) or [""]
            lines.extend(wrapped)
        y = page_height - top_margin
        line_height = 16
        for line in lines:
            if y < bottom_margin:
                c.showPage()
                c.setFont("Helvetica", 12)
                y = page_height - top_margin
            c.drawString(left_margin, y, line)
            y -= line_height
        c.save()
        return out_path

    def _find_pdf_url(self, obj: Any) -> Optional[str]:
        """在嵌套结构中寻找以 .pdf 结尾的 URL。"""
        if obj is None:
            return None
        if isinstance(obj, str):
            s = obj.strip()
            if s.lower().endswith(".pdf") and s.lower().startswith("http"):
                return s
            return None
        if isinstance(obj, list):
            for it in obj:
                u = self._find_pdf_url(it)
                if u:
                    return u
            return None
        if isinstance(obj, dict):
            for k, v in obj.items():
                u = self._find_pdf_url(v)
                if u:
                    return u
        return None

    def _download_pdf(self, url: str, save_to: Optional[str] = None) -> str:
        """下载 PDF 到 runs/artifacts 并返回路径。"""
        artifacts_dir = os.path.join("runs", "artifacts")
        os.makedirs(artifacts_dir, exist_ok=True)
        dst = save_to or os.path.join(artifacts_dir, f"report-{uuid.uuid4().hex}.pdf")
        r = self.sess.get(url, timeout=self.timeout)
        r.raise_for_status()
        with open(dst, "wb") as f:
            f.write(r.content)
        return dst

    def _extract_pdf_text(self, pdf_path: str, max_chars: int = 8000) -> Optional[str]:
        """使用 pdfminer 抽取 PDF 文本；失败或空文本返回 None。"""
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